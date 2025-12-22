"""Vector-based text fitting for precise number scaling in trapezoidal sectors."""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class VectorBounds:
    """Exact bounding box calculated from vector paths."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2


def calculate_vector_bounds(contours: List[List[Tuple[float, float]]]) -> Optional[VectorBounds]:
    """
    Calculate precise bounding box from vector contours.

    Args:
        contours: List of contours, each contour is list of (x, y) points

    Returns:
        VectorBounds with exact min/max coordinates, or None if empty
    """
    if not contours:
        return None

    # Flatten all points from all contours
    all_points = []
    for contour in contours:
        all_points.extend(contour)

    if not all_points:
        return None

    # Find min/max
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]

    return VectorBounds(
        min_x=min(xs),
        min_y=min(ys),
        max_x=max(xs),
        max_y=max(ys)
    )


def calculate_optimal_scale(
    vector_bounds: VectorBounds,
    target_width: float,
    target_height: float,
    maintain_aspect_ratio: bool = True,
    allow_stretch: bool = False,
    max_stretch_ratio: float = 1.0
) -> Tuple[float, float]:
    """
    Calculate optimal scale factors for fitting vector in target dimensions.

    Args:
        vector_bounds: Exact bounds of the vector shape
        target_width: Available width
        target_height: Available height
        maintain_aspect_ratio: If True, use same scale for X and Y
        allow_stretch: If True and maintain_aspect_ratio=False, allow independent scaling
        max_stretch_ratio: Maximum allowed stretch ratio (width_scale / height_scale)

    Returns:
        (scale_x, scale_y) tuple
    """
    if vector_bounds.width <= 0 or vector_bounds.height <= 0:
        return 1.0, 1.0

    # Calculate scale factors for each dimension
    scale_w = target_width / vector_bounds.width
    scale_h = target_height / vector_bounds.height

    if maintain_aspect_ratio:
        # Use minimum scale to fit in both dimensions
        scale = min(scale_w, scale_h)
        return scale, scale

    elif allow_stretch:
        # Allow independent scaling with optional stretch limit
        if max_stretch_ratio > 1.0:
            # Limit the ratio between scales
            ratio = scale_w / scale_h if scale_h > 0 else 1.0

            if ratio > max_stretch_ratio:
                # Width stretch too much - reduce it
                scale_w = scale_h * max_stretch_ratio
            elif ratio < (1.0 / max_stretch_ratio):
                # Height stretch too much - reduce it
                scale_h = scale_w * max_stretch_ratio

        return scale_w, scale_h

    else:
        # Maintain aspect ratio (same as first case)
        scale = min(scale_w, scale_h)
        return scale, scale


def calculate_tight_sector_fit(
    vector_bounds: VectorBounds,
    sector_inner_radius: float,
    sector_outer_radius: float,
    sector_angle_start: float,
    sector_angle_end: float,
    padding_factor: float = 0.85
) -> Tuple[float, float, float, float]:
    """
    Calculate optimal positioning and scaling for vector in trapezoidal sector.

    This analyzes the actual vector shape and the actual sector geometry
    to find the best fit.

    Args:
        vector_bounds: Exact bounds of the vector
        sector_inner_radius: Inner radius of sector
        sector_outer_radius: Outer radius of sector
        sector_angle_start: Start angle in radians
        sector_angle_end: End angle in radians
        padding_factor: How much of available space to use (0-1)

    Returns:
        (scale_x, scale_y, center_x, center_y) for optimal fit
    """
    # Calculate sector dimensions
    radial_height = sector_outer_radius - sector_inner_radius
    avg_radius = (sector_inner_radius + sector_outer_radius) / 2
    angular_span = sector_angle_end - sector_angle_start
    arc_width = avg_radius * angular_span

    # Apply padding
    target_h = radial_height * padding_factor
    target_w = arc_width * padding_factor

    # Calculate scale (maintain aspect ratio)
    # Use UNIFORM scaling to prevent distortion
    if vector_bounds.width <= 0 or vector_bounds.height <= 0:
        scale = 1.0
    else:
        scale_w = target_w / vector_bounds.width
        scale_h = target_h / vector_bounds.height
        # Use minimum to ensure it fits in BOTH dimensions
        scale = min(scale_w, scale_h)

    # Calculate center position of sector
    center_angle = (sector_angle_start + sector_angle_end) / 2
    center_radius = avg_radius
    center_x = center_radius * math.sin(center_angle)
    center_y = -center_radius * math.cos(center_angle)

    return scale, scale, center_x, center_y


def analyze_vector_distribution(
    contours: List[List[Tuple[float, float]]]
) -> dict:
    """
    Analyze the distribution of vector points for advanced fitting.

    This can be used to understand how "dense" different parts of the
    glyph are, which could inform more sophisticated scaling strategies.

    Args:
        contours: List of contours

    Returns:
        Dictionary with analysis metrics
    """
    if not contours:
        return {
            "total_points": 0,
            "total_contours": 0,
            "avg_points_per_contour": 0,
            "bounds": None
        }

    total_points = sum(len(c) for c in contours)
    bounds = calculate_vector_bounds(contours)

    return {
        "total_points": total_points,
        "total_contours": len(contours),
        "avg_points_per_contour": total_points / len(contours) if contours else 0,
        "bounds": bounds,
        "complexity": total_points / (bounds.width * bounds.height) if bounds and bounds.width > 0 and bounds.height > 0 else 0
    }
