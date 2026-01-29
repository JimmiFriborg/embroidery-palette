"""
Image Preprocessing Module for PP1 Embroidery

Stage 1 of the digitizing pipeline:
- Bilateral filtering (noise removal, edge preservation)
- Background removal (GrabCut with threshold fallback)
- Safe area calculation and enforcement
- Aspect-ratio-preserving resize

Optimized for Brother PP1 hobbyist embroidery machine.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional

# Try to import OpenCV, fall back gracefully
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from PIL import Image


# Hoop specifications (in mm)
HOOP_SPECS = {
    '100x100': {
        'size_mm': (100, 100),
        'safe_area_mm': (90, 90),  # 5mm margin on each side
        'margin_mm': 5.0,
    },
    '70x70': {
        'size_mm': (70, 70),
        'safe_area_mm': (62, 62),  # ~4mm margin
        'margin_mm': 4.0,
    },
}

# Default pixels per mm (at 10px/mm, 100mm = 1000px)
DEFAULT_PX_PER_MM = 10.0


@dataclass
class PreprocessResult:
    """Result of image preprocessing."""
    image: np.ndarray          # Cleaned RGB image
    mask: np.ndarray           # Alpha mask (foreground)
    safe_area_mm: Tuple[float, float]
    hoop_size: str
    pixels_per_mm: float
    original_size: Tuple[int, int]
    final_size: Tuple[int, int]
    background_removed: bool
    method_used: str


def preprocess_for_embroidery(
    image_np: np.ndarray,
    hoop_size: str = '100x100',
    safe_margin_mm: float = 5.0,
    use_grabcut: bool = True,
    bilateral_d: int = 9,
    bilateral_sigma_color: float = 75,
    bilateral_sigma_space: float = 75,
) -> PreprocessResult:
    """
    Main preprocessing entry point.
    
    Prepares an image for embroidery digitizing:
    1. Apply bilateral filter (smooth while preserving edges)
    2. Remove background (GrabCut or threshold)
    3. Crop to content
    4. Resize to safe area within hoop
    5. Center in hoop
    
    Args:
        image_np: Input RGB image as numpy array
        hoop_size: Target hoop ('100x100' or '70x70')
        safe_margin_mm: Margin from hoop edge in mm
        use_grabcut: Try GrabCut for background removal
        bilateral_*: Bilateral filter parameters
        
    Returns:
        PreprocessResult with cleaned image, mask, and metadata
    """
    if hoop_size not in HOOP_SPECS:
        hoop_size = '100x100'
    
    spec = HOOP_SPECS[hoop_size]
    original_size = (image_np.shape[1], image_np.shape[0])
    
    # Step 1: Bilateral filtering (noise reduction, edge preservation)
    filtered = apply_bilateral_filter(
        image_np, bilateral_d, bilateral_sigma_color, bilateral_sigma_space
    )
    
    # Step 2: Background removal
    if use_grabcut and HAS_OPENCV:
        fg_image, mask, method = remove_background_grabcut(filtered)
    else:
        fg_image, mask, method = remove_background_threshold(filtered)
    
    background_removed = np.any(mask == 0)
    
    # Step 3: Crop to content (non-transparent region)
    cropped_image, cropped_mask = crop_to_content(fg_image, mask)
    
    # Step 4: Resize to safe area
    safe_area_mm = (
        spec['size_mm'][0] - 2 * safe_margin_mm,
        spec['size_mm'][1] - 2 * safe_margin_mm,
    )
    
    resized_image, resized_mask, px_per_mm = resize_to_safe_area(
        cropped_image, cropped_mask, safe_area_mm
    )
    
    # Step 5: Center in hoop (add padding to full hoop size)
    hoop_px = (
        int(spec['size_mm'][0] * px_per_mm),
        int(spec['size_mm'][1] * px_per_mm),
    )
    
    final_image, final_mask = center_in_hoop(
        resized_image, resized_mask, hoop_px
    )
    
    return PreprocessResult(
        image=final_image,
        mask=final_mask,
        safe_area_mm=safe_area_mm,
        hoop_size=hoop_size,
        pixels_per_mm=px_per_mm,
        original_size=original_size,
        final_size=(final_image.shape[1], final_image.shape[0]),
        background_removed=background_removed,
        method_used=method,
    )


def apply_bilateral_filter(
    image: np.ndarray,
    d: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75,
) -> np.ndarray:
    """
    Apply bilateral filter to smooth while preserving edges.
    
    This is critical for embroidery: we want smooth regions
    but sharp boundaries between colors.
    """
    if HAS_OPENCV:
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
    else:
        # Fallback: no filtering (PIL doesn't have bilateral)
        return image


def remove_background_grabcut(
    image: np.ndarray,
    iterations: int = 5,
    margin_ratio: float = 0.05,
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Remove background using GrabCut algorithm.
    
    GrabCut iteratively segments foreground/background based on
    initial rectangle hint. Good for images with clear subjects.
    
    Returns: (foreground_image, mask, method_name)
    """
    if not HAS_OPENCV:
        return remove_background_threshold(image)
    
    h, w = image.shape[:2]
    
    # Initial rectangle: slightly inset from image edges
    margin_x = int(w * margin_ratio)
    margin_y = int(h * margin_ratio)
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
    
    # Initialize mask and models
    mask = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    
    try:
        cv2.grabCut(
            image, mask, rect,
            bgd_model, fgd_model,
            iterations, cv2.GC_INIT_WITH_RECT
        )
        
        # Create binary mask (foreground = 1 or 3)
        binary_mask = np.where(
            (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        
        # Apply mask to image (set background to white)
        result = image.copy()
        result[binary_mask == 0] = [255, 255, 255]
        
        return result, binary_mask, 'grabcut'
        
    except Exception:
        # Fall back to threshold if GrabCut fails
        return remove_background_threshold(image)


def remove_background_threshold(
    image: np.ndarray,
    bg_threshold: int = 240,
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Simple threshold-based background removal.
    
    Assumes near-white background (common for embroidery source images).
    Fast fallback when GrabCut isn't available or fails.
    
    Returns: (foreground_image, mask, method_name)
    """
    # Convert to grayscale for thresholding
    if len(image.shape) == 3:
        gray = np.mean(image, axis=2).astype(np.uint8)
    else:
        gray = image
    
    # Threshold: background is very bright
    mask = np.where(gray < bg_threshold, 255, 0).astype(np.uint8)
    
    # Clean up mask with morphological operations
    if HAS_OPENCV:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Apply mask (background → white)
    result = image.copy()
    result[mask == 0] = [255, 255, 255]
    
    return result, mask, 'threshold'


def crop_to_content(
    image: np.ndarray,
    mask: np.ndarray,
    padding_px: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crop image and mask to bounding box of content.
    
    Removes empty margins to focus on actual design.
    """
    # Find content bounds
    if HAS_OPENCV:
        coords = cv2.findNonZero(mask)
        if coords is None:
            return image, mask
        x, y, w, h = cv2.boundingRect(coords)
    else:
        rows = np.any(mask > 0, axis=1)
        cols = np.any(mask > 0, axis=0)
        if not np.any(rows) or not np.any(cols):
            return image, mask
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        x, y = x_min, y_min
        w, h = x_max - x_min + 1, y_max - y_min + 1
    
    # Add padding (clamped to image bounds)
    x1 = max(0, x - padding_px)
    y1 = max(0, y - padding_px)
    x2 = min(image.shape[1], x + w + padding_px)
    y2 = min(image.shape[0], y + h + padding_px)
    
    return image[y1:y2, x1:x2], mask[y1:y2, x1:x2]


def resize_to_safe_area(
    image: np.ndarray,
    mask: np.ndarray,
    safe_area_mm: Tuple[float, float],
    target_px_per_mm: float = DEFAULT_PX_PER_MM,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Resize image to fit within safe area, preserving aspect ratio.
    
    Returns: (resized_image, resized_mask, actual_px_per_mm)
    """
    h, w = image.shape[:2]
    safe_w_mm, safe_h_mm = safe_area_mm
    
    # Calculate target size in pixels
    target_w_px = int(safe_w_mm * target_px_per_mm)
    target_h_px = int(safe_h_mm * target_px_per_mm)
    
    # Preserve aspect ratio
    scale = min(target_w_px / w, target_h_px / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Resize
    if HAS_OPENCV:
        resized_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        resized_mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    else:
        pil_img = Image.fromarray(image)
        resized_img = np.array(pil_img.resize((new_w, new_h), Image.LANCZOS))
        pil_mask = Image.fromarray(mask)
        resized_mask = np.array(pil_mask.resize((new_w, new_h), Image.NEAREST))
    
    # Calculate actual pixels per mm
    actual_px_per_mm = new_w / (w / target_px_per_mm * scale / scale)
    # Simplified: use target since we're scaling to fit
    actual_px_per_mm = target_px_per_mm
    
    return resized_img, resized_mask, actual_px_per_mm


def center_in_hoop(
    image: np.ndarray,
    mask: np.ndarray,
    hoop_size_px: Tuple[int, int],
    background_color: Tuple[int, int, int] = (255, 255, 255),
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Center image in full hoop canvas.
    
    Creates a white background canvas of hoop size and places
    the design centered within it.
    """
    h, w = image.shape[:2]
    hoop_w, hoop_h = hoop_size_px
    
    # Create white canvas
    canvas = np.full((hoop_h, hoop_w, 3), background_color, dtype=np.uint8)
    mask_canvas = np.zeros((hoop_h, hoop_w), dtype=np.uint8)
    
    # Calculate position to center
    x_offset = (hoop_w - w) // 2
    y_offset = (hoop_h - h) // 2
    
    # Place image and mask
    canvas[y_offset:y_offset+h, x_offset:x_offset+w] = image
    mask_canvas[y_offset:y_offset+h, x_offset:x_offset+w] = mask
    
    return canvas, mask_canvas


def get_safe_area_for_hoop(hoop_size: str) -> Tuple[float, float]:
    """Get safe embroidery area for a hoop size (in mm)."""
    if hoop_size in HOOP_SPECS:
        return HOOP_SPECS[hoop_size]['safe_area_mm']
    return (90, 90)  # Default


def mm_to_px(mm: float, px_per_mm: float = DEFAULT_PX_PER_MM) -> int:
    """Convert millimeters to pixels."""
    return int(mm * px_per_mm)


def px_to_mm(px: int, px_per_mm: float = DEFAULT_PX_PER_MM) -> float:
    """Convert pixels to millimeters."""
    return px / px_per_mm
