"""
Appwrite Python Function: Image Processing (Phase 2 Pipeline)
Handles preprocessing, shape analysis, and region extraction for embroidery conversion.

Deploy to Appwrite with:
  appwrite functions create --functionId process-image --name "Process Image" --runtime python-3.11
  appwrite functions createDeployment --functionId process-image --entrypoint main.py --code .

Required environment variables in Appwrite:
  - APPWRITE_ENDPOINT
  - APPWRITE_PROJECT_ID
  - APPWRITE_API_KEY
"""

import os
import io
import json
import sys
import numpy as np
from PIL import Image
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.input_file import InputFile

# Add lib directory to path for Phase 2 modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

# Import Phase 2 pipeline modules
try:
    from image_preprocess import preprocess_for_embroidery
    from shape_analyzer import extract_regions, Region
    PHASE2_AVAILABLE = True
except ImportError as e:
    PHASE2_AVAILABLE = False
    PHASE2_ERROR = str(e)

# Try importing OpenCV
try:
    import cv2
except ImportError:
    cv2 = None


def main(context):
    """
    Main entry point for Appwrite function.
    
    Expected payload:
    {
        "projectId": "document_id",
        "imageId": "storage_file_id", 
        "threadCount": 6,
        "hoopSize": "100x100"
    }
    
    Returns:
    {
        "success": true,
        "processedImageId": "...",
        "outlineImageId": "...",
        "extractedColors": ["#FF0000", ...],
        "colorCount": 6,
        "regionData": {...}  // Shape analysis for stitch planning
    }
    """
    try:
        # Parse request
        payload = json.loads(context.req.body) if context.req.body else {}
        
        project_id = payload.get('projectId')
        image_id = payload.get('imageId')
        thread_count = payload.get('threadCount', 6)
        hoop_size = payload.get('hoopSize', '100x100')
        
        if not project_id or not image_id:
            return context.res.json({
                'success': False,
                'error': 'Missing projectId or imageId'
            }, 400)
        
        # Check Phase 2 modules availability
        if not PHASE2_AVAILABLE:
            context.log(f'Phase 2 modules not available: {PHASE2_ERROR}')
            context.log('Falling back to legacy processing...')
        
        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
        client.set_project(os.environ.get('APPWRITE_PROJECT_ID'))
        client.set_key(os.environ.get('APPWRITE_API_KEY'))
        
        storage = Storage(client)
        databases = Databases(client)
        
        # Download original image
        context.log('Downloading original image...')
        file_data = storage.get_file_download(
            bucket_id='project_images',
            file_id=image_id
        )
        
        # Load image
        image = Image.open(io.BytesIO(file_data))
        image_np = np.array(image.convert('RGB'))
        
        context.log(f'Image loaded: {image_np.shape[1]}x{image_np.shape[0]} px')
        
        # Use Phase 2 pipeline if available
        if PHASE2_AVAILABLE:
            result = process_with_phase2(
                context, storage, databases, project_id,
                image_np, thread_count, hoop_size
            )
        else:
            result = process_legacy(
                context, storage, databases, project_id,
                image_np, thread_count, hoop_size
            )
        
        return context.res.json(result)
        
    except Exception as e:
        context.error(f'Processing error: {str(e)}')
        import traceback
        context.error(traceback.format_exc())
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def process_with_phase2(context, storage, databases, project_id, image_np, thread_count, hoop_size):
    """
    Process image using Phase 2 digitizing pipeline.
    
    Pipeline stages:
    1. Image Preprocessing (bilateral filter, background removal, safe area)
    2. Color Quantization & Region Extraction
    3. Shape Analysis (contours, classification)
    """
    context.log('=== Using Phase 2 Digitizing Pipeline ===')
    
    # Stage 1: Preprocess image
    context.log('Stage 1: Preprocessing for embroidery...')
    preprocessed, alpha_mask, dimensions = preprocess_for_embroidery(
        image_np, 
        hoop_size=hoop_size,
        use_grabcut=True
    )
    
    context.log(f'  Preprocessed to {dimensions["width_mm"]:.1f}x{dimensions["height_mm"]:.1f}mm')
    context.log(f'  Safe area: {dimensions["safe_width_mm"]}x{dimensions["safe_height_mm"]}mm')
    
    # Stage 2: Extract regions with color quantization
    context.log(f'Stage 2: Extracting {thread_count} color regions...')
    regions, quantized_image, color_palette = extract_regions(
        preprocessed,
        n_colors=thread_count,
        alpha_mask=alpha_mask,
        min_area_mm2=2.0  # Filter tiny regions
    )
    
    context.log(f'  Found {len(regions)} regions')
    
    # Count region types
    fill_count = sum(1 for r in regions if r.region_type == 'fill')
    outline_count = sum(1 for r in regions if r.region_type == 'outline')
    detail_count = sum(1 for r in regions if r.region_type == 'detail')
    context.log(f'  Types: {fill_count} fill, {outline_count} outline, {detail_count} detail')
    
    # Stage 3: Generate outline visualization
    context.log('Stage 3: Generating outline preview...')
    outline_image = generate_outline_preview(quantized_image, regions)
    
    # Upload processed image
    context.log('Uploading processed image...')
    processed_pil = Image.fromarray(quantized_image)
    buffer = io.BytesIO()
    processed_pil.save(buffer, format='PNG')
    buffer.seek(0)
    
    processed_file = storage.create_file(
        bucket_id='project_images',
        file_id='unique()',
        file=InputFile.from_bytes(buffer.read(), f'{project_id}_processed.png')
    )
    
    # Upload outline image
    outline_file_id = None
    if outline_image is not None:
        outline_pil = Image.fromarray(outline_image)
        outline_buffer = io.BytesIO()
        outline_pil.save(outline_buffer, format='PNG')
        outline_buffer.seek(0)
        
        outline_file = storage.create_file(
            bucket_id='project_images',
            file_id='unique()',
            file=InputFile.from_bytes(outline_buffer.read(), f'{project_id}_outlines.png')
        )
        outline_file_id = outline_file['$id']
    
    # Prepare region data for stitch planning
    region_data = serialize_regions(regions)
    
    # Convert color palette to hex
    color_hex_list = [rgb_to_hex(c) for c in color_palette]
    
    # Update project document
    context.log('Updating project...')
    update_data = {
        'processedImageId': processed_file['$id'],
        'status': 'ready',
        'extractedColors': color_hex_list
    }
    
    if outline_file_id:
        update_data['outlineImageId'] = outline_file_id
        update_data['contourCount'] = sum(len(r.contours) for r in regions)
    
    databases.update_document(
        database_id='newstitchdb',
        collection_id='projects',
        document_id=project_id,
        data=update_data
    )
    
    context.log('=== Phase 2 Processing Complete ===')
    
    return {
        'success': True,
        'processedImageId': processed_file['$id'],
        'outlineImageId': outline_file_id,
        'extractedColors': color_hex_list,
        'colorCount': len(color_palette),
        'contourCount': sum(len(r.contours) for r in regions),
        'regionData': region_data,
        'dimensions': dimensions,
        'pipeline': 'phase2'
    }


