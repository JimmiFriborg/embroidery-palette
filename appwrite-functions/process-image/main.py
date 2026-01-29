"""
Appwrite Python Function: Image Processing
Handles background removal and color quantization for embroidery conversion.

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
import base64
import numpy as np
from PIL import Image
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.input_file import InputFile

# Try importing OpenCV - may need installation
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
        
        # Process image with embroidery-friendly pipeline
        context.log(f'Processing with {thread_count} colors for PP1...')
        
        # Step 1: Remove background (GrabCut for cleaner results)
        context.log('Removing background...')
        processed_np = remove_background_simple(image_np)
        
        # Step 2: Extract clean outlines (Canny + contour simplification)
        context.log('Extracting embroidery-friendly outlines...')
        outline_image, contours = extract_clean_outlines(processed_np)
        
        # Step 3: Quantize colors (fewer = better for PP1 hobbyist use)
        context.log(f'Quantizing to {thread_count} colors...')
        quantized_np, colors = quantize_colors(processed_np, thread_count)
        
        # Step 4: Resize for hoop with safe area (90x90 for 100mm, 62x62 for 70mm)
        context.log(f'Sizing for {hoop_size} hoop with safe margins...')
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
        
        # Update project document with outline data
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
        
        return context.res.json({
            'success': True,
            'processedImageId': processed_file['$id'],
            'outlineImageId': outline_file_id,
            'extractedColors': color_hex_list,
            'colorCount': len(colors),
            'contourCount': len(contours) if contours else 0
        })
        
    except Exception as e:
        context.error(f'Processing error: {str(e)}')
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def remove_background_simple(image_np):
    """
    Background removal using GrabCut for cleaner segmentation.
    Falls back to edge-based detection if GrabCut fails.
    """
    if cv2 is None:
        return image_np
    
    h, w = image_np.shape[:2]
    
    # Try GrabCut first (better results for hobby embroidery)
    try:
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        
        # Rectangle covering center 80% of image
        margin_x, margin_y = int(w * 0.1), int(h * 0.1)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        cv2.grabCut(image_np, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        
        # Create binary mask (foreground + probable foreground)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        result = image_np.copy()
        result[mask2 == 0] = [255, 255, 255]
        return result
        
    except Exception:
        # Fallback to simple edge-based detection
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
    """
    Extract clean, embroidery-friendly outlines using Canny + contour simplification.
    
    For PP1 hobby machine:
    - Fewer points = cleaner stitches
    - Smooth curves = less thread breaks
    - Structural outlines, not literal pixel boundaries
    """
    if cv2 is None:
        return None, []
    
    h, w = image_np.shape[:2]
    
    # Convert to grayscale
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    
    # Bilateral filter: preserves edges while removing noise (critical for embroidery)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Adaptive Canny thresholds based on image
    median_val = np.median(filtered)
    lower = int(max(0, 0.66 * median_val))
    upper = int(min(255, 1.33 * median_val))
    
    # Canny edge detection with tuned thresholds
    edges = cv2.Canny(filtered, lower, upper)
    
    # Morphological closing to connect nearby edges
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, []
    
    # Filter and simplify contours for embroidery
    min_contour_length = min(h, w) * 0.05  # Ignore tiny contours
    simplified_contours = []
    
    for contour in contours:
        # Filter by arc length (perimeter)
        arc_length = cv2.arcLength(contour, True)
        if arc_length < min_contour_length:
            continue
        
        # Filter by area (ignore very small enclosed regions)
        area = cv2.contourArea(contour)
        if area < (min_contour_length ** 2) * 0.1:
            continue
        
        # Ramer-Douglas-Peucker simplification
        # Higher epsilon = fewer points = cleaner embroidery
        epsilon = simplify_epsilon * 0.01 * arc_length
        simplified = cv2.approxPolyDP(contour, epsilon, True)
        
        # Only keep if simplification retained meaningful shape
        if len(simplified) >= 4:
            simplified_contours.append(simplified)
    
    # Create outline image
    outline_image = np.ones((h, w, 3), dtype=np.uint8) * 255
    cv2.drawContours(outline_image, simplified_contours, -1, (0, 0, 0), 2)
    
    return outline_image, simplified_contours


def quantize_colors(image_np, n_colors):
    """
    Reduce image to n_colors using K-means clustering in LAB color space.
    """
    if cv2 is None:
        # Fallback without OpenCV
        return quantize_colors_pil(image_np, n_colors)
    
    # Reshape image for clustering
    pixels = image_np.reshape(-1, 3).astype(np.float32)
    
    # Convert to LAB color space for better perceptual clustering
    lab_pixels = cv2.cvtColor(image_np, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    
    # K-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(lab_pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Convert centers back to RGB
    centers_lab = centers.reshape(1, -1, 3).astype(np.uint8)
    centers_rgb = cv2.cvtColor(centers_lab, cv2.COLOR_LAB2RGB).reshape(-1, 3)
    
    # Map pixels to nearest center
    quantized = centers_rgb[labels.flatten()]
    quantized_image = quantized.reshape(image_np.shape).astype(np.uint8)
    
    return quantized_image, centers_rgb.tolist()


def quantize_colors_pil(image_np, n_colors):
    """
    Fallback color quantization using PIL.
    """
    image = Image.fromarray(image_np)
    quantized = image.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    
    # Get palette colors
    palette = quantized.getpalette()
    colors = []
    for i in range(n_colors):
        colors.append([palette[i*3], palette[i*3+1], palette[i*3+2]])
    
    return np.array(quantized.convert('RGB')), colors


def resize_for_hoop(image_np, hoop_size):
    """
    Resize image to fit within hoop SAFE AREA.
    
    PP1 safe areas (leaving margin for hoop flex and registration):
    - 100x100mm hoop → 90x90mm safe area (900x900 px at 10px/mm)
    - 70x70mm hoop → 62x62mm safe area (620x620 px at 10px/mm)
    
    This prevents edge distortion and registration errors common with
    auto-digitized content on hobby machines.
    """
    # Safe areas in pixels (10 px/mm for embroidery resolution)
    safe_areas = {
        '100x100': (900, 900),   # 90mm safe zone
        '70x70': (620, 620)      # 62mm safe zone
    }
    
    # Full hoop size for canvas
    full_sizes = {
        '100x100': (1000, 1000),
        '70x70': (700, 700)
    }
    
    safe_size = safe_areas.get(hoop_size, (900, 900))
    full_size = full_sizes.get(hoop_size, (1000, 1000))
    
    image = Image.fromarray(image_np)
    image.thumbnail(safe_size, Image.Resampling.LANCZOS)
    
    # Create white canvas at full hoop size and center image
    canvas = Image.new('RGB', full_size, (255, 255, 255))
    offset = ((full_size[0] - image.width) // 2, (full_size[1] - image.height) // 2)
    canvas.paste(image, offset)
    
    return np.array(canvas)


def rgb_to_hex(rgb):
    """Convert RGB list to hex string."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
