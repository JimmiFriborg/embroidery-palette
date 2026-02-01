"""
Appwrite Python Function: Image Processing (Phase 2 Pipeline)
Handles preprocessing, shape analysis, and region extraction for embroidery conversion.

Uses scikit-image + PIL + numpy (no OpenCV dependency).
"""

import os
import io
import json
import sys
import numpy as np
from PIL import Image, ImageDraw
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
    """
    try:
        # Parse request body - try all Appwrite 1.8 body accessors
        payload = {}
        
        # Try body_text first (Appwrite 1.8 snake_case), then bodyText, then body
        for attr in ['body_text', 'bodyText', 'body_raw', 'bodyRaw', 'body']:
            try:
                val = getattr(context.req, attr, None)
                if val and isinstance(val, str) and val.strip():
                    payload = json.loads(val)
                    context.log(f"Parsed payload from {attr}")
                    break
            except Exception:
                continue
        
        # Try body_json / bodyJson (already parsed dict)
        if not payload:
            for attr in ['body_json', 'bodyJson']:
                try:
                    val = getattr(context.req, attr, None)
                    if val and isinstance(val, dict):
                        payload = val
                        context.log(f"Parsed payload from {attr}")
                        break
                except Exception:
                    continue
        
        # Unwrap { data: "..." } wrapper if present
        if isinstance(payload, dict) and 'data' in payload and isinstance(payload['data'], str):
            try:
                payload = json.loads(payload['data'])
                context.log("Unwrapped data wrapper")
            except Exception:
                pass
        
        context.log(f"Payload: {json.dumps(payload) if isinstance(payload, dict) else str(payload)}")
        
        project_id = payload.get('projectId') if isinstance(payload, dict) else None
        image_id = payload.get('imageId') if isinstance(payload, dict) else None
        thread_count = payload.get('threadCount', 6) if isinstance(payload, dict) else 6
        hoop_size = payload.get('hoopSize', '100x100') if isinstance(payload, dict) else '100x100'
        
        if not project_id or not image_id:
            return context.res.json({
                'success': False,
                'error': 'Missing projectId or imageId'
            }, 400)
        
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
        
        image = Image.open(io.BytesIO(file_data))
        image_np = np.array(image.convert('RGB'))
        
        context.log(f'Image loaded: {image_np.shape[1]}x{image_np.shape[0]} px')
        
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
    """Process image using Phase 2 digitizing pipeline."""
    context.log('=== Using Phase 2 Digitizing Pipeline ===')
    
    # Stage 1: Preprocess image
    context.log('Stage 1: Preprocessing for embroidery...')
    preprocessed, alpha_mask, dimensions = preprocess_for_embroidery(
        image_np, 
        hoop_size=hoop_size,
        use_grabcut=True
    )
    
    context.log(f'  Preprocessed to {dimensions["width_mm"]:.1f}x{dimensions["height_mm"]:.1f}mm')
    
    # Stage 2: Extract regions with color quantization
    context.log(f'Stage 2: Extracting {thread_count} color regions...')
    regions, quantized_image, color_palette = extract_regions(
        preprocessed,
        n_colors=thread_count,
        alpha_mask=alpha_mask,
        min_area_mm2=2.0
    )
    
    context.log(f'  Found {len(regions)} regions')
    
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
    """Generate a preview image showing extracted contours using PIL."""
    h, w = quantized_image.shape[:2]
    
    outline_pil = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(outline_pil)
    
    for region in regions:
        color = hex_to_rgb(region.color)
        
        for contour in region.contours:
            if len(contour) < 2:
                continue
            
            # Convert contour to list of tuples for PIL
            points = [(int(p[0]), int(p[1])) for p in contour]
            
            if region.region_type == 'fill':
                width = 2
            elif region.region_type == 'outline':
                width = 1
            else:
                width = 1
            
            # Draw polygon outline
            if len(points) >= 3:
                draw.polygon(points, outline=color, width=width)
            else:
                draw.line(points, fill=color, width=width)
    
    return np.array(outline_pil)


def serialize_regions(regions):
    """Convert Region objects to JSON-serializable format."""
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
    """Legacy processing fallback using PIL only."""
    context.log('Using legacy processing...')
    
    # Quantize colors using PIL
    context.log(f'Quantizing to {thread_count} colors...')
    quantized_np, colors = quantize_colors_pil(image_np, thread_count)
    
    # Resize for hoop
    context.log(f'Sizing for {hoop_size} hoop...')
    final_np = resize_for_hoop(quantized_np, hoop_size)
    
    # Save processed image
    processed_image = Image.fromarray(final_np)
    buffer = io.BytesIO()
    processed_image.save(buffer, format='PNG')
    buffer.seek(0)
    
    context.log('Uploading processed image...')
    processed_file = storage.create_file(
        bucket_id='project_images',
        file_id='unique()',
        file=InputFile.from_bytes(buffer.read(), f'{project_id}_processed.png')
    )
    
    color_hex_list = [rgb_to_hex(c) for c in colors]
    
    context.log('Updating project...')
    databases.update_document(
        database_id='newstitchdb',
        collection_id='projects',
        document_id=project_id,
        data={
            'processedImageId': processed_file['$id'],
            'status': 'ready',
            'extractedColors': color_hex_list
        }
    )
    
    return {
        'success': True,
        'processedImageId': processed_file['$id'],
        'outlineImageId': None,
        'extractedColors': color_hex_list,
        'colorCount': len(colors),
        'contourCount': 0,
        'pipeline': 'legacy'
    }


def quantize_colors_pil(image_np, n_colors):
    """Color quantization using PIL."""
    image = Image.fromarray(image_np)
    quantized = image.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    
    palette = quantized.getpalette()
    colors = []
    for i in range(n_colors):
        colors.append([palette[i*3], palette[i*3+1], palette[i*3+2]])
    
    return np.array(quantized.convert('RGB')), colors


def resize_for_hoop(image_np, hoop_size):
    """Resize image to fit within hoop safe area."""
    safe_areas = {'100x100': (900, 900), '70x70': (620, 620)}
    full_sizes = {'100x100': (1000, 1000), '70x70': (700, 700)}
    
    safe_size = safe_areas.get(hoop_size, (900, 900))
    full_size = full_sizes.get(hoop_size, (1000, 1000))
    
    image = Image.fromarray(image_np)
    image.thumbnail(safe_size, Image.Resampling.LANCZOS)
    
    canvas = Image.new('RGB', full_size, (255, 255, 255))
    offset = ((full_size[0] - image.width) // 2, (full_size[1] - image.height) // 2)
    canvas.paste(image, offset)
    
    return np.array(canvas)


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
