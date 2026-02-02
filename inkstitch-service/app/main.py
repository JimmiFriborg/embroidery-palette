# app/main.py
# InkStitch Microservice: Image → SVG (vectorized) → PES via Ink/Stitch CLI
#
# Endpoints:
#   GET  /health              → health check
#   POST /image-to-pes        → full pipeline: image → quantize → vectorize → stitch → PES
#   POST /svg-to-pes          → SVG with inkstitch attrs → PES (skip image processing)
#   POST /resize-or-convert   → pyembroidery: resize/convert existing embroidery files

import io
import os
import sys
import json
import shutil
import subprocess
import tempfile
import zipfile
import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
import numpy as np
from PIL import Image

logger = logging.getLogger("inkstitch_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="InkStitch Microservice", version="1.0.0")

# Paths
INKSTITCH_DIR = os.environ.get("INKSTITCH_DIR", "/opt/inkstitch")
INKSTITCH_BIN = os.path.join(INKSTITCH_DIR, "inkstitch.py")  # Python entry point
INKSCAPE_BIN = shutil.which("inkscape") or "inkscape"
POTRACE_BIN = "potrace"

# Hoop safe areas in mm (slightly inset from full hoop)
HOOP_SAFE = {
    "100x100": (90, 90),
    "70x70": (62, 62),
}

# Default stitch parameters for Ink/Stitch SVG attributes
DEFAULT_FILL_PARAMS = {
    "inkstitch:auto_fill": "true",
    "inkstitch:fill_underlay": "true",
    "inkstitch:fill_underlay_angle": "0",
    "inkstitch:fill_underlay_row_spacing_mm": "3",
    "inkstitch:fill_underlay_max_stitch_length_mm": "3",
    "inkstitch:row_spacing_mm": "0.25",
    "inkstitch:max_stitch_length_mm": "3.0",
    "inkstitch:staggers": "4",
    "inkstitch:running_stitch_length_mm": "1.5",
}

QUALITY_PRESETS = {
    "fast": {
        "inkstitch:row_spacing_mm": "0.35",
        "inkstitch:max_stitch_length_mm": "3.5",
        "inkstitch:fill_underlay": "false",
        "inkstitch:staggers": "3",
    },
    "balanced": {
        "inkstitch:row_spacing_mm": "0.25",
        "inkstitch:max_stitch_length_mm": "3.0",
        "inkstitch:fill_underlay": "true",
        "inkstitch:staggers": "4",
    },
    "quality": {
        "inkstitch:row_spacing_mm": "0.2",
        "inkstitch:max_stitch_length_mm": "2.5",
        "inkstitch:fill_underlay": "true",
        "inkstitch:fill_underlay_angle": "0,90",
        "inkstitch:staggers": "5",
    },
}


@app.get("/health")
def health():
    inkstitch_ok = os.path.isdir(INKSTITCH_DIR)
    inkscape_ok = shutil.which("inkscape") is not None
    potrace_ok = shutil.which(POTRACE_BIN) is not None
    return {
        "status": "ok" if (inkstitch_ok and potrace_ok and inkscape_ok) else "degraded",
        "service": "inkstitch_api",
        "inkstitch_dir": inkstitch_ok,
        "inkscape_available": inkscape_ok,
        "potrace_available": potrace_ok,
    }


@app.post("/image-to-pes")
async def image_to_pes(
    file: UploadFile = File(...),
    hoop_size: str = Form("100x100"),
    quality: str = Form("balanced"),
    thread_colors: Optional[str] = Form(None),
    density_override: Optional[float] = Form(None),
):
    """
    Full pipeline: raster image → quantize colors → vectorize → add inkstitch params → PES
    
    Args:
        file: Input image (PNG, JPG, etc.) — ideally already quantized/processed
        hoop_size: "100x100" or "70x70"
        quality: "fast", "balanced", or "quality"
        thread_colors: JSON array of hex colors for thread order, e.g. '["#FF0000","#00FF00"]'
        density_override: Override row spacing (mm), lower = denser
    """
    tmpdir = tempfile.mkdtemp(prefix="inkstitch_")
    try:
        # 1. Load and preprocess image with Pillow
        logger.info("Step 1: Loading image...")
        raw = await file.read()
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        
        # Parse thread colors if provided
        colors = None
        if thread_colors:
            try:
                colors = json.loads(thread_colors)
            except json.JSONDecodeError:
                pass
        
        # Get hoop dimensions
        safe_w, safe_h = HOOP_SAFE.get(hoop_size, (90, 90))
        
        # Resize image to fit hoop safe area (at 10 pixels/mm for good vectorization)
        px_per_mm = 10
        target_w = safe_w * px_per_mm
        target_h = safe_h * px_per_mm
        
        # Maintain aspect ratio
        ratio = min(target_w / img.width, target_h / img.height)
        new_w = int(img.width * ratio)
        new_h = int(img.height * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        
        logger.info(f"  Resized to {new_w}x{new_h} px (hoop: {safe_w}x{safe_h} mm)")
        
        # 2. Extract unique colors (image should already be quantized)
        logger.info("Step 2: Extracting color regions...")
        img_rgb = img.convert("RGB")
        arr = np.array(img_rgb)
        
        # Also get alpha for background masking
        alpha = np.array(img.split()[-1]) if img.mode == "RGBA" else np.full(arr.shape[:2], 255, dtype=np.uint8)
        
        # Find unique non-background colors
        mask_fg = alpha > 128  # foreground pixels
        fg_pixels = arr[mask_fg]
        
        if len(fg_pixels) == 0:
            raise HTTPException(status_code=400, detail="Image has no foreground pixels")
        
        unique_colors = np.unique(fg_pixels.reshape(-1, 3), axis=0)
        logger.info(f"  Found {len(unique_colors)} unique colors")
        
        # If too many colors, quantize
        if len(unique_colors) > 20:
            logger.info("  Too many colors, quantizing to 8...")
            img_q = img_rgb.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
            img_rgb = img_q.convert("RGB")
            arr = np.array(img_rgb)
            fg_pixels = arr[mask_fg]
            unique_colors = np.unique(fg_pixels.reshape(-1, 3), axis=0)
            logger.info(f"  After quantization: {len(unique_colors)} colors")
        
        # Order colors by thread_colors if provided, otherwise by area (largest first)
        if colors:
            # Match provided colors to detected colors
            ordered = order_colors_by_mapping(unique_colors, colors)
        else:
            # Sort by area (most pixels first) 
            ordered = sort_colors_by_area(arr, unique_colors, mask_fg)
        
        # 3. Vectorize each color region with potrace
        logger.info("Step 3: Vectorizing regions...")
        svg_paths = []
        
        for i, color_rgb in enumerate(ordered):
            hex_color = "#{:02X}{:02X}{:02X}".format(*color_rgb)
            logger.info(f"  Vectorizing color {i+1}/{len(ordered)}: {hex_color}")
            
            # Create binary mask for this color
            color_mask = np.all(arr == color_rgb, axis=2) & mask_fg
            
            if not np.any(color_mask):
                continue
            
            # Save as PBM for potrace
            pbm_path = os.path.join(tmpdir, f"color_{i}.pbm")
            svg_path = os.path.join(tmpdir, f"color_{i}.svg")
            
            save_mask_as_pbm(color_mask, pbm_path)
            
            # Run potrace to get SVG path
            result = subprocess.run(
                [POTRACE_BIN, "-s", "--flat", "-o", svg_path, pbm_path],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"  potrace failed for color {hex_color}: {result.stderr}")
                continue
            
            # Extract path data from potrace SVG output
            path_data = extract_potrace_paths(svg_path)
            if path_data:
                svg_paths.append({
                    "color": hex_color,
                    "paths": path_data,
                    "index": i,
                })
        
        if not svg_paths:
            raise HTTPException(status_code=400, detail="No regions could be vectorized")
        
        logger.info(f"  Vectorized {len(svg_paths)} color regions")
        
        # 4. Build SVG with inkstitch attributes
        logger.info("Step 4: Building SVG with stitch parameters...")
        
        # Get quality preset params
        preset_params = dict(DEFAULT_FILL_PARAMS)
        if quality in QUALITY_PRESETS:
            preset_params.update(QUALITY_PRESETS[quality])
        
        # Apply density override
        if density_override and density_override > 0:
            preset_params["inkstitch:row_spacing_mm"] = str(density_override)
        
        svg_content = build_inkstitch_svg(
            svg_paths, new_w, new_h, px_per_mm, preset_params
        )
        
        svg_file = os.path.join(tmpdir, "design.svg")
        with open(svg_file, "w") as f:
            f.write(svg_content)
        
        # 5. Run Ink/Stitch to generate PES
        logger.info("Step 5: Generating PES with Ink/Stitch...")
        
        pes_bytes = run_inkstitch_export(svg_file, tmpdir)
        
        logger.info(f"  PES generated: {len(pes_bytes)} bytes")
        
        return Response(
            content=pes_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="design.pes"'},
        )
        
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Processing timed out")
    except Exception as e:
        logger.exception("Processing error")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/svg-to-pes")
async def svg_to_pes(
    file: UploadFile = File(...),
    quality: str = Form("balanced"),
):
    """
    Convert SVG (with inkstitch attributes already set) directly to PES.
    Use this if you build the SVG yourself and just need Ink/Stitch to generate stitches.
    """
    tmpdir = tempfile.mkdtemp(prefix="inkstitch_")
    try:
        svg_data = await file.read()
        svg_file = os.path.join(tmpdir, "input.svg")
        with open(svg_file, "wb") as f:
            f.write(svg_data)
        
        pes_bytes = run_inkstitch_export(svg_file, tmpdir)
        
        return Response(
            content=pes_bytes,
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="design.pes"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.post("/resize-or-convert")
async def resize_or_convert(
    file: UploadFile = File(...),
    target_format: str = Form("pes"),
    scale: float = Form(1.0),
):
    """Resize or convert existing embroidery files using pyembroidery."""
    from pyembroidery import read as emb_read, write as emb_write
    
    tmpdir = tempfile.mkdtemp(prefix="inkstitch_")
    try:
        raw = await file.read()
        suffix = os.path.splitext(file.filename or "input.pes")[1]
        in_path = os.path.join(tmpdir, f"input{suffix}")
        with open(in_path, "wb") as f:
            f.write(raw)
        
        pattern = emb_read(in_path)
        if pattern is None:
            raise HTTPException(status_code=400, detail="Could not read embroidery file")
        
        if scale != 1.0:
            pattern.scale(scale, scale)
        
        out_path = os.path.join(tmpdir, f"output.{target_format.lower()}")
        emb_write(pattern, out_path)
        
        with open(out_path, "rb") as f:
            out_bytes = f.read()
        
        return Response(
            content=out_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="output.{target_format.lower()}"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─── Ink/Stitch export helper ────────────────────────────────────────

def run_inkstitch_export(svg_file: str, tmpdir: str) -> bytes:
    """
    Run Ink/Stitch to convert SVG → PES.
    
    Tries multiple approaches:
    1. inkstitch.py direct CLI (if available)
    2. Inkscape with Ink/Stitch extension actions
    3. Fallback: pyembroidery from SVG paths (basic fill)
    """
    
    # Approach 1: Try inkstitch.py directly
    if os.path.isfile(INKSTITCH_BIN):
        try:
            logger.info("  Trying inkstitch.py CLI...")
            result = subprocess.run(
                [sys.executable, INKSTITCH_BIN, "--extension=zip",
                 "--format-pes=True", svg_file],
                capture_output=True, timeout=120,
                env={**os.environ, "PYTHONPATH": INKSTITCH_DIR}
            )
            if result.returncode == 0 and result.stdout:
                pes = extract_pes_from_zip(result.stdout)
                if pes:
                    logger.info(f"  inkstitch.py succeeded: {len(pes)} bytes")
                    return pes
            logger.warning(f"  inkstitch.py failed: {result.stderr[:300]}")
        except Exception as e:
            logger.warning(f"  inkstitch.py error: {e}")
    
    # Approach 2: Inkscape CLI with extension
    try:
        logger.info("  Trying Inkscape + Ink/Stitch extension...")
        pes_file = os.path.join(tmpdir, "output.pes")
        result = subprocess.run(
            [INKSCAPE_BIN, svg_file,
             "--actions=select-all;org.inkstitch.output_pes",
             f"--export-filename={pes_file}"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "DISPLAY": "", "HOME": "/root"}
        )
        if os.path.isfile(pes_file) and os.path.getsize(pes_file) > 0:
            with open(pes_file, "rb") as f:
                pes = f.read()
            logger.info(f"  Inkscape export succeeded: {len(pes)} bytes")
            return pes
        logger.warning(f"  Inkscape export failed: {result.stderr[:300]}")
    except Exception as e:
        logger.warning(f"  Inkscape error: {e}")
    
    # Approach 3: Fallback — pyembroidery basic conversion
    logger.info("  Falling back to pyembroidery basic fill...")
    return pyembroidery_fallback(svg_file, tmpdir)


def pyembroidery_fallback(svg_file: str, tmpdir: str) -> bytes:
    """
    Basic PES generation using pyembroidery when Ink/Stitch isn't working.
    Parses SVG paths, generates simple fill stitches.
    """
    import pyembroidery
    import xml.etree.ElementTree as ET
    
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    
    # Get viewBox dimensions
    vb = root.get("viewBox", "0 0 100 100").split()
    vb_w, vb_h = float(vb[2]), float(vb[3])
    
    # Parse width/height in mm
    width_str = root.get("width", "100mm")
    height_str = root.get("height", "100mm")
    width_mm = float(width_str.replace("mm", ""))
    height_mm = float(height_str.replace("mm", ""))
    
    # Scale: viewBox pixels → embroidery units (10 units = 1mm)
    scale_x = (width_mm * 10) / vb_w
    scale_y = (height_mm * 10) / vb_h
    
    pattern = pyembroidery.EmbPattern()
    
    # Find all paths with fill colors
    paths = root.findall(".//svg:path", ns) or root.findall(".//path")
    
    if not paths:
        raise HTTPException(status_code=400, detail="No paths found in SVG")
    
    color_count = 0
    for path_el in paths:
        style = path_el.get("style", "")
        fill_color = None
        for part in style.split(";"):
            if part.strip().startswith("fill:"):
                fill_color = part.split(":")[1].strip()
                break
        
        if not fill_color or fill_color == "none":
            continue
        
        # Parse hex color
        try:
            fc = fill_color.lstrip("#")
            r, g, b = int(fc[0:2], 16), int(fc[2:4], 16), int(fc[4:6], 16)
        except (ValueError, IndexError):
            r, g, b = 0, 0, 0
        
        # Add thread
        thread = pyembroidery.EmbThread()
        thread.color = (r << 16) | (g << 8) | b
        pattern.add_thread(thread)
        
        if color_count > 0:
            pattern.color_change()
        color_count += 1
        
        # Simple bounding box fill (since parsing SVG path data is complex)
        # Get a rough bounding box from the path data
        d = path_el.get("d", "")
        coords = extract_coords_from_path(d)
        
        if not coords:
            continue
        
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Generate fill stitches (zigzag rows)
        row_spacing = 3  # pixels
        stitch_len = 30  # pixels
        first = True
        direction = 1
        
        y = min_y
        while y <= max_y:
            if direction == 1:
                x_range = range(int(min_x), int(max_x) + 1, stitch_len)
            else:
                x_range = range(int(max_x), int(min_x) - 1, -stitch_len)
            
            for x in x_range:
                ex = int((x - vb_w / 2) * scale_x)
                ey = int((y - vb_h / 2) * scale_y)
                
                if first:
                    pattern.add_stitch_absolute(pyembroidery.JUMP, ex, ey)
                    first = False
                else:
                    pattern.add_stitch_absolute(pyembroidery.STITCH, ex, ey)
            
            y += row_spacing
            direction *= -1
    
    pattern.end()
    
    output = io.BytesIO()
    pyembroidery.write_pes(pattern, output)
    output.seek(0)
    pes_data = output.read()
    
    if len(pes_data) < 50:
        raise HTTPException(status_code=500, detail="Failed to generate PES")
    
    logger.info(f"  pyembroidery fallback: {len(pes_data)} bytes, {color_count} colors")
    return pes_data


def extract_coords_from_path(d: str) -> list:
    """Extract approximate coordinates from SVG path data."""
    import re
    coords = []
    # Find all number pairs in the path data
    numbers = re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)', d)
    for i in range(0, len(numbers) - 1, 2):
        try:
            coords.append((float(numbers[i]), float(numbers[i + 1])))
        except (ValueError, IndexError):
            pass
    return coords


# ─── Helper functions ───────────────────────────────────────────────

def save_mask_as_pbm(mask: np.ndarray, path: str):
    """Save a boolean mask as PBM (portable bitmap) for potrace."""
    h, w = mask.shape
    # PBM: P1 format (ASCII), 1 = black, 0 = white
    # Potrace traces black pixels, so invert: foreground (True) → 1
    with open(path, "w") as f:
        f.write(f"P1\n{w} {h}\n")
        for row in mask:
            f.write(" ".join("1" if px else "0" for px in row) + "\n")


def extract_potrace_paths(svg_path: str) -> list[str]:
    """Extract SVG path 'd' attributes from potrace SVG output."""
    import xml.etree.ElementTree as ET
    
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        ns = {"svg": "http://www.w3.org/2000/svg"}
        
        paths = []
        # potrace outputs paths inside a group
        for path_el in root.iter("{http://www.w3.org/2000/svg}path"):
            d = path_el.get("d")
            if d:
                paths.append(d)
        
        # Also check without namespace (potrace sometimes omits it)
        if not paths:
            for path_el in root.iter("path"):
                d = path_el.get("d")
                if d:
                    paths.append(d)
        
        return paths
    except Exception as e:
        logger.warning(f"Failed to parse SVG: {e}")
        return []


def build_inkstitch_svg(
    svg_paths: list[dict],
    width_px: int,
    height_px: int,
    px_per_mm: float,
    stitch_params: dict,
) -> str:
    """
    Build an SVG document with inkstitch namespace attributes for each color region.
    
    Potrace outputs paths in pixel coordinates. We need to set the SVG viewBox
    and dimensions in mm so Ink/Stitch knows the physical size.
    """
    width_mm = width_px / px_per_mm
    height_mm = height_px / px_per_mm
    
    # Build stitch param attributes string
    param_attrs = " ".join(f'{k}="{v}"' for k, v in stitch_params.items())
    
    paths_xml = []
    for region in svg_paths:
        color = region["color"]
        for j, path_d in enumerate(region["paths"]):
            path_id = f"region_{region['index']}_{j}"
            # Ink/Stitch reads fill color for thread assignment
            # and inkstitch:* attributes for stitch parameters
            paths_xml.append(
                f'  <path id="{path_id}" '
                f'style="fill:{color};stroke:none;fill-opacity:1" '
                f'd="{path_d}" '
                f'{param_attrs} />'
            )
    
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkstitch="http://inkstitch.org/namespace"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="{width_mm}mm"
     height="{height_mm}mm"
     viewBox="0 0 {width_px} {height_px}">
{chr(10).join(paths_xml)}
</svg>"""
    
    return svg


def extract_pes_from_zip(zip_bytes: bytes) -> Optional[bytes]:
    """Extract .pes file from Ink/Stitch zip output."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        for name in zf.namelist():
            if name.lower().endswith(".pes"):
                return zf.read(name)
        # If no .pes, return first file
        if zf.namelist():
            return zf.read(zf.namelist()[0])
    except Exception as e:
        logger.warning(f"Failed to extract from zip: {e}")
    return None


def order_colors_by_mapping(
    detected: np.ndarray, thread_colors: list[str]
) -> list[np.ndarray]:
    """Order detected colors to match the provided thread color list."""
    from colorsys import rgb_to_hsv
    
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    
    def color_distance(c1, c2):
        return sum((a - b) ** 2 for a, b in zip(c1, c2))
    
    ordered = []
    remaining = list(detected)
    
    for hex_color in thread_colors:
        target = hex_to_rgb(hex_color)
        if not remaining:
            break
        # Find closest remaining color
        best_idx = min(range(len(remaining)), key=lambda i: color_distance(tuple(remaining[i]), target))
        ordered.append(remaining.pop(best_idx))
    
    # Append any unmatched colors
    ordered.extend(remaining)
    return ordered


def sort_colors_by_area(
    arr: np.ndarray, colors: np.ndarray, fg_mask: np.ndarray
) -> list[np.ndarray]:
    """Sort colors by pixel count (largest area first) — typical embroidery order."""
    counts = []
    for color in colors:
        mask = np.all(arr == color, axis=2) & fg_mask
        counts.append(np.sum(mask))
    
    indices = np.argsort(counts)[::-1]
    return [colors[i] for i in indices]
