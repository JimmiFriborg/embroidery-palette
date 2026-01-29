# StitchCraft Phase 2: Proper Digitizing Pipeline

## Architecture Overview

This is a **proper but pragmatic** embroidery digitizing pipeline optimized for the Brother PP1 hobbyist embroidery machine.

### Design Philosophy

1. **PP1-first:** Low density, clear outlines, predictable results
2. **Extract shapes, not pixels:** Understand structure before stitching
3. **Reliable over realistic:** Clarity beats photorealism
4. **Not overengineered:** Use proven algorithms, don't reinvent CV

---

## Pipeline Stages

```
Input Image
    ↓
┌─────────────────────────────────────┐
│ 1. Image Preprocessing              │
│    (image_preprocess.py)             │
├─────────────────────────────────────┤
│ • Bilateral filter (noise removal)  │
│ • Background removal (GrabCut)      │
│ • Safe area calculation             │
│ • Resize & center in hoop           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Color Quantization               │
│    (existing K-means in LAB)         │
├─────────────────────────────────────┤
│ • Reduce to N thread colors         │
│ • Match to Brother palette          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Shape Analysis                   │
│    (shape_analyzer.py)               │
├─────────────────────────────────────┤
│ • Extract contours per color        │
│ • Classify: fill/outline/detail     │
│ • Calculate principal angles        │
│ • Filter noise (< 2mm²)             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. Stitch Planning                  │
│    (stitch_planner.py)               │
├─────────────────────────────────────┤
│ • Determine stitch type per region  │
│ • Calculate density & angle         │
│ • Plan underlay (for large fills)   │
│ • Estimate stitch count & time      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 5. Stitch Generation                │
│    (stitch_generator.py)             │
├─────────────────────────────────────┤
│ • Scanline fill for regions         │
│ • Bean stitch for outlines          │
│ • Travel optimization               │
│ • Generate EmbPattern               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 6. PES Export                       │
│    (pyembroidery)                    │
├─────────────────────────────────────┤
│ • Write .pes file                   │
│ • Generate preview image            │
└─────────────────────────────────────┘
    ↓
Output: .pes file + preview
```

---

## Module Documentation

### `image_preprocess.py`

**Purpose:** Clean and prepare images for digitizing

**Key Functions:**
- `preprocess_for_embroidery()` - Main entry point
- `remove_background_grabcut()` - Smart background removal
- `remove_background_threshold()` - Fast fallback
- `crop_to_content()` - Intelligent cropping
- `resize_to_safe_area()` - Fit to hoop with margins

**Output:** Cleaned image + alpha mask + metadata

**PP1 Optimization:**
- Safe area = hoop - 5mm margin (90×90 for 100×100 hoop)
- Preserves aspect ratio
- White background (easy to see on fabric)

---

### `shape_analyzer.py`

**Purpose:** Extract and classify regions for intelligent stitching

**Key Classes:**
- `Region` - A single embroidery region with metadata

**Key Functions:**
- `extract_regions()` - Main entry point
- `classify_region()` - Determine fill/outline/detail
- `calculate_principal_angle()` - For stitch direction
- `filter_overlapping_regions()` - Clean up artifacts

**Classification Logic:**
```python
if compactness < 0.1 or aspect_ratio > 8:
    return 'outline'  # Thin stroke
elif area_mm2 < 5.0:
    return 'detail'   # Small element
else:
    return 'fill'     # Large area
```

**Output:** List of `Region` objects with:
- Color
- Type (fill/outline/detail)
- Simplified contours
- Principal angle (for stitching)
- Area, perimeter, complexity metrics

---

### `stitch_planner.py`

**Purpose:** Determine optimal stitch strategy per region

**Key Classes:**
- `StitchOperation` - Single stitch operation
- `StitchLayer` - All operations for one thread color
- `StitchPlan` - Complete design plan

**Key Functions:**
- `plan_stitches()` - Main entry point
- `plan_region_operations()` - Strategy per region
- `estimate_fill_stitches()` - Stitch count prediction
- `validate_plan()` - PP1 compatibility checks

**PP1 Defaults:**
```python
{
    'fill_density': 5.0,           # stitches/mm
    'outline_density': 0.5,        # ~2mm per stitch
    'bean_stitch_repeat': 3,       # 3× for clarity
    'stitch_length_target': 2.0,   # mm (PP1 sweet spot)
    'underlay_threshold_mm2': 50,  # Use underlay for fills > 50mm²
    'max_recommended_stitches': 15000
}
```

