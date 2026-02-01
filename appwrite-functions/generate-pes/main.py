"""
Appwrite Python Function: PES File Generation (Phase 2 Pipeline)
Generates Brother PES embroidery files using the proper digitizing pipeline.

Deploy to Appwrite with:
  appwrite functions create --functionId generate-pes --name "Generate PES" --runtime python-3.11
  appwrite functions createDeployment --functionId generate-pes --entrypoint main.py --code .

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
    from shape_analyzer import extract_regions
    from stitch_planner import plan_stitches, QualityPreset
    from stitch_generator import generate_stitches
    PHASE2_AVAILABLE = True
except ImportError as e:
    PHASE2_AVAILABLE = False
    PHASE2_ERROR = str(e)

# pyembroidery for PES generation
try:
    import pyembroidery
except ImportError:
    pyembroidery = None

# No OpenCV needed - using scikit-image + PIL


# Brother thread database
BROTHER_THREADS = {
    '#FFFFFF': ('001', 'White'),
    '#000000': ('900', 'Black'),
    '#FF0000': ('202', 'Red'),
    '#00FF00': ('208', 'Kelly Green'),
    '#0000FF': ('406', 'Royal Blue'),
    '#FFFF00': ('512', 'Bright Yellow'),
    '#FF00FF': ('810', 'Magenta'),
    '#00FFFF': ('613', 'Aqua'),
    '#FFA500': ('208', 'Orange'),
    '#800080': ('614', 'Purple'),
    '#FFC0CB': ('086', 'Pink'),
    '#8B4513': ('459', 'Medium Brown'),
    '#808080': ('415', 'Medium Gray'),
    '#FFD700': ('214', 'Gold'),
    '#228B22': ('232', 'Forest Green'),
}


def main(context):
    """
    Main entry point for Appwrite function.
    
    Expected payload:
    {
        "projectId": "document_id",
        "colorMappings": [
            {"originalColor": "#FF0000", "threadNumber": "202", "threadName": "Red", "threadColor": "#FF0000"}
        ],
        "hoopSize": "100x100",
        "qualityPreset": "balanced",  // "fast", "balanced", "quality"
        "density": 5.0  // Optional override (stitches/mm)
    }
    """
    if pyembroidery is None:
        return context.res.json({
            'success': False,
            'error': 'pyembroidery not installed'
        }, 500)
    
    try:
        # Parse request
        payload = json.loads(context.req.body) if context.req.body else {}
        
        project_id = payload.get('projectId')
        color_mappings = payload.get('colorMappings', [])
        hoop_size = payload.get('hoopSize', '100x100')
        quality_preset = payload.get('qualityPreset', 'balanced')
        density_override = payload.get('density')
        
        if not project_id:
            return context.res.json({
                'success': False,
                'error': 'Missing projectId'
            }, 400)
        
        # Check Phase 2 availability
        if not PHASE2_AVAILABLE:
            context.log(f'Phase 2 modules not available: {PHASE2_ERROR}')
            context.log('Falling back to legacy PES generation...')
        
        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://cloud.appwrite.io/v1'))
        client.set_project(os.environ.get('APPWRITE_PROJECT_ID'))
        client.set_key(os.environ.get('APPWRITE_API_KEY'))
        
        storage = Storage(client)
        databases = Databases(client)
        
        # Get project data
        context.log('Fetching project...')
        project = databases.get_document(
            database_id='newstitchdb',
            collection_id='projects',
            document_id=project_id
        )
        
        processed_image_id = project.get('processedImageId')
        if not processed_image_id:
            return context.res.json({
                'success': False,
                'error': 'No processed image found. Process image first.'
            }, 400)
        
        # Download processed image
        context.log('Downloading processed image...')
        file_data = storage.get_file_download(
            bucket_id='project_images',
            file_id=processed_image_id
        )
        
        image = Image.open(io.BytesIO(file_data)).convert('RGB')
        image_np = np.array(image)
        
        context.log(f'Image loaded: {image_np.shape[1]}x{image_np.shape[0]} px')
        
        # Generate PES using appropriate pipeline
        if PHASE2_AVAILABLE:
            result = generate_pes_phase2(
                context, image_np, color_mappings, hoop_size,
                quality_preset, density_override, project.get('name', 'Design')
            )
        else:
            result = generate_pes_legacy(
                context, image_np, color_mappings, hoop_size,
                project.get('name', 'Design')
            )
        
        if not result['success']:
            return context.res.json(result, 500)
        
        pes_data = result['pes_data']
        stats = result.get('stats', {})
        
        # Upload PES file
        context.log('Uploading PES file...')
        pes_file = storage.create_file(
            bucket_id='pes_files',
            file_id='unique()',
            file=InputFile.from_bytes(pes_data, f'{project.get("name", "design")}.pes')
        )
        
        # Generate stitch preview
        context.log('Generating preview...')
        preview_data = generate_preview(pes_data)
        
        preview_file = None
        if preview_data:
            preview_file = storage.create_file(
                bucket_id='stitch_previews',
                file_id='unique()',
                file=InputFile.from_bytes(preview_data, f'{project_id}_preview.png')
            )
        
        # Update project
        update_data = {
            'pesFileId': pes_file['$id'],
            'status': 'exported'
        }
        if preview_file:
            update_data['previewImageId'] = preview_file['$id']
        
        databases.update_document(
            database_id='newstitchdb',
            collection_id='projects',
            document_id=project_id,
            data=update_data
        )
        
        context.log('=== PES Generation Complete ===')
        
        return context.res.json({
            'success': True,
            'pesFileId': pes_file['$id'],
            'previewImageId': preview_file['$id'] if preview_file else None,
            'stats': stats,
            'pipeline': 'phase2' if PHASE2_AVAILABLE else 'legacy'
        })
        
    except Exception as e:
        context.error(f'PES generation error: {str(e)}')
        import traceback
        context.error(traceback.format_exc())
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def generate_pes_phase2(context, image_np, color_mappings, hoop_size, quality_preset, density_override, design_name):
    """
    Generate PES using Phase 2 digitizing pipeline.
    
    Pipeline stages:
    1. Extract regions from quantized image
    2. Plan stitches (type, angle, density per region)
    3. Generate actual stitch coordinates
    4. Export to PES format
    """
    context.log('=== Using Phase 2 PES Generation ===')
    
    # Map quality preset
    preset_map = {
        'fast': QualityPreset.FAST,
        'balanced': QualityPreset.BALANCED,
        'quality': QualityPreset.QUALITY
    }
    preset = preset_map.get(quality_preset, QualityPreset.BALANCED)
    
    context.log(f'Quality preset: {quality_preset}')
    
    # Stage 1: Extract regions
    context.log('Stage 1: Extracting regions...')
    n_colors = len(color_mappings) if color_mappings else 6
    regions, quantized_image, color_palette = extract_regions(
        image_np,
        n_colors=n_colors,
        min_area_mm2=2.0
    )
    
    context.log(f'  Found {len(regions)} regions')
    
    # Stage 2: Plan stitches
    context.log('Stage 2: Planning stitches...')
    stitch_plan = plan_stitches(
        regions,
        hoop_size=hoop_size,
        quality_preset=preset,
        density_override=density_override
    )
    
    context.log(f'  Estimated stitches: {stitch_plan.total_stitch_estimate:,}')
    context.log(f'  Estimated time: {stitch_plan.estimated_time_minutes:.1f} minutes')
    
    # Check stitch count warning
    if stitch_plan.total_stitch_estimate > 15000:
        context.log(f'  ⚠️ WARNING: High stitch count ({stitch_plan.total_stitch_estimate:,}) may strain PP1')
    
    # Stage 3: Generate stitches
    context.log('Stage 3: Generating stitch coordinates...')
    
    # Build color mapping lookup
    color_to_thread = {}
    for mapping in color_mappings:
        color_to_thread[mapping['originalColor'].upper()] = mapping
    
    pattern = generate_stitches(stitch_plan, color_to_thread)
    
    # Set metadata
    pattern.extras['name'] = design_name
    pattern.extras['author'] = 'StitchFlow Phase 2'
    
    # Stage 4: Export to PES
    context.log('Stage 4: Exporting to PES format...')
    output = io.BytesIO()
    pyembroidery.write_pes(pattern, output)
    output.seek(0)
    pes_data = output.read()
    
    # Calculate actual stats
    actual_stitch_count = len(pattern.stitches)
    
    return {
        'success': True,
        'pes_data': pes_data,
        'stats': {
            'stitch_count': actual_stitch_count,
            'estimated_time_minutes': stitch_plan.estimated_time_minutes,
            'color_count': len(stitch_plan.layers),
            'region_count': len(regions),
            'quality_preset': quality_preset,
            'warning': 'High stitch count' if actual_stitch_count > 15000 else None
        }
    }


def generate_pes_legacy(context, image_np, color_mappings, hoop_size, design_name):
    """
    Legacy PES generation when Phase 2 modules aren't available.
    """
    context.log('Using legacy PES generation...')
    
    # Hoop dimensions in mm
    hoop_dims = {
        '100x100': (100, 100),
        '70x70': (70, 70)
    }
    hoop_mm = hoop_dims.get(hoop_size, (100, 100))
    
    # Create embroidery pattern
    pattern = pyembroidery.EmbPattern()
    pattern.extras['name'] = design_name
    pattern.extras['author'] = 'StitchFlow Legacy'
    
    # Get unique colors from image
    height, width = image_np.shape[:2]
    unique_colors = get_unique_colors(image_np)
    
    context.log(f'Found {len(unique_colors)} unique colors')
    
    # Build color mapping lookup
    color_to_thread = {}
    for mapping in color_mappings:
        color_to_thread[mapping['originalColor'].upper()] = mapping
    
    # Scale factor: pixels to embroidery units (10 units = 1mm in PES)
    scale_x = (hoop_mm[0] * 10) / width
    scale_y = (hoop_mm[1] * 10) / height
    
    total_stitches = 0
    
    # Process each color
    for color_rgb in unique_colors:
        color_hex = '#{:02X}{:02X}{:02X}'.format(*color_rgb)
        
        # Skip white/background
        if color_hex == '#FFFFFF':
            continue
        
        # Get thread info
        thread_info = color_to_thread.get(color_hex, {})
        thread_color = thread_info.get('threadColor', color_hex)
        
        # Parse thread color
        thread_rgb = hex_to_rgb(thread_color)
        
        # Add thread/color change
        pattern.add_thread({
            'color': pyembroidery.EmbThread(thread_rgb[0], thread_rgb[1], thread_rgb[2]),
            'name': thread_info.get('threadName', 'Thread'),
            'catalog_number': thread_info.get('threadNumber', '000')
        })
        
        # Find all pixels of this color
        mask = np.all(image_np == color_rgb, axis=2)
        
        # Generate fill stitches
        stitches_added = generate_fill_stitches_legacy(pattern, mask, scale_x, scale_y)
        total_stitches += stitches_added
        
        # Color change
        pattern.color_change()
    
    # End pattern
    pattern.end()
    
    # Write to PES format
    output = io.BytesIO()
    pyembroidery.write_pes(pattern, output)
    output.seek(0)
    
    return {
        'success': True,
        'pes_data': output.read(),
        'stats': {
            'stitch_count': total_stitches,
            'estimated_time_minutes': total_stitches / 400,  # Rough estimate
            'color_count': len(unique_colors) - 1,  # Exclude white
            'quality_preset': 'legacy'
        }
    }


def get_unique_colors(image_np):
    """Get unique RGB colors from image."""
    pixels = image_np.reshape(-1, 3)
    unique = np.unique(pixels, axis=0)
    return [tuple(c) for c in unique]


def generate_fill_stitches_legacy(pattern, mask, scale_x, scale_y):
    """Generate fill stitches for a masked region (legacy method)."""
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return 0
    
    row_min, row_max = np.where(rows)[0][[0, -1]]
    col_min, col_max = np.where(cols)[0][[0, -1]]
    
    stitch_spacing = 3
    max_stitch_length = 40
    
    direction = 1
    first_stitch = True
    stitch_count = 0
    
    for y in range(row_min, row_max + 1, stitch_spacing):
        row_mask = mask[y, :]
        if not np.any(row_mask):
            continue
        
        x_positions = np.where(row_mask)[0]
        x_start, x_end = x_positions[0], x_positions[-1]
        
        if direction == 1:
            x_range = range(x_start, x_end + 1, max_stitch_length)
        else:
            x_range = range(x_end, x_start - 1, -max_stitch_length)
        
        for x in x_range:
            ex = int((x - mask.shape[1] / 2) * scale_x)
            ey = int((y - mask.shape[0] / 2) * scale_y)
            
            if first_stitch:
                pattern.add_stitch_absolute(pyembroidery.MOVE, ex, ey)
                first_stitch = False
            else:
                pattern.add_stitch_absolute(pyembroidery.STITCH, ex, ey)
                stitch_count += 1
        
        direction *= -1
    
    return stitch_count


def generate_preview(pes_data):
    """Generate a PNG preview of the embroidery pattern."""
    try:
        pattern = pyembroidery.read_pes(io.BytesIO(pes_data))
        output = io.BytesIO()
        pyembroidery.write_png(pattern, output)
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f'Preview generation failed: {e}')
        return None


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
