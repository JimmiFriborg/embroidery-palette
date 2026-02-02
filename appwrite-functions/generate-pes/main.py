"""
Appwrite Function: PES File Generation
Delegates stitch generation to the InkStitch microservice.

Flow:
1. Fetch processed image from Appwrite storage
2. Send to InkStitch microservice (image → PES)
3. Upload PES + preview to storage
4. Update project document
"""

import os
import io
import json
import requests
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.input_file import InputFile

# InkStitch microservice URL (Docker internal network or LAN IP)
INKSTITCH_URL = os.environ.get("INKSTITCH_URL", "http://192.168.30.100:5021")


def main(context):
    try:
        # Parse request body
        payload = parse_payload(context)
        
        project_id = payload.get('projectId')
        color_mappings = payload.get('colorMappings', [])
        hoop_size = payload.get('hoopSize', '100x100')
        quality_preset = payload.get('qualityPreset', 'balanced')
        density_override = payload.get('density')
        
        if not project_id:
            return context.res.json({'success': False, 'error': 'Missing projectId'}, 400)
        
        # Initialize Appwrite client
        client = Client()
        client.set_endpoint(os.environ.get('APPWRITE_ENDPOINT', 'https://appwrite.friborg.uk/v1'))
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
        
        context.log(f'Image downloaded: {len(file_data)} bytes')
        
        # Build thread colors list for microservice
        thread_colors = []
        for m in color_mappings:
            if not m.get('skip'):
                thread_colors.append(m.get('threadColor', m.get('originalColor', '#000000')))
        
        # Call InkStitch microservice
        context.log(f'Calling InkStitch microservice at {INKSTITCH_URL}...')
        context.log(f'  Hoop: {hoop_size}, Quality: {quality_preset}, Colors: {len(thread_colors)}')
        
        form_data = {
            'hoop_size': (None, hoop_size),
            'quality': (None, quality_preset),
            'thread_colors': (None, json.dumps(thread_colors)),
        }
        if density_override:
            form_data['density_override'] = (None, str(density_override))
        
        files = {
            'file': ('design.png', io.BytesIO(file_data), 'image/png'),
        }
        
        response = requests.post(
            f'{INKSTITCH_URL}/image-to-pes',
            files={**files, **form_data},
            timeout=120
        )
        
        if response.status_code != 200:
            error_detail = "Unknown error"
            try:
                error_detail = response.json().get('detail', response.text[:500])
            except Exception:
                error_detail = response.text[:500]
            context.error(f'InkStitch error ({response.status_code}): {error_detail}')
            return context.res.json({
                'success': False,
                'error': f'Stitch generation failed: {error_detail}'
            }, 500)
        
        pes_data = response.content
        context.log(f'PES received: {len(pes_data)} bytes')
        
        # Upload PES file
        context.log('Uploading PES file...')
        pes_file = storage.create_file(
            bucket_id='pes_files',
            file_id='unique()',
            file=InputFile.from_bytes(pes_data, f'{project.get("name", "design")}.pes')
        )
        
        # Generate preview using pyembroidery (if available)
        preview_file = None
        try:
            import pyembroidery
            pattern = pyembroidery.read_pes(io.BytesIO(pes_data))
            if pattern and pattern.stitches:
                preview_buf = io.BytesIO()
                pyembroidery.write_png(pattern, preview_buf)
                preview_buf.seek(0)
                preview_data = preview_buf.read()
                
                if len(preview_data) > 100:  # Valid PNG
                    preview_file = storage.create_file(
                        bucket_id='stitch_previews',
                        file_id='unique()',
                        file=InputFile.from_bytes(preview_data, f'{project_id}_preview.png')
                    )
                    context.log(f'Preview generated: {len(preview_data)} bytes')
                
                stitch_count = len([s for s in pattern.stitches if s[2] == 0])  # Regular stitches
                context.log(f'Stitch count: {stitch_count}')
        except Exception as e:
            context.log(f'Preview generation skipped: {e}')
            stitch_count = 0
        
        # Update project document
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
            'stats': {
                'stitch_count': stitch_count,
                'estimated_time_minutes': round(stitch_count / 400) if stitch_count else 0,
                'color_count': len(thread_colors),
                'quality_preset': quality_preset,
            },
            'pipeline': 'inkstitch'
        })
        
    except Exception as e:
        context.error(f'PES generation error: {str(e)}')
        import traceback
        context.error(traceback.format_exc())
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def parse_payload(context):
    """Parse Appwrite function payload with fallbacks for different versions."""
    payload = {}
    for attr in ['body_text', 'bodyText', 'body_raw', 'bodyRaw', 'body']:
        try:
            val = getattr(context.req, attr, None)
            if val and isinstance(val, str) and val.strip():
                payload = json.loads(val)
                break
        except Exception:
            continue
    if not payload:
        for attr in ['body_json', 'bodyJson']:
            try:
                val = getattr(context.req, attr, None)
                if val and isinstance(val, dict):
                    payload = val
                    break
            except Exception:
                continue
    
    # Unwrap { data: "..." } wrapper if present
    if isinstance(payload, dict) and 'data' in payload and isinstance(payload['data'], str):
        try:
            payload = json.loads(payload['data'])
        except Exception:
            pass
    
    return payload if isinstance(payload, dict) else {}