**Quality Presets:**
- `fast` - 80% density, no underlay
- `balanced` - 100% density, selective underlay
- `quality` - 120% density, frequent underlay

---

### `stitch_generator.py`

**Purpose:** Convert stitch plan to actual coordinates

**Key Functions:**
- `generate_stitches()` - Main entry point
- `generate_fill_stitches()` - Scanline fill algorithm
- `generate_outline_stitches()` - Bean stitch (3× run)
- `scanline_fill()` - Core fill algorithm
- `subdivide_contour()` - Even stitch spacing

**Scanline Fill Algorithm:**
1. Rotate region to align with stitch angle
2. Generate horizontal scanlines (spaced by density)
3. Find intersections with contour
4. Generate stitches along scanlines
5. Alternate direction (zigzag for efficiency)
6. Rotate back to original orientation

**Bean Stitch (Outline):**
1. Subdivide contour into even segments (~2mm)
2. Pass 1: Forward along contour
3. Pass 2: Backward (reinforcement)
4. Pass 3: Forward again
Result: Strong, visible outline (3× coverage)

**Output:** `pyembroidery.EmbPattern` ready for PES export

---

## PP1-Specific Optimizations

### Safe Area Enforcement
- 100×100mm hoop → 90×90mm safe area (5mm margin)
- 70×70mm hoop → 60-65mm safe area
- Prevents edge distortion and registration errors

### Stitch Density
- Default: 5 stitches/mm (vs. 7-10 for industrial)
- Lower density = faster sewing, fewer breaks
- Still produces clear, quality embroidery

### Stitch Length
- Target: 2.0mm (PP1 sweet spot)
- Min: 1.0mm (tight curves)
- Max: 3.5mm (straight runs)

### Bean Stitch Outlines
- 3× run provides clarity without bulk
- Better than satin for thin features
- Consistent with PP1's hobbyist focus

### Underlay Strategy
- Only for large fills (> 50mm²)
- Half density, perpendicular angle
- Prevents fabric distortion

### Stitch Count Limits
- Warn at 15k stitches
- Hard limit at 20k (PP1 maximum)
- Encourage users to simplify if needed

---

## Usage Example

```python
from lib.image_preprocess import preprocess_for_embroidery
from lib.shape_analyzer import extract_regions
from lib.stitch_planner import plan_stitches
from lib.stitch_generator import generate_stitches
import pyembroidery

# 1. Preprocess
image_clean, mask, metadata = preprocess_for_embroidery(
    image_np,
    hoop_size='100x100',
    safe_margin_mm=5.0
)

# 2. Quantize colors (existing logic)
quantized, colors = quantize_colors(image_clean, n_colors=6)

# 3. Extract regions
regions = extract_regions(
    quantized,
    colors,
    mask,
    pixels_per_mm=10.0,
    min_area_mm2=2.0
)

# 4. Plan stitches
plan = plan_stitches(
    regions,
    hoop_size='100x100',
    density_multiplier=1.0,
    quality_preset='balanced'
)

# 5. Generate stitches
pattern = generate_stitches(plan, pixels_per_mm=10.0)

# 6. Export PES
pyembroidery.write_pes(pattern, 'output.pes')
```

---

## Future Enhancements

### Short-term (Phase 2b)
- [ ] Add satin stitch for columns (>1.2mm wide)
- [ ] Implement travel path optimization (TSP)
- [ ] Improve underlay angle calculation
- [ ] Add manual density slider in UI

### Medium-term (Phase 3)
- [ ] Advanced edge detection (ML-based)
- [ ] Stitch direction visualization in preview
- [ ] Per-region parameter override
- [ ] Template/preset system

### Long-term (Phase 4)
- [ ] Photo-realistic mode (higher density)
- [ ] Appliqué support
- [ ] Custom thread libraries
- [ ] Batch processing

---

## Credits & Inspiration

**Algorithms inspired by:**
- Ink/Stitch (GPL - concepts only, clean-room implementation)
- PEmbroider (Processing/Java - educational reference)
- Academic papers on embroidery digitizing

**Clean-room implementation:** All code written from scratch based on algorithmic understanding, not copied from GPL projects.

**Tools used:**
- OpenCV (BSD) - Image processing
- NumPy (BSD) - Math operations
- pyembroidery (MIT) - File format handling