def generate_outline_preview(quantized_image, regions):
    """Generate a preview image showing extracted contours."""
    if cv2 is None:
        return None
    
    h, w = quantized_image.shape[:2]
    outline_image = np.ones((h, w, 3), dtype=np.uint8) * 255
    
    # Draw contours for each region
    for region in regions:
        # Use region color for contours
        color = hex_to_rgb(region.color)
        bgr_color = (color[2], color[1], color[0])  # RGB to BGR for OpenCV
        
        for contour in region.contours:
            if region.region_type == 'fill':
                # Thick line for fill regions
                cv2.drawContours(outline_image, [contour], -1, bgr_color, 2)
            elif region.region_type == 'outline':
                # Medium line for outlines
                cv2.drawContours(outline_image, [contour], -1, bgr_color, 1)
            else:
                # Thin dashed for details (draw as dots)
                cv2.drawContours(outline_image, [contour], -1, bgr_color, 1)
    
    return outline_image


def serialize_regions(regions):
    """Convert Region objects to JSON-serializable format for stitch planning."""
    return {
        'regions': [
            {
                'color': r.color,
                'type': r.region_type,
                'area_mm2': round(r.area_mm2, 2),
                'has_holes': r.has_holes,
                'contour_count': len(r.contours),
                'bounding_box': r.bounding_box,
                'principal_angle': round(r.principal_angle, 1) if r.principal_angle else 0
            }
            for r in regions
        ],
        'summary': {
            'total_regions': len(regions),
            'fill_count': sum(1 for r in regions if r.region_type == 'fill'),
            'outline_count': sum(1 for r in regions if r.region_type == 'outline'),
            'detail_count': sum(1 for r in regions if r.region_type == 'detail'),
            'total_area_mm2': round(sum(r.area_mm2 for r in regions), 2)
        }
    }


def process_legacy(context, storage, databases, project_id, image_np, thread_count, hoop_size):
    """
    Legacy processing fallback when Phase 2 modules aren't available.
    """
    context.log('Using legacy processing (Phase 2 modules not available)')
    
    # Step 1: Remove background
    context.log('Removing background...')
    processed_np = remove_background_simple(image_np)
    
    # Step 2: Extract clean outlines
    context.log('Extracting outlines...')
    outline_image, contours = extract_clean_outlines(processed_np)
    
    # Step 3: Quantize colors
    context.log(f'Quantizing to {thread_count} colors...')
    quantized_np, colors = quantize_colors(processed_np, thread_count)
    
    # Step 4: Resize for hoop with safe area
    context.log(f'Sizing for {hoop_size} hoop...')
    final_np = resize_for_hoop(quantized_np, hoop_size)
    
    # Save processed image
    processed_image = Image.fromarray(final_np)
    buffer = io.BytesIO()
    processed_image.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Upload processed image
    context.log('Uploading processed image...')
    processed_file = storage.create_file(
        bucket_id='project_images',
        file_id='unique()',
        file=InputFile.from_bytes(buffer.read(), f'{project_id}_processed.png')
    )
    
    # Upload outline image if generated
    outline_file_id = None
    if outline_image is not None:
        outline_pil = Image.fromarray(outline_image)
        outline_buffer = io.BytesIO()
        outline_pil.save(outline_buffer, format='PNG')
        outline_buffer.seek(0)
        outline_file = storage.create_file(
            bucket_id='project_images',
            file_id='unique()',
            file=InputFile.from_bytes(outline_buffer.read(), f'{project_id}_outlines.png')
        )
        outline_file_id = outline_file['$id']
    
    # Convert colors to hex
    color_hex_list = [rgb_to_hex(c) for c in colors]
    
    # Update project document
    context.log('Updating project...')
    update_data = {
        'processedImageId': processed_file['$id'],
        'status': 'ready',
        'extractedColors': color_hex_list
    }
    if outline_file_id:
        update_data['outlineImageId'] = outline_file_id
        update_data['contourCount'] = len(contours)
    
    databases.update_document(
        database_id='newstitchdb',
        collection_id='projects',
        document_id=project_id,
        data=update_data
    )
    
    return {
        'success': True,
        'processedImageId': processed_file['$id'],
        'outlineImageId': outline_file_id,
        'extractedColors': color_hex_list,
        'colorCount': len(colors),
        'contourCount': len(contours) if contours else 0,
        'pipeline': 'legacy'
    }


