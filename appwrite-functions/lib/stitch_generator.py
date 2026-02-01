"""
Stitch Generation Module for PP1 Embroidery

Stage 5 of the digitizing pipeline:
- Scanline fill algorithm for regions
- Bean stitch (3× run) for outlines
- Adaptive stitch length
- Travel optimization
- Output pyembroidery.EmbPattern

Optimized for Brother PP1 hobbyist embroidery machine.
"""

import math
import numpy as np
from typing import List, Tuple, Optional

# Try to import pyembroidery
try:
    import pyembroidery
    HAS_PYEMBROIDERY = True
except ImportError:
    HAS_PYEMBROIDERY = False

from .stitch_planner import StitchPlan, StitchOperation, StitchType


# Stitch generation constants
STITCH_LENGTH_MIN_MM = 1.0
STITCH_LENGTH_MAX_MM = 3.5
STITCH_LENGTH_TARGET_MM = 2.0

# Embroidery units: 10 units = 1mm in PES format
UNITS_PER_MM = 10


def generate_stitches(
    plan: StitchPlan,
    pixels_per_mm: float = 10.0,
    center_offset: Tuple[float, float] = (0, 0),
) -> 'pyembroidery.EmbPattern':
    """
    Generate embroidery pattern from stitch plan.
    
    Main entry point for stitch generation:
    1. Create EmbPattern
    2. For each layer (color):
       - Add thread
       - Generate stitches for each operation
       - Add color change
    3. Finalize pattern
    
    Args:
        plan: StitchPlan from stitch_planner
        pixels_per_mm: Scale factor (from preprocessing)
        center_offset: Offset to center in hoop (pixels)
        
    Returns:
        pyembroidery.EmbPattern ready for PES export
    """
    if not HAS_PYEMBROIDERY:
        raise ImportError("pyembroidery is required for stitch generation")
    
    pattern = pyembroidery.EmbPattern()
    
    # Set metadata
    pattern.extras['name'] = 'StitchFlow Design'
    pattern.extras['author'] = 'StitchFlow App'
    
    # Process each layer
    for layer in plan.layers:
        # Add thread
        r, g, b = layer.color_rgb
        thread = pyembroidery.EmbThread(r, g, b)
        thread.description = layer.thread_name or layer.color_hex
        thread.catalog_number = layer.thread_number or '000'
        pattern.add_thread(thread)
        
        # Generate stitches for each operation in this layer
        first_stitch_in_layer = True
        
        for op in layer.operations:
            stitches = generate_operation_stitches(
                op, pixels_per_mm, center_offset
            )
            
            for i, (x, y) in enumerate(stitches):
                if first_stitch_in_layer and i == 0:
                    # First stitch: move without sewing (use move_abs for compatibility)
                    try:
                        pattern.move_abs(x, y)
                    except Exception:
                        # Fallback if move_abs not available
                        pattern.add_stitch_absolute(getattr(pyembroidery, 'JUMP', pyembroidery.STITCH), x, y)
                    first_stitch_in_layer = False
                else:
                    try:
                        pattern.stitch_abs(x, y)
                    except Exception:
                        pattern.add_stitch_absolute(pyembroidery.STITCH, x, y)
        
        # Color change after this layer
        pattern.color_change()
    
    # End pattern
    pattern.end()
    
    return pattern


def generate_operation_stitches(
    op: StitchOperation,
    pixels_per_mm: float,
    center_offset: Tuple[float, float],
) -> List[Tuple[int, int]]:
    """
    Generate stitch coordinates for a single operation.
    
    Routes to appropriate generator based on stitch type.
    """
    if op.stitch_type == StitchType.FILL:
        return generate_fill_stitches(
            op.contour, op.angle, op.density, op.stitch_length,
            pixels_per_mm, center_offset
        )
    elif op.stitch_type == StitchType.UNDERLAY:
        return generate_fill_stitches(
            op.contour, op.angle, op.density, op.stitch_length,
            pixels_per_mm, center_offset
        )
    elif op.stitch_type == StitchType.OUTLINE:
        return generate_outline_stitches(
            op.contour, op.stitch_length, pixels_per_mm, center_offset
        )
    elif op.stitch_type == StitchType.DETAIL:
        # Detail uses lighter fill
        return generate_fill_stitches(
            op.contour, op.angle, op.density * 0.8, op.stitch_length,
            pixels_per_mm, center_offset
        )
    
    return []


