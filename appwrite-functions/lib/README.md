# StitchFlow Digitizing Pipeline

## Architecture Overview

The pipeline uses **Ink/Stitch as the primary stitch generation engine**. Custom modules handle only preprocessing and analysis — all stitch planning, underlay, satin columns, and PES export are delegated to the InkStitch microservice.

### Pipeline

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
│ 4. InkStitch Microservice           │
│    (inkstitch-service)               │
├─────────────────────────────────────┤
│ • Receives processed image          │
│ • Converts to SVG with potrace      │
│ • Applies Ink/Stitch stitch params  │
│   (underlay, satin, pull comp.)     │
│ • Exports .pes file                 │
└─────────────────────────────────────┘
    ↓
Output: .pes file + preview
```

## Modules

### `image_preprocess.py`
Cleans and prepares images for digitizing. Handles background removal, noise filtering, and hoop-aware resizing.

### `shape_analyzer.py`
Extracts contours and classifies regions (fill/outline/detail) for frontend display and color mapping.

### InkStitch Microservice (`inkstitch-service/`)
Separate Docker service that handles all stitch generation using Ink/Stitch's proven algorithms for fill stitches, satin columns, underlay, and pull compensation. See `inkstitch-service/README.md`.

## PP1-Specific Settings
- **Safe area:** 100×100mm hoop → 90×90mm (5mm margin)
- **Stitch count warning:** 15,000 stitches
- **Default density:** 5 stitches/mm
