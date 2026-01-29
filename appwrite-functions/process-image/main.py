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
        
        # Process image
        context.log(f'Processing with {thread_count} colors...')
        
        # Step 1: Remove background (simplified approach)
        processed_np = remove_background_simple(image_np)
        
        # Step 2: Quantize colors
        quantized_np, colors = quantize_colors(processed_np, thread_count)
        
        # Step 3: Resize for hoop
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
        
        # Convert colors to hex
        color_hex_list = [rgb_to_hex(c) for c in colors]
        
        # Update project document
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
        
        return context.res.json({
            'success': True,
            'processedImageId': processed_file['$id'],
            'extractedColors': color_hex_list,
            'colorCount': len(colors)
        })
        
    except Exception as e:
        context.error(f'Processing error: {str(e)}')
        return context.res.json({
            'success': False,
            'error': str(e)
        }, 500)


def remove_background_simple(image_np):
    """
    Simple background removal using edge detection and thresholding.
    For better results, use GrabCut or a deep learning model.
    """
    if cv2 is None:
        # Fallback: return image as-is if OpenCV not available
        return image_np
    
    # Convert to grayscale
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
    
    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilate edges to close gaps
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image_np
    
    # Create mask from largest contour
    mask = np.zeros(gray.shape, dtype=np.uint8)
    largest_contour = max(contours, key=cv2.contourArea)
    cv2.drawContours(mask, [largest_contour], -1, 255, -1)
    
    # Apply mask - set background to white
    result = image_np.copy()
    result[mask == 0] = [255, 255, 255]
    
    return result


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
    Resize image to fit within hoop dimensions.
    Maintains aspect ratio, adds padding if needed.
    """
    # Hoop sizes in mm, convert to pixels at 10 pixels/mm for embroidery
    sizes = {
        '100x100': (1000, 1000),  # 100mm at 10px/mm
        '70x70': (700, 700)       # 70mm at 10px/mm
    }
    
    target_size = sizes.get(hoop_size, (1000, 1000))
    
    image = Image.fromarray(image_np)
    image.thumbnail(target_size, Image.Resampling.LANCZOS)
    
    # Create white canvas and center image
    canvas = Image.new('RGB', target_size, (255, 255, 255))
    offset = ((target_size[0] - image.width) // 2, (target_size[1] - image.height) // 2)
    canvas.paste(image, offset)
    
    return np.array(canvas)


def rgb_to_hex(rgb):
    """Convert RGB list to hex string."""
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