def generate_fill_stitches(
    contour: List,
    angle: float,
    density: float,
    stitch_length: float,
    pixels_per_mm: float,
    center_offset: Tuple[float, float],
) -> List[Tuple[int, int]]:
    """
    Generate scanline fill stitches for a region.
    
    Algorithm:
    1. Convert contour to numpy array
    2. Rotate to align with stitch angle
    3. Generate horizontal scanlines at density spacing
    4. Find intersections with contour
    5. Generate stitches along scanlines (zigzag)
    6. Rotate back and convert to embroidery units
    """
    if not contour:
        return []
    
    # Convert to numpy array
    points = np.array(contour).reshape(-1, 2).astype(np.float64)
    
    if len(points) < 3:
        return []
    
    # Calculate spacing between scanlines (pixels)
    line_spacing_px = pixels_per_mm / density
    
    # Rotate points to align with stitch angle
    angle_rad = math.radians(-angle)  # Negative for rotation
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    
    # Center of rotation
    center = np.mean(points, axis=0)
    
    # Rotate
    rotated = rotate_points(points, center, angle_rad)
    
    # Get bounding box of rotated contour
    min_y = np.min(rotated[:, 1])
    max_y = np.max(rotated[:, 1])
    
    # Generate scanlines
    stitches_rotated = []
    direction = 1  # Alternate direction for efficiency
    
    y = min_y + line_spacing_px / 2
    while y <= max_y:
        # Find intersections with contour at this y
        intersections = find_scanline_intersections(rotated, y)
        
        if len(intersections) >= 2:
            # Sort intersections
            intersections.sort()
            
            # Process pairs (enter/exit)
            for i in range(0, len(intersections) - 1, 2):
                x_start = intersections[i]
                x_end = intersections[i + 1] if i + 1 < len(intersections) else intersections[i]
                
                # Generate stitches along this segment
                segment_stitches = generate_line_stitches(
                    x_start, y, x_end, y,
                    stitch_length * pixels_per_mm,
                    direction
                )
                stitches_rotated.extend(segment_stitches)
        
        y += line_spacing_px
        direction *= -1  # Alternate
    
    # Rotate stitches back
    if not stitches_rotated:
        return []
    
    stitches_array = np.array(stitches_rotated)
    stitches_original = rotate_points(stitches_array, center, -angle_rad)
    
    # Convert to embroidery units (centered)
    result = []
    for x, y in stitches_original:
        # Apply center offset and convert to embroidery units
        ex = int((x - center_offset[0]) * UNITS_PER_MM / pixels_per_mm)
        ey = int((y - center_offset[1]) * UNITS_PER_MM / pixels_per_mm)
        result.append((ex, ey))
    
    return result


def generate_outline_stitches(
    contour: List,
    stitch_length: float,
    pixels_per_mm: float,
    center_offset: Tuple[float, float],
    passes: int = 3,  # Bean stitch = 3 passes
) -> List[Tuple[int, int]]:
    """
    Generate bean stitch (3× run) outline.
    
    Bean stitch provides strong, visible outlines by passing
    over the same path 3 times:
    1. Forward
    2. Backward
    3. Forward
    """
    if not contour:
        return []
    
    points = np.array(contour).reshape(-1, 2).astype(np.float64)
    
    if len(points) < 2:
        return []
    
    # Subdivide contour into even stitch lengths
    subdivided = subdivide_contour(points, stitch_length * pixels_per_mm)
    
    if len(subdivided) < 2:
        return []
    
    # Generate stitch sequence: forward, backward, forward
    all_stitches = []
    
    for pass_num in range(passes):
        if pass_num % 2 == 0:
            # Forward pass
            stitch_points = subdivided
        else:
            # Backward pass
            stitch_points = subdivided[::-1]
        
        for x, y in stitch_points:
            ex = int((x - center_offset[0]) * UNITS_PER_MM / pixels_per_mm)
            ey = int((y - center_offset[1]) * UNITS_PER_MM / pixels_per_mm)
            all_stitches.append((ex, ey))
    
    return all_stitches


def rotate_points(
    points: np.ndarray,
    center: np.ndarray,
    angle_rad: float,
) -> np.ndarray:
    """Rotate points around a center."""
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    centered = points - center
    rotated = np.zeros_like(centered)
    rotated[:, 0] = centered[:, 0] * cos_a - centered[:, 1] * sin_a
    rotated[:, 1] = centered[:, 0] * sin_a + centered[:, 1] * cos_a
    
    return rotated + center


