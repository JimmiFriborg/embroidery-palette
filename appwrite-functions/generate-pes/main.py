"""
Appwrite Python Function: PES File Generation
Generates Brother PES embroidery files using pyembroidery.

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
import numpy as np
from PIL import Image
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.input_file import InputFile

# pyembroidery for PES generation
try:
    import pyembroidery
except ImportError:
    pyembroidery = None


# Brother thread database (subset - add more as needed)
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
        "hoopSize": "100x100"
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
        
        if not project_id:
            return context.res.json({
                'success': False,
                'error': 'Missing projectId'
            }, 400)
        
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
        
        # Generate PES file
        context.log('Generating PES file...')
        pes_data = generate_pes(image_np, color_mappings, hoop_size, context)
        
        # Upload PES file
        context.log('Uploading PES file...')
        pes_file = storage.create_file(
            bucket_id='pes_files',
            file_id='unique()',
            file=InputFile.from_bytes(pes_data, f'{project["name"]}.pes')
        )
        
        # Generate stitch preview image
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
        
        # Get download URL
        download_url = storage.get_file_download(
            bucket_id='pes_files',
            file_id=pes_file['$id']
        )
        
        return context.res.json({
            'success': True,
            'pesFileId': pes_file['$id'],
            'previewImageId': preview_file['$id'] if preview_file else None,
            'downloadUrl': str(download_url)
        })
        
    except Exception as e:
        context.error(f'PES generation error: {str(e)}')
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def generate_pes(image_np, color_mappings, hoop_size, context):
    """
    Generate PES embroidery file from processed image.
    Uses fill stitch pattern for each color region.
    """
    # Hoop dimensions in mm
    hoop_dims = {
        '100x100': (100, 100),
        '70x70': (70, 70)
    }
    hoop_mm = hoop_dims.get(hoop_size, (100, 100))
    
    # Create embroidery pattern
    pattern = pyembroidery.EmbPattern()
    
    # Set metadata
    pattern.extras['name'] = 'StitchFlow Design'
    pattern.extras['author'] = 'StitchFlow App'
    
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
        
        # Generate fill stitches for this color region
        generate_fill_stitches(pattern, mask, scale_x, scale_y, context)
        
        # Color change
        pattern.color_change()
    
    # End pattern
    pattern.end()
    
    # Write to PES format
    output = io.BytesIO()
    pyembroidery.write_pes(pattern, output)
    output.seek(0)
    
    return output.read()


def get_unique_colors(image_np):
    """Get unique RGB colors from image."""
    pixels = image_np.reshape(-1, 3)
    unique = np.unique(pixels, axis=0)
    return [tuple(c) for c in unique]


def generate_fill_stitches(pattern, mask, scale_x, scale_y, context):
    """
    Generate fill stitches for a masked region.
    Uses horizontal line fill pattern.
    """
    # Find bounding box of masked region
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return
    
    row_min, row_max = np.where(rows)[0][[0, -1]]
    col_min, col_max = np.where(cols)[0][[0, -1]]
    
    # Stitch spacing (in pixels, adjust for density)
    stitch_spacing = 3  # Every 3 pixels vertically
    max_stitch_length = 40  # Max stitch length in pixels
    
    # Generate horizontal fill lines
    direction = 1  # Alternate direction
    first_stitch = True
    
    for y in range(row_min, row_max + 1, stitch_spacing):
        # Find x extents for this row
        row_mask = mask[y, :]
        if not np.any(row_mask):
            continue
        
        x_positions = np.where(row_mask)[0]
        x_start, x_end = x_positions[0], x_positions[-1]
        
        # Generate stitches along this line
        if direction == 1:
            x_range = range(x_start, x_end + 1, max_stitch_length)
        else:
            x_range = range(x_end, x_start - 1, -max_stitch_length)
        
        for x in x_range:
            # Convert to embroidery coordinates (centered)
            ex = int((x - mask.shape[1] / 2) * scale_x)
            ey = int((y - mask.shape[0] / 2) * scale_y)
            
            if first_stitch:
                pattern.add_stitch_absolute(pyembroidery.MOVE, ex, ey)
                first_stitch = False
            else:
                pattern.add_stitch_absolute(pyembroidery.STITCH, ex, ey)
        
        direction *= -1  # Alternate direction


def generate_preview(pes_data):
    """
    Generate a PNG preview of the embroidery pattern.
    """
    try:
        # Load PES data
        pattern = pyembroidery.read_pes(io.BytesIO(pes_data))
        
        # Render to image
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
