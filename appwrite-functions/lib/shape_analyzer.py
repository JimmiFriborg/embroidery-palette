"""
Shape Analysis Module for Embroidery Digitizing
Extracts and classifies regions from quantized images for stitch planning.

Uses scikit-image + scipy + numpy (no OpenCV dependency).
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Region:
    """Represents an embroidery region with its properties."""
    color: str  # Hex color string
    region_type: str  # 'fill', 'outline', or 'detail'
    contours: List[np.ndarray]  # List of contour arrays, each (N, 2)
    holes: List[np.ndarray] = field(default_factory=list)
    area_mm2: float = 0.0
    perimeter_mm: float = 0.0
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    principal_angle: float = 0.0  # Degrees, for stitch direction
    has_holes: bool = False
    compactness: float = 0.0

    def __post_init__(self):
        self.has_holes = len(self.holes) > 0


# Default pixels per mm (matches image_preprocess)
DEFAULT_PX_PER_MM = 10


def extract_regions(image_np, n_colors=6, alpha_mask=None, min_area_mm2=2.0):
    """
    Extract color regions from image with quantization and analysis.
    
    Args:
        image_np: RGB numpy array
        n_colors: Number of colors to quantize to
        alpha_mask: Optional foreground mask (255=fg)
        min_area_mm2: Minimum region area to keep
    
    Returns:
        regions: List of Region objects
        quantized: Quantized RGB image
        palette: List of RGB color tuples
    """
    # Quantize colors
    quantized, palette = quantize_colors_kmeans(image_np, n_colors)
    
    # Apply mask if provided
    if alpha_mask is not None:
        bg_mask = alpha_mask < 127
        quantized[bg_mask] = [255, 255, 255]
    
    # Extract regions for each color
    regions = []
    min_area_px = min_area_mm2 * (DEFAULT_PX_PER_MM ** 2)
    
    for color_rgb in palette:
        color_hex = '#{:02x}{:02x}{:02x}'.format(int(color_rgb[0]), int(color_rgb[1]), int(color_rgb[2]))
        
        # Skip white/near-white (background)
        if all(c > 240 for c in color_rgb):
            continue
        
        # Create mask for this color
        color_mask = create_color_mask(quantized, color_rgb)
        
        # Apply alpha mask
        if alpha_mask is not None:
            color_mask = color_mask & (alpha_mask > 127)
        
        # Find contours
        contours = find_contours(color_mask)
        
        if not contours:
            continue
        
        # Filter and classify contours
        valid_contours = []
        total_area_px = 0
        total_perimeter_px = 0
        
        for contour in contours:
            area = polygon_area(contour)
            if area < min_area_px:
                continue
            
            perimeter = polygon_perimeter(contour)
            min_perimeter_px = 3.0 * DEFAULT_PX_PER_MM  # 3mm minimum
            if perimeter < min_perimeter_px:
                continue
            
            # Simplify contour (Douglas-Peucker)
            simplified = simplify_polygon(contour, tolerance=1.5)
            if len(simplified) < 3:
                continue
            
            valid_contours.append(simplified)
            total_area_px += area
            total_perimeter_px += perimeter
        
        if not valid_contours:
            continue
        
        # Calculate region properties
        area_mm2 = total_area_px / (DEFAULT_PX_PER_MM ** 2)
        perimeter_mm = total_perimeter_px / DEFAULT_PX_PER_MM
        
        # Classify region type
        region_type = classify_region(
            area_mm2, perimeter_mm, valid_contours
        )
        
        # Bounding box
        all_points = np.vstack(valid_contours)
        x_min, y_min = all_points.min(axis=0)
        x_max, y_max = all_points.max(axis=0)
        bbox = (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
        
        # Principal angle for stitch direction
        angle = compute_principal_angle(all_points)
        
        # Compactness
        compactness = 0.0
        if perimeter_mm > 0:
            compactness = (4 * np.pi * area_mm2) / (perimeter_mm ** 2)
        
        region = Region(
            color=color_hex,
            region_type=region_type,
            contours=valid_contours,
            area_mm2=round(area_mm2, 2),
            perimeter_mm=round(perimeter_mm, 2),
            bounding_box=bbox,
            principal_angle=round(angle, 1),
            compactness=round(compactness, 3),
        )
        regions.append(region)
    
    return regions, quantized, palette


def quantize_colors_kmeans(image_np, n_colors):
    """
    Quantize image colors using K-means clustering in LAB color space.
    Uses scipy for clustering (no sklearn needed).
    """
    try:
        from skimage.color import rgb2lab, lab2rgb
        from scipy.cluster.vq import kmeans2
        
        # Convert to LAB for perceptually uniform clustering
        img_float = image_np.astype(np.float64) / 255.0
        lab_image = rgb2lab(img_float)
        
        # Reshape to pixel list
        h, w = lab_image.shape[:2]
        pixels = lab_image.reshape(-1, 3).astype(np.float64)
        
        # Subsample for speed if image is large
        max_samples = 50000
        if len(pixels) > max_samples:
            indices = np.random.choice(len(pixels), max_samples, replace=False)
            sample_pixels = pixels[indices]
        else:
            sample_pixels = pixels
        
        # K-means clustering
        centroids, labels_sample = kmeans2(sample_pixels, n_colors, minit='points', iter=20)
        
        # Assign all pixels to nearest centroid
        from scipy.spatial.distance import cdist
        distances = cdist(pixels, centroids)
        labels = np.argmin(distances, axis=1)
        
        # Convert centroids back to RGB
        centroids_rgb = []
        for c in centroids:
            lab_pixel = c.reshape(1, 1, 3)
            rgb_pixel = lab2rgb(lab_pixel)
            rgb_values = (rgb_pixel[0, 0] * 255).clip(0, 255).astype(np.uint8)
            centroids_rgb.append(rgb_values.tolist())
        
        # Create quantized image
        quantized_lab = centroids[labels].reshape(h, w, 3)
        quantized_rgb = lab2rgb(quantized_lab)
        quantized = (quantized_rgb * 255).clip(0, 255).astype(np.uint8)
        
        return quantized, centroids_rgb
        
    except ImportError:
        # Fallback to PIL quantization
        return quantize_colors_pil(image_np, n_colors)


def quantize_colors_pil(image_np, n_colors):
    """Fallback color quantization using PIL."""
    from PIL import Image
    
    pil_img = Image.fromarray(image_np)
    quantized = pil_img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
    
    palette = quantized.getpalette()
    colors = []
    for i in range(n_colors):
        colors.append([palette[i*3], palette[i*3+1], palette[i*3+2]])
    
    return np.array(quantized.convert('RGB')), colors


def create_color_mask(quantized, color_rgb, tolerance=10):
    """Create a binary mask for pixels matching the given color."""
    color = np.array(color_rgb, dtype=np.int16)
    diff = np.abs(quantized.astype(np.int16) - color)
    return np.all(diff <= tolerance, axis=2)


def find_contours(binary_mask):
    """
    Find contours in a binary mask.
    Returns list of contour arrays, each (N, 2) with (x, y) coordinates.
    """
    try:
        from skimage.measure import find_contours as skimage_find_contours
        
        # skimage find_contours returns (row, col) format
        mask_float = binary_mask.astype(np.float64)
        raw_contours = skimage_find_contours(mask_float, level=0.5)
        
        # Convert from (row, col) to (x, y) and ensure integer coords
        contours = []
        for c in raw_contours:
            if len(c) < 3:
                continue
            # Swap columns: (row, col) -> (x, y) = (col, row)
            xy = np.column_stack([c[:, 1], c[:, 0]]).astype(np.int32)
            contours.append(xy)
        
        return contours
        
    except ImportError:
        # Fallback: use scipy labeling
        from scipy import ndimage
        
        labeled, n_features = ndimage.label(binary_mask)
        contours = []
        
        for i in range(1, n_features + 1):
            region_mask = (labeled == i)
            # Get boundary pixels
            eroded = ndimage.binary_erosion(region_mask)
            boundary = region_mask & ~eroded
            coords = np.argwhere(boundary)
            if len(coords) >= 3:
                # Convert (row, col) to (x, y)
                xy = np.column_stack([coords[:, 1], coords[:, 0]])
                contours.append(xy.astype(np.int32))
        
        return contours


def polygon_area(contour):
    """Calculate area of polygon using Shoelace formula."""
    if len(contour) < 3:
        return 0.0
    
    x = contour[:, 0].astype(np.float64)
    y = contour[:, 1].astype(np.float64)
    
    return 0.5 * abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]) + 
                      x[-1] * y[0] - x[0] * y[-1])


def polygon_perimeter(contour):
    """Calculate perimeter of polygon."""
    if len(contour) < 2:
        return 0.0
    
    diffs = np.diff(contour, axis=0)
    segment_lengths = np.sqrt(np.sum(diffs ** 2, axis=1))
    
    # Add closing segment
    closing = np.sqrt(np.sum((contour[-1] - contour[0]) ** 2))
    
    return float(np.sum(segment_lengths) + closing)


def simplify_polygon(contour, tolerance=1.5):
    """
    Simplify polygon using Douglas-Peucker algorithm.
    """
    try:
        from skimage.measure import approximate_polygon
        simplified = approximate_polygon(contour, tolerance=tolerance)
        return simplified.astype(np.int32)
    except ImportError:
        # Basic simplification: keep every Nth point
        if len(contour) <= 10:
            return contour
        step = max(1, len(contour) // 50)
        return contour[::step].astype(np.int32)


def classify_region(area_mm2, perimeter_mm, contours):
    """
    Classify a region as fill, outline, or detail based on its properties.
    """
    if area_mm2 <= 0 or perimeter_mm <= 0:
        return 'detail'
    
    compactness = (4 * np.pi * area_mm2) / (perimeter_mm ** 2)
    
    # Calculate aspect ratio from bounding box
    all_points = np.vstack(contours)
    x_range = all_points[:, 0].max() - all_points[:, 0].min()
    y_range = all_points[:, 1].max() - all_points[:, 1].min()
    
    if min(x_range, y_range) == 0:
        aspect_ratio = 100
    else:
        aspect_ratio = max(x_range, y_range) / min(x_range, y_range)
    
    # Classification logic
    if compactness < 0.1 or aspect_ratio > 8:
        return 'outline'  # Thin stroke
    elif area_mm2 < 5.0:
        return 'detail'   # Small element
    else:
        return 'fill'     # Large area


def compute_principal_angle(points):
    """
    Compute the principal axis angle of a set of points.
    Returns angle in degrees (0-180).
    """
    if len(points) < 3:
        return 0.0
    
    # Center points
    centroid = points.mean(axis=0)
    centered = points - centroid
    
    # Covariance matrix
    cov = np.cov(centered.T)
    
    if cov.shape != (2, 2):
        return 0.0
    
    # Eigenvalues and eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    
    # Principal axis is the eigenvector with larger eigenvalue
    principal = eigenvectors[:, np.argmax(eigenvalues)]
    
    # Angle in degrees
    angle = np.degrees(np.arctan2(principal[1], principal[0]))
    
    # Normalize to 0-180
    return float(angle % 180)