def find_scanline_intersections(
    contour: np.ndarray,
    y: float,
) -> List[float]:
    """Find x coordinates where a horizontal line intersects the contour."""
    intersections = []
    n = len(contour)
    
    for i in range(n):
        p1 = contour[i]
        p2 = contour[(i + 1) % n]
        
        # Check if scanline crosses this edge
        if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
            # Linear interpolation for x
            if p2[1] != p1[1]:
                t = (y - p1[1]) / (p2[1] - p1[1])
                x = p1[0] + t * (p2[0] - p1[0])
                intersections.append(x)
    
    return intersections


def generate_line_stitches(
    x1: float, y1: float,
    x2: float, y2: float,
    stitch_length_px: float,
    direction: int = 1,
) -> List[Tuple[float, float]]:
    """Generate evenly spaced stitches along a line segment."""
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    
    if length < stitch_length_px / 2:
        # Too short, just one stitch
        return [(x1, y1), (x2, y2)]
    
    # Calculate number of stitches
    num_stitches = max(2, int(length / stitch_length_px) + 1)
    
    stitches = []
    for i in range(num_stitches):
        t = i / (num_stitches - 1) if num_stitches > 1 else 0
        if direction < 0:
            t = 1 - t
        x = x1 + t * dx
        y = y1 + t * dy
        stitches.append((x, y))
    
    return stitches


def subdivide_contour(
    points: np.ndarray,
    target_length: float,
) -> np.ndarray:
    """
    Subdivide contour into evenly spaced points.
    
    Used for outline stitches to ensure consistent stitch length.
    """
    if len(points) < 2:
        return points
    
    # Calculate total perimeter
    perimeter = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        perimeter += np.linalg.norm(p2 - p1)
    
    # Number of subdivisions
    num_points = max(3, int(perimeter / target_length))
    
    # Resample at even intervals
    result = []
    target_spacing = perimeter / num_points
    
    accumulated = 0
    next_target = 0
    point_idx = 0
    
    # Add first point
    result.append(points[0].tolist())
    
    while point_idx < len(points) - 1 and len(result) < num_points:
        p1 = points[point_idx]
        p2 = points[point_idx + 1]
        segment_length = np.linalg.norm(p2 - p1)
        
        while next_target < accumulated + segment_length and len(result) < num_points:
            # Interpolate within this segment
            t = (next_target - accumulated) / segment_length if segment_length > 0 else 0
            t = max(0, min(1, t))
            new_point = p1 + t * (p2 - p1)
            result.append(new_point.tolist())
            next_target += target_spacing
        
        accumulated += segment_length
        point_idx += 1
    
    # Ensure we close the contour
    if len(result) > 0:
        result.append(points[0].tolist())
    
    return np.array(result)


def optimize_travel_path(
    layers: List,
) -> List:
    """
    Optimize stitch order to minimize travel (jump) stitches.
    
    Uses nearest-neighbor heuristic for simplicity.
    Full TSP would be better but too slow for real-time.
    """
    # TODO: Implement travel optimization
    # For now, just return layers as-is
    return layers


def add_tie_offs(
    pattern: 'pyembroidery.EmbPattern',
    tie_length: float = 0.5,  # mm
) -> None:
    """
    Add tie-off stitches at start/end of color blocks.
    
    Tie-offs secure the thread and prevent unraveling.
    """
    # TODO: Implement tie-offs
    pass


def write_pes(
    pattern: 'pyembroidery.EmbPattern',
    output_path: str,
) -> bytes:
    """Write pattern to PES file."""
    import io
    
    if isinstance(output_path, str):
        pyembroidery.write_pes(pattern, output_path)
        with open(output_path, 'rb') as f:
            return f.read()
    else:
        # Write to bytes buffer
        buffer = io.BytesIO()
        pyembroidery.write_pes(pattern, buffer)
        buffer.seek(0)
        return buffer.read()


def generate_preview_image(
    pattern: 'pyembroidery.EmbPattern',
) -> Optional[bytes]:
    """Generate PNG preview of the pattern."""
    import io
    
    if not HAS_PYEMBROIDERY:
        return None
    
    try:
        buffer = io.BytesIO()
        pyembroidery.write_png(pattern, buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception:
        return None