# ============================================================================
# Legacy helper functions (used as fallback)
# ============================================================================

def remove_background_simple(image_np):
    """Background removal using GrabCut with edge-based fallback."""
    if cv2 is None:
        return image_np
    
    h, w = image_np.shape[:2]
    
    try:
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        margin_x, margin_y = int(w * 0.1), int(h * 0.1)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        cv2.grabCut(image_np, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        result = image_np.copy()
        result[mask2 == 0] = [255, 255, 255]
        return result
        
    except Exception:
        gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image_np
        
        mask = np.zeros(gray.shape, dtype=np.uint8)
        largest_contour = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [largest_contour], -1, 255, -1)
        
        result = image_np.copy()
        result[mask == 0] = [255, 255, 255]
        return result


def extract_clean_outlines(image_np, simplify_epsilon=2.0):
    """Extract embroidery-friendly outlines using Canny + contour simplification."""
    if cv2 is None:
        return None, []
    
    h, w = image_np.shape[:2]
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    median_val = np.median(filtered)
    lower = int(max(0, 0.66 * median_val))
    upper = int(min(255, 1.33 * median_val))
    
    edges = cv2.Canny(filtered, lower, upper)
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, []
    
    min_contour_length = min(h, w) * 0.05
    simplified_contours = []
    
    for contour in contours:
        arc_length = cv2.arcLength(contour, True)
        if arc_length < min_contour_length:
            continue
        
        area = cv2.contourArea(contour)
        if area < (min_contour_length ** 2) * 0.1:
            continue
        
        epsilon = simplify_epsilon * 0.01 * arc_length
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(simplified) >= 4:
            simplified_contours.append(simplified)
    
    outline_image = np.ones((h, w, 3), dtype=np.uint8) * 255
    cv2.drawContours(outline_image, simplified_contours, -1, (0, 0, 0), 2)
    
    return outline_image, simplified_contours


def quantize_colors(image_np, n_colors):
    """Reduce image to n_colors using K-means in LAB color space."""
    if cv2 is None:
        return quantize_colors_pil(image_np, n_colors)
    
    lab_pixels = cv2.cvtColor(image_np, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(lab_pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    centers_lab = centers.reshape(1, -1, 3).astype(np.uint8)
    centers_rgb = cv2.cvtColor(centers_lab, cv2.COLOR_LAB2RGB).reshape(-1, 3)
    
    quantized = centers_rgb[labels.flatten()]
    quantized_image = quantized.reshape(image_np.shape).astype(np.uint8)
    
    return quantized_image, centers_rgb.tolist()


def quantize_colors_pil(image_np, n_colors):
    """Fallback color quantization using PIL."""
    image = Image.fromarray(image_np)
    quantized = image.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    
    palette = quantized.getpalette()
    colors = []
    for i in range(n_colors):
        colors.append([palette[i*3], palette[i*3+1], palette[i*3+2]])
    
    return np.array(quantized.convert('RGB')), colors


def resize_for_hoop(image_np, hoop_size):
    """Resize image to fit within hoop safe area."""
    safe_areas = {
        '100x100': (900, 900),
        '70x70': (620, 620)
    }
    full_sizes = {
        '100x100': (1000, 1000),
        '70x70': (700, 700)
    }
    
    safe_size = safe_areas.get(hoop_size, (900, 900))
    full_size = full_sizes.get(hoop_size, (1000, 1000))
    
    image = Image.fromarray(image_np)
    image.thumbnail(safe_size, Image.Resampling.LANCZOS)
    
    canvas = Image.new('RGB', full_size, (255, 255, 255))
    offset = ((full_size[0] - image.width) // 2, (full_size[1] - image.height) // 2)
    canvas.paste(image, offset)
    
    return np.array(canvas)


def rgb_to_hex(rgb):
    """Convert RGB list to hex string."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def hex_to_rgb(hex_color):
    """Convert hex string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
