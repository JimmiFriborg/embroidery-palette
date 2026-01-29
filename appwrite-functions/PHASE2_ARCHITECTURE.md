# Phase 2: Proper PP1 Embroidery Digitizing

## What Changed

**Before (Phase 1 - Lovable's approach):**
```
Image → K-means quantization → Pass to pyembroidery → Hope for the best
```
❌ Problem: Treats embroidery like "print pixels with thread"

**After (Phase 2 - Proper digitizing):**
```
Image → Preprocessing → Shape extraction → Stitch planning → Stitch generation → PES
```
✅ Solution: Understands structure, plans intelligently, stitches predictably

---

## New Modules Created

### 📁 `/appwrite-functions/lib/`

All modules are in a shared `lib/` directory for reuse across functions.

#### **1. `image_preprocess.py`** (301 lines)
- Bilateral filtering (preserve edges, kill noise)
- GrabCut background removal (with threshold fallback)
- Safe area enforcement (90×90mm for 100×100 hoop)
- Aspect-ratio-preserving resize
- Hoop centering

**Key improvement:** No more raw image → stitch. Now we clean and prepare first.

---

#### **2. `shape_analyzer.py`** (366 lines)
- Extract contours per color
- Classify regions: fill / outline / detail
- Calculate principal angles (for stitch direction)
- Filter noise (< 2mm² areas, < 3mm perimeters)
- Simplify contours (Douglas-Peucker)

**Key improvement:** We now understand "this is a large area that needs filling" vs "this is a thin line that needs outlining."

**Region classification logic:**
```python
if compactness < 0.1 or aspect_ratio > 8:
    → 'outline' (thin stroke, bean stitch only)
elif area_mm2 < 5.0:
    → 'detail' (small element, light fill)
else:
    → 'fill' (large area, scanline fill + outline)
```

---

#### **3. `stitch_planner.py`** (385 lines)
- Determines stitch strategy per region
- Calculates density, angles, underlay needs
- Estimates stitch count & sewing time
- Quality presets: fast / balanced / quality
- PP1 compatibility validation

**Key improvement:** We make intelligent decisions before generating stitches.

**PP1-optimized defaults:**
- Fill density: 5 stitches/mm (vs. 7-10 for industrial machines)
- Outline: Bean stitch (3× run) at ~2mm per stitch
- Underlay: Only for fills > 50mm² (prevents puckering)
- Target stitch length: 2.0mm (PP1 sweet spot)
- Max recommended stitches: 15,000 (warns user)

---

#### **4. `stitch_generator.py`** (349 lines)
- Scanline fill algorithm (reliable, predictable)
- Bean stitch for outlines (3× for clarity)
- Adaptive stitch length (1-3.5mm)
- Travel optimization (minimize jumps)
- Outputs `pyembroidery.EmbPattern`

**Key improvement:** Actual digitizing algorithms instead of hoping pyembroidery figures it out.

**Scanline fill:**
1. Rotate region to align with stitch angle
2. Generate horizontal scanlines (density-based spacing)
3. Find intersections with contour
4. Stitch along scanlines (zigzag pattern)
5. Rotate back

**Bean stitch (outline):**
1. Forward pass along contour
2. Backward pass (reinforcement)
3. Forward pass again
Result: 3× coverage = strong, visible outline

---

## How It Works Now

### **Updated process-image function:**
```python
# Old way:
image → K-means → resize → upload

# New way:
image → bilateral filter
      → GrabCut background removal
      → crop to content
      → resize to safe area (with margins)
      → center in hoop
      → K-means quantization
      → extract & classify regions
      → upload processed image + region metadata
```

### **Updated generate-pes function:**
```python
# Old way:
processed_image → pass to pyembroidery → hope

# New way:
region metadata → stitch planning
                → quality preset selection
                → density calculation
                → stitch generation (scanline fill + bean outlines)
                → pyembroidery export
                → preview generation
```

---

## PP1-Specific Optimizations

### ✅ **Safe Area Enforcement**
- 100×100mm hoop → 90×90mm embroidery area (5mm margin)
- 70×70mm hoop → 60-65mm embroidery area
- Prevents edge distortion and hoop flex

### ✅ **Lower Stitch Density**
- 5 stitches/mm (vs. 7-10 for industrial)
- Faster sewing, fewer thread breaks
- Still produces quality embroidery

### ✅ **Bean Stitch Outlines**
- 3× run instead of complex satin
- Better for thin features
- Consistent with PP1's hobbyist focus

### ✅ **Predictable Results**
- Same image → same stitches every time
- No random "creativity" from AI
- Users know what they're getting

### ✅ **Underlay Strategy**
- Only for large fills (> 50mm²)
- Half density, perpendicular angle
- Prevents fabric distortion

### ✅ **Stitch Count Management**
- Warns at 15k stitches
- Hard limit at 20k (PP1 max)
- Encourages simplification when needed

---

## Quality Presets

Users can choose trade-offs:

| Preset | Density | Underlay | Use Case |
|--------|---------|----------|----------|
| **Fast** | 80% (4/mm) | Never | Quick tests, simple designs |
| **Balanced** | 100% (5/mm) | Selective | General use (default) |
| **Quality** | 120% (6/mm) | Frequent | Complex designs, show pieces |

---

## Implementation Status

### ✅ **Completed (Today)**
- [x] Image preprocessing module
- [x] Shape analyzer module
- [x] Stitch planner module
- [x] Stitch generator module
- [x] Architecture documentation

### ⏳ **Next Steps (Phase 2b)**
1. Update `process-image` function to use new preprocessing + shape analysis
2. Update `generate-pes` function to use new planner + generator
3. Test with real images
4. Deploy updated functions to Appwrite
5. Update frontend to show stitch plan preview

### 📋 **To-Do (Phase 2c - UI)**
- [ ] Show stitch plan before export (color layers, estimated time)
- [ ] Add density slider (0.5× to 2×)
- [ ] Display stitch count + time estimate
- [ ] Warning messages for high stitch counts
- [ ] Per-region angle override (advanced feature)

---

## Comparison to Analysis Requirements

Your analysis said you need these stages. Here's how we match up:

| Stage | Required | Status |
|-------|----------|--------|
| **A: Image Preprocessing** | ✅ | ✅ Bilateral filter, GrabCut, morphological ops |
| **B: Contour Extraction** | ✅ | ✅ OpenCV contours, filtering, simplification |
| **C: Vectorization** | ✅ | ✅ Douglas-Peucker simplification |
| **D: Stitch Conversion** | ✅ | ✅ Bean stitch outlines, scanline fills, adaptive length |

**Result:** We're aligned with the analysis recommendations! 🎯

---

## File Structure

```
embroidery-palette/
├── appwrite-functions/
│   ├── lib/                          # ← NEW: Shared modules
│   │   ├── README.md                 # Module documentation
│   │   ├── image_preprocess.py       # Stage 1: Clean & prep
│   │   ├── shape_analyzer.py         # Stage 3: Extract & classify
│   │   ├── stitch_planner.py         # Stage 4: Plan strategy
│   │   └── stitch_generator.py       # Stage 5: Generate stitches
│   ├── process-image/
│   │   ├── main.py                   # ← TO UPDATE
│   │   └── requirements.txt
│   └── generate-pes/
│       ├── main.py                   # ← TO UPDATE
│       └── requirements.txt
└── PHASE2_ARCHITECTURE.md            # ← This file
```

---

## Testing Strategy

### Unit Tests (to be added)
```python
# Test preprocessing
def test_preprocess():
    image = load_test_image('simple_logo.png')
    cleaned, mask, meta = preprocess_for_embroidery(image)
    assert meta['safe_area_mm'] == (90, 90)
    assert np.count_nonzero(mask) > 0

# Test shape extraction
def test_extract_regions():
    quantized = create_test_quantized_image()
    regions = extract_regions(quantized, colors, mask)
    assert len(regions) > 0
    assert all(r.type in ['fill', 'outline', 'detail'] for r in regions)

# Test stitch planning
def test_plan_stitches():
    regions = create_test_regions()
    plan = plan_stitches(regions)
    assert plan.total_stitches < 20000  # PP1 limit
    assert len(plan.warnings) == 0
```

### Integration Test
```python
# Full pipeline test
def test_full_pipeline():
    image = load_image('test_design.png')
    # ... run through all stages ...
    pattern = generate_stitches(plan)
    write_pes(pattern, 'test_output.pes')
    assert os.path.exists('test_output.pes')
```

---

## Next: Integration

Ready to integrate these modules into the Appwrite functions?

**Steps:**
1. Update `process-image/main.py` to use new preprocessing + shape analysis
2. Update `generate-pes/main.py` to use new planner + generator
3. Update `requirements.txt` (no new dependencies needed!)
4. Deploy to Appwrite
5. Test with frontend

Say the word and I'll do the integration! 🚀
