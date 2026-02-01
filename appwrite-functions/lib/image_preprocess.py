"""
Image Preprocessing Module for Embroidery Digitizing
Handles image cleanup, background removal, and sizing for PP1 hoop.

Uses scikit-image + PIL + numpy (no OpenCV dependency).
"""

import numpy as np
from PIL import Image, ImageFilter


# PP1 hoop specifications
HOOP_SPECS = {
    '100x100': {
        'width_mm': 100,
        'height_mm': 100,
        'safe_width_mm': 90,  # 5mm margin each side
        'safe_height_mm': 90,
    },
    '70x70': {
        'width_mm': 70,
        'height_mm': 70,
        'safe_width_mm': 62,
        'safe_height_mm': 62,
    }
}

# Default DPI for mm conversion (10 pixels per mm)
DEFAULT_PX_PER_MM = 10


def preprocess_for_embroidery(image_np, hoop_size='100x100', use_grabcut=True):
    """
    Full preprocessing pipeline for embroidery conversion.
    
    Args:
        image_np: RGB numpy array (H, W, 3)
        hoop_size: '100x100' or '70x70'
        use_grabcut: Whether to attempt advanced background removal
    
    Returns:
        preprocessed: Cleaned RGB numpy array
        alpha_mask: Binary mask (255=foreground, 0=background)
        dimensions: Dict with size info in mm
    """
    spec = HOOP_SPECS.get(hoop_size, HOOP_SPECS['100x100'])
    
    # Stage 1: Denoise
    denoised = denoise_bilateral(image_np)
    
    # Stage 2: Background removal
    if use_grabcut:
        try:
            fg_mask = remove_background_threshold(denoised)
        except Exception:
            fg_mask = np.ones(denoised.shape[:2], dtype=np.uint8) * 255
    else:
        fg_mask = np.ones(denoised.shape[:2], dtype=np.uint8) * 255
    
    # Stage 3: Clean up mask with morphological operations
    fg_mask = clean_mask(fg_mask)
    
    # Stage 4: Crop to content
    cropped, cropped_mask = crop_to_content(denoised, fg_mask)
    
    # Stage 5: Resize to safe area
    safe_w_px = spec['safe_width_mm'] * DEFAULT_PX_PER_MM
    safe_h_px = spec['safe_height_mm'] * DEFAULT_PX_PER_MM
    
    resized, resized_mask = resize_preserve_aspect(
        cropped, cropped_mask, safe_w_px, safe_h_px
    )
    
    # Stage 6: Center in hoop
    hoop_w_px = spec['width_mm'] * DEFAULT_PX_PER_MM
    hoop_h_px = spec['height_mm'] * DEFAULT_PX_PER_MM
    
    centered, centered_mask = center_in_canvas(
        resized, resized_mask, hoop_w_px, hoop_h_px
    )
    
    # Calculate actual dimensions
    actual_h, actual_w = resized.shape[:2]
    dimensions = {
        'width_mm': actual_w / DEFAULT_PX_PER_MM,
        'height_mm': actual_h / DEFAULT_PX_PER_MM,
        'safe_width_mm': spec['safe_width_mm'],
        'safe_height_mm': spec['safe_height_mm'],
        'hoop_width_mm': spec['width_mm'],
        'hoop_height_mm': spec['height_mm'],
        'px_per_mm': DEFAULT_PX_PER_MM,
    }
    
    return centered, centered_mask, dimensions


def denoise_bilateral(image_np, sigma_color=0.05, sigma_spatial=10):
    """
    Bilateral-like denoising using PIL's edge-preserving smooth filter.
    Preserves edges while reducing noise.
    """
    try:
        from skimage.restoration import denoise_bilateral as skimage_bilateral
        # skimage bilateral works on float images [0,1]
        img_float = image_np.astype(np.float64) / 255.0
        denoised = skimage_bilateral(
            img_float,
            sigma_color=sigma_color,
            sigma_spatial=sigma_spatial,
            channel_axis=-1
        )
        return (denoised * 255).clip(0, 255).astype(np.uint8)
    except ImportError:
        # Fallback to PIL smooth filter
        pil_img = Image.fromarray(image_np)
        smoothed = pil_img.filter(ImageFilter.SMOOTH_MORE)
        return np.array(smoothed)


