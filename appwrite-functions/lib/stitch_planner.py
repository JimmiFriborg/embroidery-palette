"""
Stitch Planning Module for PP1 Embroidery

Stage 4 of the digitizing pipeline:
- Determine stitch type per region (fill/outline/satin)
- Calculate density and angle
- Plan underlay (for large fills)
- Estimate stitch count and sewing time
- PP1 compatibility validation

Optimized for Brother PP1 hobbyist embroidery machine.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Import Region type
from .shape_analyzer import Region


class StitchType(Enum):
    """Types of stitches we can generate."""
    FILL = 'fill'           # Scanline fill for large areas
    OUTLINE = 'outline'     # Bean stitch (3× run) for edges
    SATIN = 'satin'         # Column stitch (not used for PP1)
    DETAIL = 'detail'       # Light fill for small elements
    UNDERLAY = 'underlay'   # Base layer under fills


class QualityPreset(Enum):
    """Quality presets for different use cases."""
    FAST = 'fast'           # Quick tests, simple designs
    BALANCED = 'balanced'   # General use (default)
    QUALITY = 'quality'     # Complex designs, show pieces


# PP1-optimized defaults
PP1_DEFAULTS = {
    'fill_density': 5.0,           # stitches per mm
    'outline_density': 0.5,        # ~2mm per stitch
    'bean_stitch_repeat': 3,       # 3× for clarity
    'stitch_length_target': 2.0,   # mm (PP1 sweet spot)
    'stitch_length_min': 1.0,      # mm (tight curves)
    'stitch_length_max': 3.5,      # mm (straight runs)
    'underlay_threshold_mm2': 50,  # Use underlay for fills > 50mm²
    'underlay_density_ratio': 0.5, # Half density for underlay
    'underlay_angle_offset': 90,   # Perpendicular to fill
    'max_recommended_stitches': 15000,
    'max_stitches_hard_limit': 20000,
    'sewing_speed_stitches_per_min': 400,  # Approximate for PP1
}

# Quality preset multipliers
QUALITY_MULTIPLIERS = {
    QualityPreset.FAST: {
        'density': 0.8,
        'underlay': False,
    },
    QualityPreset.BALANCED: {
        'density': 1.0,
        'underlay': True,  # Selective
    },
    QualityPreset.QUALITY: {
        'density': 1.2,
        'underlay': True,  # Frequent
    },
}


@dataclass
class StitchOperation:
    """
    A single stitch operation within a layer.
    
    Represents one contiguous set of stitches (e.g., one fill region,
    one outline pass).
    """
    stitch_type: StitchType
    region: Region                          # Source region
    contour: list                           # Points to stitch
    angle: float = 0.0                      # Stitch angle (degrees)
    density: float = 5.0                    # Stitches per mm
    stitch_length: float = 2.0              # Target stitch length (mm)
    estimated_stitches: int = 0             # Predicted count
    is_underlay: bool = False               # True if this is underlay


@dataclass
class StitchLayer:
    """
    All operations for one thread color.
    
    A layer is stitched continuously before changing thread.
    """
    color_hex: str
    color_rgb: Tuple[int, int, int]
    thread_number: Optional[str] = None     # Brother thread ID
    thread_name: Optional[str] = None
    operations: List[StitchOperation] = field(default_factory=list)
    estimated_stitches: int = 0
    
    def add_operation(self, op: StitchOperation):
        """Add an operation and update stitch count."""
        self.operations.append(op)
        self.estimated_stitches += op.estimated_stitches


@dataclass
class StitchPlan:
    """
    Complete stitch plan for a design.
    
    Contains all layers, operations, and metadata.
    """
    layers: List[StitchLayer] = field(default_factory=list)
    total_stitches: int = 0
    estimated_time_minutes: float = 0.0
    quality_preset: str = 'balanced'
    hoop_size: str = '100x100'
    warnings: List[str] = field(default_factory=list)
    
    def add_layer(self, layer: StitchLayer):
        """Add a layer and update totals."""
        self.layers.append(layer)
        self.total_stitches += layer.estimated_stitches
    
    def finalize(self):
        """Calculate final estimates and validate."""
        self.total_stitches = sum(l.estimated_stitches for l in self.layers)
        self.estimated_time_minutes = (
            self.total_stitches / PP1_DEFAULTS['sewing_speed_stitches_per_min']
        )
        self._validate()
    
    def _validate(self):
        """Check PP1 compatibility and add warnings."""
        if self.total_stitches > PP1_DEFAULTS['max_stitches_hard_limit']:
            self.warnings.append(
                f"⚠️ Stitch count ({self.total_stitches:,}) exceeds PP1 maximum "
                f"({PP1_DEFAULTS['max_stitches_hard_limit']:,}). Reduce complexity."
            )
        elif self.total_stitches > PP1_DEFAULTS['max_recommended_stitches']:
            self.warnings.append(
                f"⚠️ High stitch count ({self.total_stitches:,}). Consider reducing "
                f"density or simplifying design for smoother sewing."
            )
        
        if len(self.layers) > 10:
            self.warnings.append(
                f"⚠️ Many thread colors ({len(self.layers)}). Consider reducing "
                f"for faster sewing and fewer thread changes."
            )


def plan_stitches(
    regions: List[Region],
    hoop_size: str = '100x100',
    quality_preset: str = 'balanced',
    density_multiplier: float = 1.0,
    thread_mappings: Optional[Dict[str, dict]] = None,
) -> StitchPlan:
    """
    Create a stitch plan from extracted regions.
    
    Main entry point for stitch planning:
    1. Group regions by color
    2. Plan operations for each region
    3. Calculate stitch counts
    4. Validate for PP1 compatibility
    
    Args:
        regions: List of Region objects from shape_analyzer
        hoop_size: Target hoop size
        quality_preset: 'fast', 'balanced', or 'quality'
        density_multiplier: Additional density scaling (0.5-2.0)
        thread_mappings: Optional color → thread info dict
        
    Returns:
        StitchPlan with all layers and operations
    """
    # Parse quality preset
    try:
        preset = QualityPreset(quality_preset)
    except ValueError:
        preset = QualityPreset.BALANCED
    
    preset_config = QUALITY_MULTIPLIERS[preset]
    effective_density = preset_config['density'] * density_multiplier
    use_underlay = preset_config['underlay']
    
    # Group regions by color
    by_color: Dict[str, List[Region]] = {}
    for region in regions:
        if region.color_hex not in by_color:
            by_color[region.color_hex] = []
        by_color[region.color_hex].append(region)
    
    # Create plan
    plan = StitchPlan(
        quality_preset=quality_preset,
        hoop_size=hoop_size,
    )
    
    # Create a layer for each color
    for color_hex, color_regions in by_color.items():
        # Get thread info from mappings if provided
        thread_info = thread_mappings.get(color_hex, {}) if thread_mappings else {}
        
        layer = StitchLayer(
            color_hex=color_hex,
            color_rgb=color_regions[0].color_rgb,
            thread_number=thread_info.get('threadNumber'),
            thread_name=thread_info.get('threadName'),
        )
        
        # Plan operations for each region of this color
        for region in color_regions:
            operations = plan_region_operations(
                region, effective_density, use_underlay
            )
            for op in operations:
                layer.add_operation(op)
        
        if layer.operations:
            plan.add_layer(layer)
    
    plan.finalize()
    return plan


def plan_region_operations(
    region: Region,
    density_multiplier: float = 1.0,
    use_underlay: bool = True,
) -> List[StitchOperation]:
    """
    Plan stitch operations for a single region.
    
    Based on region type, creates appropriate operations:
    - Fill: Underlay (optional) + scanline fill + outline
    - Outline: Bean stitch only
    - Detail: Light fill + outline
    """
    operations = []
    
    base_fill_density = PP1_DEFAULTS['fill_density'] * density_multiplier
    
    if region.region_type == 'fill':
        # Large fill region: underlay + fill + outline
        
        # 1. Underlay (if enabled and area is large enough)
        if use_underlay and region.area_mm2 > PP1_DEFAULTS['underlay_threshold_mm2']:
            underlay_op = create_underlay_operation(region, base_fill_density)
            operations.append(underlay_op)
        
        # 2. Main fill
        fill_op = create_fill_operation(region, base_fill_density)
        operations.append(fill_op)
        
        # 3. Outline
        outline_op = create_outline_operation(region)
        operations.append(outline_op)
        
    elif region.region_type == 'outline':
        # Thin stroke: bean stitch only
        outline_op = create_outline_operation(region)
        operations.append(outline_op)
        
    elif region.region_type == 'detail':
        # Small element: light fill + outline
        fill_op = create_fill_operation(
            region, base_fill_density * 0.8  # Lighter density
        )
        operations.append(fill_op)
        
        outline_op = create_outline_operation(region)
        operations.append(outline_op)
    
    return operations


def create_fill_operation(
    region: Region,
    density: float,
) -> StitchOperation:
    """Create a fill stitch operation for a region."""
    # Estimate stitch count for fill
    # Rough formula: area × density² (stitches cover area)
    estimated = estimate_fill_stitches(region.area_mm2, density)
    
    return StitchOperation(
        stitch_type=StitchType.FILL,
        region=region,
        contour=region.contours[0].tolist() if region.contours else [],
        angle=region.principal_angle,
        density=density,
        stitch_length=PP1_DEFAULTS['stitch_length_target'],
        estimated_stitches=estimated,
        is_underlay=False,
    )


def create_outline_operation(region: Region) -> StitchOperation:
    """Create a bean stitch outline operation."""
    # Bean stitch: 3 passes along the contour
    perimeter_mm = region.perimeter_mm
    stitch_length = PP1_DEFAULTS['stitch_length_target']
    
    # Stitches = (perimeter / stitch_length) × 3 passes
    estimated = int((perimeter_mm / stitch_length) * PP1_DEFAULTS['bean_stitch_repeat'])
    
    return StitchOperation(
        stitch_type=StitchType.OUTLINE,
        region=region,
        contour=region.contours[0].tolist() if region.contours else [],
        angle=0,  # Not used for outlines
        density=PP1_DEFAULTS['outline_density'],
        stitch_length=stitch_length,
        estimated_stitches=estimated,
        is_underlay=False,
    )


def create_underlay_operation(
    region: Region,
    base_density: float,
) -> StitchOperation:
    """Create an underlay operation for stabilization."""
    # Underlay: half density, perpendicular angle
    underlay_density = base_density * PP1_DEFAULTS['underlay_density_ratio']
    underlay_angle = (region.principal_angle + PP1_DEFAULTS['underlay_angle_offset']) % 180
    
    estimated = estimate_fill_stitches(region.area_mm2, underlay_density)
    
    return StitchOperation(
        stitch_type=StitchType.UNDERLAY,
        region=region,
        contour=region.contours[0].tolist() if region.contours else [],
        angle=underlay_angle,
        density=underlay_density,
        stitch_length=PP1_DEFAULTS['stitch_length_max'],  # Longer for underlay
        estimated_stitches=estimated,
        is_underlay=True,
    )


def estimate_fill_stitches(area_mm2: float, density: float) -> int:
    """
    Estimate stitch count for a fill region.
    
    Uses empirical formula based on area and density.
    """
    # Rough approximation: 
    # - Scanline spacing = 1/density mm
    # - Average scanline length ≈ √area mm
    # - Number of scanlines ≈ √area × density
    # - Total stitches ≈ scanlines × (scanline_length / stitch_length)
    
    sqrt_area = math.sqrt(area_mm2)
    num_scanlines = sqrt_area * density
    avg_scanline_stitches = sqrt_area / PP1_DEFAULTS['stitch_length_target']
    
    return int(num_scanlines * avg_scanline_stitches)


def estimate_sewing_time(stitch_count: int) -> float:
    """Estimate sewing time in minutes."""
    return stitch_count / PP1_DEFAULTS['sewing_speed_stitches_per_min']


def validate_plan(plan: StitchPlan) -> List[str]:
    """
    Validate a stitch plan for PP1 compatibility.
    
    Returns list of warning messages.
    """
    warnings = []
    
    if plan.total_stitches > PP1_DEFAULTS['max_stitches_hard_limit']:
        warnings.append(
            f"Stitch count {plan.total_stitches:,} exceeds PP1 limit of "
            f"{PP1_DEFAULTS['max_stitches_hard_limit']:,}"
        )
    elif plan.total_stitches > PP1_DEFAULTS['max_recommended_stitches']:
        warnings.append(
            f"High stitch count ({plan.total_stitches:,}). May cause slow sewing."
        )
    
    if len(plan.layers) > 15:
        warnings.append(
            f"Many thread colors ({len(plan.layers)}). Consider simplifying."
        )
    
    return warnings


def get_plan_summary(plan: StitchPlan) -> dict:
    """Get a summary of the stitch plan for display."""
    return {
        'total_stitches': plan.total_stitches,
        'estimated_time_minutes': round(plan.estimated_time_minutes, 1),
        'num_colors': len(plan.layers),
        'quality_preset': plan.quality_preset,
        'hoop_size': plan.hoop_size,
        'warnings': plan.warnings,
        'layers': [
            {
                'color': layer.color_hex,
                'thread_name': layer.thread_name,
                'stitches': layer.estimated_stitches,
                'num_operations': len(layer.operations),
            }
            for layer in plan.layers
        ],
    }
