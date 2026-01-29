"""
Shape Analysis Module for PP1 Embroidery

Stage 3 of the digitizing pipeline:
- Extract contours per color
- Classify regions: fill / outline / detail
- Calculate principal angles (for stitch direction)
- Filter noise (< 2mm² areas)
- Simplify contours (Douglas-Peucker)

Optimized for Brother PP1 hobbyist embroidery machine.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import math

# Try to import OpenCV
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


# Region classification thresholds
MIN_AREA_MM2 = 2.0           # Ignore regions smaller than this
MIN_PERIMETER_MM = 3.0       # Ignore very short contours
OUTLINE_COMPACTNESS = 0.1    # Below this = outline (thin stroke)
OUTLINE_ASPECT_RATIO = 8.0   # Above this = outline
DETAIL_AREA_MM2 = 5.0        # Below this = detail (small fill)
FILL_AREA_MM2 = 5.0          # Above this = full fill

# Simplification
SIMPLIFY_EPSILON_MM = 0.3    # Douglas-Peucker epsilon


@dataclass
class Region:
    """
    A single embroidery region extracted from the image.
    
    Contains all information needed for stitch planning.
    """
    color_hex: str                          # e.g., '#FF0000'
    color_rgb: Tuple[int, int, int]         # (255, 0, 0)
    region_type: str                        # 'fill', 'outline', or 'detail'
    contours: List[np.ndarray]              # Simplified contour points
    holes: List[np.ndarray] = field(default_factory=list)  # Interior holes
    area_mm2: float = 0.0                   # Area in mm²
    perimeter_mm: float = 0.0               # Perimeter in mm
    principal_angle: float = 0.0            # Degrees, for stitch direction
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    aspect_ratio: float = 1.0               # width / height
    compactness: float = 1.0                # 4π * area / perimeter²
    centroid: Tuple[float, float] = (0.0, 0.0)


def extract_regions(
    quantized_image: np.ndarray,
    color_palette: List[Tuple[int, int, int]],
    mask: Optional[np.ndarray] = None,
    pixels_per_mm: float = 10.0,
    min_area_mm2: float = MIN_AREA_MM2,
    simplify_epsilon_mm: float = SIMPLIFY_EPSILON_MM,
) -> List[Region]:
    """
    Extract and classify embroidery regions from a quantized image.
    
    For each color in the palette:
    1. Create binary mask for that color
    2. Find contours
    3. Filter by size
    4. Classify (fill/outline/detail)
    5. Simplify contours
    6. Calculate properties
    
    Args:
        quantized_image: Color-quantized RGB image
        color_palette: List of RGB tuples in the image
        mask: Optional foreground mask
        pixels_per_mm: Scale factor
        min_area_mm2: Minimum region area
        simplify_epsilon_mm: Contour simplification tolerance
        
    Returns:
        List of Region objects, sorted by area (largest first)
    """
    if not HAS_OPENCV:
        return _extract_regions_fallback(
            quantized_image, color_palette, pixels_per_mm
        )
    
    regions = []
    px_per_mm2 = pixels_per_mm ** 2
    min_area_px = min_area_mm2 * px_per_mm2
    epsilon_px = simplify_epsilon_mm * pixels_per_mm
    
    for color_rgb in color_palette:
        # Skip white (background)
        if color_rgb == (255, 255, 255) or sum(color_rgb) > 750:
            continue
        
        # Create mask for this color
        color_mask = create_color_mask(quantized_image, color_rgb)
        
        # Apply foreground mask if provided
        if mask is not None:
            color_mask = cv2.bitwise_and(color_mask, mask)
        
        # Find contours with hierarchy (for hole detection)
        contours, hierarchy = cv2.findContours(
            color_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours or hierarchy is None:
            continue
        
        hierarchy = hierarchy[0]
        
        # Process each outer contour
        for i, contour in enumerate(contours):
            # Skip if this is a hole (has parent)
            if hierarchy[i][3] != -1:
                continue
            
            area_px = cv2.contourArea(contour)
            if area_px < min_area_px:
                continue
            
            perimeter_px = cv2.arcLength(contour, True)
            if perimeter_px < min_area_mm2 * pixels_per_mm:
                continue
            
            # Simplify contour
            simplified = cv2.approxPolyDP(contour, epsilon_px, True)
            
            # Find holes (child contours)
            holes = []
            child_idx = hierarchy[i][2]  # First child
            while child_idx != -1:
                hole = contours[child_idx]
                if cv2.contourArea(hole) > min_area_px * 0.5:
                    holes.append(cv2.approxPolyDP(hole, epsilon_px, True))
                child_idx = hierarchy[child_idx][0]  # Next sibling
            
            # Calculate properties
            region = create_region_from_contour(
                simplified, holes, color_rgb, pixels_per_mm
            )
            
            regions.append(region)
    
    # Sort by area (largest first - stitch order optimization)
    regions.sort(key=lambda r: r.area_mm2, reverse=True)
    
    # Filter overlapping/duplicate regions
    regions = filter_overlapping_regions(regions, pixels_per_mm)
    
    return regions


def create_color_mask(
    image: np.ndarray,
    color_rgb: Tuple[int, int, int],
    tolerance: int = 5,
) -> np.ndarray:
    """Create binary mask for a specific color."""
    lower = np.array([max(0, c - tolerance) for c in color_rgb])
    upper = np.array([min(255, c + tolerance) for c in color_rgb])
    return cv2.inRange(image, lower, upper)


def create_region_from_contour(
    contour: np.ndarray,
    holes: List[np.ndarray],
    color_rgb: Tuple[int, int, int],
    pixels_per_mm: float,
) -> Region:
    """
    Create a Region object from a contour.
    
    Calculates all geometric properties and classifies the region.
    """
    px_per_mm2 = pixels_per_mm ** 2
    
    # Basic measurements
    area_px = cv2.contourArea(contour)
    perimeter_px = cv2.arcLength(contour, True)
    area_mm2 = area_px / px_per_mm2
    perimeter_mm = perimeter_px / pixels_per_mm
    
    # Bounding box and aspect ratio
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / max(h, 1)
    
    # Compactness (circularity): 4π * area / perimeter²
    # Circle = 1.0, very thin shape = close to 0
    if perimeter_px > 0:
        compactness = (4 * math.pi * area_px) / (perimeter_px ** 2)
    else:
        compactness = 0
    
    # Centroid
    M = cv2.moments(contour)
    if M['m00'] != 0:
        cx = M['m10'] / M['m00']
        cy = M['m01'] / M['m00']
    else:
        cx, cy = x + w/2, y + h/2
    
    # Principal angle (orientation for stitch direction)
    principal_angle = calculate_principal_angle(contour)
    
    # Classify region type
    region_type = classify_region(
        area_mm2, perimeter_mm, compactness, aspect_ratio
    )
    
    # Color hex
    color_hex = '#{:02X}{:02X}{:02X}'.format(*color_rgb)
    
    return Region(
        color_hex=color_hex,
        color_rgb=color_rgb,
        region_type=region_type,
        contours=[contour],
        holes=holes,
        area_mm2=area_mm2,
        perimeter_mm=perimeter_mm,
        principal_angle=principal_angle,
        bounding_box=(x, y, w, h),
        aspect_ratio=aspect_ratio,
        compactness=compactness,
        centroid=(cx, cy),
    )


def classify_region(
    area_mm2: float,
    perimeter_mm: float,
    compactness: float,
    aspect_ratio: float,
) -> str:
    """
    Classify a region as 'fill', 'outline', or 'detail'.
    
    Logic:
    - Outline: Very thin (low compactness or high aspect ratio)
    - Detail: Small area (< 5mm²)
    - Fill: Everything else (large solid areas)
    """
    # Very thin shapes → outline only (bean stitch)
    if compactness < OUTLINE_COMPACTNESS:
        return 'outline'
    
    if aspect_ratio > OUTLINE_ASPECT_RATIO:
        return 'outline'
    
    # Small shapes → detail (light fill)
    if area_mm2 < DETAIL_AREA_MM2:
        return 'detail'
    
    # Large shapes → full fill
    return 'fill'


def calculate_principal_angle(contour: np.ndarray) -> float:
    """
    Calculate the principal axis angle of a contour.
    
    This determines the optimal stitch direction for fills.
    Uses PCA on contour points to find the longest axis.
    
    Returns angle in degrees (0-180).
    """
    if len(contour) < 5:
        return 0.0
    
    # Flatten contour points
    points = contour.reshape(-1, 2).astype(np.float64)
    
    # Try fitting an ellipse (more robust for regular shapes)
    if len(points) >= 5:
        try:
            ellipse = cv2.fitEllipse(contour)
            angle = ellipse[2]  # Rotation angle
            return angle % 180
        except:
            pass
    
    # Fallback: PCA on contour points
    mean = np.mean(points, axis=0)
    centered = points - mean
    cov = np.cov(centered.T)
    
    if cov.shape == (2, 2):
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        # Principal axis is eigenvector with largest eigenvalue
        idx = np.argmax(eigenvalues)
        principal = eigenvectors[:, idx]
        angle = math.degrees(math.atan2(principal[1], principal[0]))
        return angle % 180
    
    return 0.0


def filter_overlapping_regions(
    regions: List[Region],
    pixels_per_mm: float,
    overlap_threshold: float = 0.8,
) -> List[Region]:
    """
    Remove regions that are mostly contained within larger regions.
    
    This cleans up artifacts from color quantization where small
    noise regions appear inside larger fills.
    """
    if len(regions) <= 1:
        return regions
    
    filtered = []
    
    for i, region in enumerate(regions):
        is_contained = False
        
        for j, other in enumerate(regions):
            if i == j:
                continue
            
            # Skip if other region is smaller
            if other.area_mm2 <= region.area_mm2:
                continue
            
            # Check if bounding boxes overlap significantly
            r_box = region.bounding_box
            o_box = other.bounding_box
            
            # Calculate intersection
            x1 = max(r_box[0], o_box[0])
            y1 = max(r_box[1], o_box[1])
            x2 = min(r_box[0] + r_box[2], o_box[0] + o_box[2])
            y2 = min(r_box[1] + r_box[3], o_box[1] + o_box[3])
            
            if x1 < x2 and y1 < y2:
                intersection_area = (x2 - x1) * (y2 - y1)
                region_box_area = r_box[2] * r_box[3]
                
                if region_box_area > 0:
                    overlap = intersection_area / region_box_area
                    if overlap > overlap_threshold:
                        # Region is mostly contained, skip it
                        is_contained = True
                        break
        
        if not is_contained:
            filtered.append(region)
    
    return filtered


def merge_regions_by_color(regions: List[Region]) -> Dict[str, List[Region]]:
    """Group regions by color hex code."""
    by_color = {}
    for region in regions:
        if region.color_hex not in by_color:
            by_color[region.color_hex] = []
        by_color[region.color_hex].append(region)
    return by_color


def get_region_stats(regions: List[Region]) -> dict:
    """Get summary statistics for a list of regions."""
    if not regions:
        return {
            'count': 0,
            'total_area_mm2': 0,
            'types': {'fill': 0, 'outline': 0, 'detail': 0},
            'colors': [],
        }
    
    types = {'fill': 0, 'outline': 0, 'detail': 0}
    colors = set()
    total_area = 0
    
    for r in regions:
        types[r.region_type] += 1
        colors.add(r.color_hex)
        total_area += r.area_mm2
    
    return {
        'count': len(regions),
        'total_area_mm2': total_area,
        'types': types,
        'colors': list(colors),
    }


def _extract_regions_fallback(
    quantized_image: np.ndarray,
    color_palette: List[Tuple[int, int, int]],
    pixels_per_mm: float,
) -> List[Region]:
    """
    Fallback region extraction without OpenCV.
    
    Creates simple bounding-box regions for each color.
    Less accurate but functional.
    """
    regions = []
    px_per_mm2 = pixels_per_mm ** 2
    
    for color_rgb in color_palette:
        if color_rgb == (255, 255, 255):
            continue
        
        # Find pixels of this color
        mask = np.all(quantized_image == color_rgb, axis=2)
        if not np.any(mask):
            continue
        
        # Get bounding box
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not np.any(rows) or not np.any(cols):
            continue
        
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        w = x_max - x_min + 1
        h = y_max - y_min + 1
        area_px = np.sum(mask)
        area_mm2 = area_px / px_per_mm2
        
        if area_mm2 < MIN_AREA_MM2:
            continue
        
        # Create simple rectangular contour
        contour = np.array([
            [[x_min, y_min]],
            [[x_max, y_min]],
            [[x_max, y_max]],
            [[x_min, y_max]],
        ], dtype=np.int32)
        
        color_hex = '#{:02X}{:02X}{:02X}'.format(*color_rgb)
        
        region = Region(
            color_hex=color_hex,
            color_rgb=color_rgb,
            region_type='fill' if area_mm2 > DETAIL_AREA_MM2 else 'detail',
            contours=[contour],
            area_mm2=area_mm2,
            perimeter_mm=2 * (w + h) / pixels_per_mm,
            bounding_box=(x_min, y_min, w, h),
            aspect_ratio=w / max(h, 1),
            centroid=((x_min + x_max) / 2, (y_min + y_max) / 2),
        )
        regions.append(region)
    
    return regions