def remove_background_threshold(image_np):
    """
    Background removal using edge detection + flood fill approach.
    Works without OpenCV's GrabCut.
    """
    try:
        from skimage.filters import sobel
        from skimage.color import rgb2gray
        from scipy import ndimage
        
        gray = rgb2gray(image_np)  # Returns float [0, 1]
        
        # Edge detection
        edges = sobel(gray)
        
        # Create binary mask from edges
        threshold = np.mean(edges) + np.std(edges)
        edge_mask = edges > threshold
        
        # Dilate edges to close gaps
        struct = ndimage.generate_binary_structure(2, 2)
        closed_edges = ndimage.binary_dilation(edge_mask, struct, iterations=3)
        closed_edges = ndimage.binary_closing(closed_edges, struct, iterations=2)
        
        # Fill holes to get foreground
        filled = ndimage.binary_fill_holes(closed_edges)
        
        # If the filled region is too small or too large, use center-based approach
        fill_ratio = np.sum(filled) / filled.size
        if fill_ratio < 0.05 or fill_ratio > 0.95:
            # Fallback: assume center is foreground, edges are background
            h, w = gray.shape
            center_mask = np.zeros_like(gray, dtype=bool)
            margin = min(h, w) // 10
            center_mask[margin:h-margin, margin:w-margin] = True
            
            # Use luminance threshold
            mean_center = np.mean(gray[center_mask])
            mean_border = np.mean(np.concatenate([
                gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]
            ]))
            
            if mean_center < mean_border:
                # Dark subject on light background
                fg_mask = gray < (mean_border - 0.1)
            else:
                # Light subject on dark background
                fg_mask = gray > (mean_border + 0.1)
            
            fg_mask = ndimage.binary_fill_holes(fg_mask)
            fg_mask = ndimage.binary_closing(fg_mask, struct, iterations=3)
            filled = fg_mask
        
        return (filled.astype(np.uint8) * 255)
        
    except ImportError:
        # Ultimate fallback: no background removal
        return np.ones(image_np.shape[:2], dtype=np.uint8) * 255


def clean_mask(mask, close_size=5, open_size=3):
    """Clean binary mask with morphological operations."""
    try:
        from skimage.morphology import disk, closing, opening
        
        binary = mask > 127
        # Close small gaps
        binary = closing(binary, disk(close_size))
        # Remove small noise
        binary = opening(binary, disk(open_size))
        
        return (binary.astype(np.uint8) * 255)
    except ImportError:
        from scipy import ndimage
        binary = mask > 127
        struct = np.ones((close_size, close_size))
        binary = ndimage.binary_closing(binary, struct)
        binary = ndimage.binary_opening(binary, np.ones((open_size, open_size)))
        return (binary.astype(np.uint8) * 255)


def crop_to_content(image_np, mask):
    """Crop image and mask to the bounding box of the mask content."""
    coords = np.argwhere(mask > 127)
    
    if len(coords) == 0:
        return image_np, mask
    
    y_min, x_min = coords.min(axis=0)
    y_max, x_max = coords.max(axis=0)
    
    # Add small padding
    pad = 5
    h, w = image_np.shape[:2]
    y_min = max(0, y_min - pad)
    x_min = max(0, x_min - pad)
    y_max = min(h - 1, y_max + pad)
    x_max = min(w - 1, x_max + pad)
    
    return image_np[y_min:y_max+1, x_min:x_max+1], mask[y_min:y_max+1, x_min:x_max+1]


def resize_preserve_aspect(image_np, mask, max_w, max_h):
    """Resize image preserving aspect ratio to fit within max dimensions."""
    h, w = image_np.shape[:2]
    
    if w == 0 or h == 0:
        return image_np, mask
    
    scale = min(max_w / w, max_h / h)
    if scale >= 1.0:
        return image_np, mask
    
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    
    # Use PIL for high-quality resize
    pil_img = Image.fromarray(image_np)
    pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    pil_mask = Image.fromarray(mask)
    pil_mask = pil_mask.resize((new_w, new_h), Image.Resampling.NEAREST)
    
    return np.array(pil_img), np.array(pil_mask)


def center_in_canvas(image_np, mask, canvas_w, canvas_h):
    """Center image and mask in a white canvas of given size."""
    h, w = image_np.shape[:2]
    
    canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 255
    mask_canvas = np.zeros((canvas_h, canvas_w), dtype=np.uint8)
    
    offset_x = (canvas_w - w) // 2
    offset_y = (canvas_h - h) // 2
    
    # Clamp to canvas bounds
    src_x1 = max(0, -offset_x)
    src_y1 = max(0, -offset_y)
    src_x2 = min(w, canvas_w - offset_x)
    src_y2 = min(h, canvas_h - offset_y)
    
    dst_x1 = max(0, offset_x)
    dst_y1 = max(0, offset_y)
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)
    
    canvas[dst_y1:dst_y2, dst_x1:dst_x2] = image_np[src_y1:src_y2, src_x1:src_x2]
    mask_canvas[dst_y1:dst_y2, dst_x1:dst_x2] = mask[src_y1:src_y2, src_x1:src_x2]
    
    return canvas, mask_canvas
