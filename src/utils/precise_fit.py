"""Precise fitting algorithm that guarantees numbers stay within trapezoidal sectors."""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TrapezoidalSector:
    """Defines a trapezoidal sector in polar coordinates."""
    inner_radius: float
    outer_radius: float
    angle_start: float  # radians
    angle_end: float    # radians


def point_in_sector(x: float, y: float, sector: TrapezoidalSector) -> bool:
    """
    Check if a point (x, y) is inside the trapezoidal sector.

    The sector is defined by:
    - Inner and outer radii (rings)
    - Start and end angles

    Args:
        x, y: Point coordinates (Cartesian, origin at center)
        sector: Trapezoidal sector definition

    Returns:
        True if point is inside sector, False otherwise
    """
    # Convert to polar coordinates
    r = math.sqrt(x*x + y*y)

    # Check radial bounds
    if r < sector.inner_radius or r > sector.outer_radius:
        return False

    # Check angular bounds
    # Angle from +Y axis, clockwise (matching our coordinate system)
    angle = math.atan2(x, -y)  # atan2(x, -y) gives angle from top, clockwise

    # Normalize angles to [0, 2π)
    while angle < 0:
        angle += 2 * math.pi
    while angle >= 2 * math.pi:
        angle -= 2 * math.pi

    angle_start = sector.angle_start
    angle_end = sector.angle_end

    while angle_start < 0:
        angle_start += 2 * math.pi
    while angle_end < 0:
        angle_end += 2 * math.pi

    # Handle wraparound
    if angle_start <= angle_end:
        return angle_start <= angle <= angle_end
    else:
        # Wraps around 0
        return angle >= angle_start or angle <= angle_end


def all_points_in_sector(
    contours: List[List[Tuple[float, float]]],
    scale: float,
    offset_x: float,
    offset_y: float,
    sector: TrapezoidalSector
) -> bool:
    """
    Check if ALL points of the scaled and translated contours are inside sector.

    Args:
        contours: Vector contours (list of point lists)
        scale: Uniform scale factor applied to points
        offset_x, offset_y: Translation applied after scaling
        sector: Sector to test against

    Returns:
        True if all points are inside, False if any point is outside
    """
    for contour in contours:
        for x, y in contour:
            # Apply scaling and translation
            scaled_x = x * scale + offset_x
            scaled_y = y * scale + offset_y

            # Check if point is in sector
            if not point_in_sector(scaled_x, scaled_y, sector):
                return False

    return True


def calculate_precise_fit(
    contours: List[List[Tuple[float, float]]],
    vector_center_x: float,
    vector_center_y: float,
    sector: TrapezoidalSector,
    sector_center_x: float,
    sector_center_y: float,
    initial_scale: float,
    padding_factor: float = 0.85,
    max_iterations: int = 50
) -> float:
    """
    Calculate precise scale that ensures ALL vector points stay inside sector.

    Uses binary search to find maximum scale where all points are inside.

    Args:
        contours: Vector contours of the glyph
        vector_center_x, vector_center_y: Center of the vector bounding box
        sector: Trapezoidal sector definition
        sector_center_x, sector_center_y: Where to position the glyph center
        initial_scale: Starting scale (from bounding box calculation)
        padding_factor: Target usage of available space (0-1)
        max_iterations: Max iterations for binary search

    Returns:
        Optimal scale factor that keeps all points inside
    """
    # Helper function to test a scale with correct offset calculation
    def test_scale(scale):
        # Calculate offset for this specific scale
        offset_x = sector_center_x - (vector_center_x * scale)
        offset_y = sector_center_y - (vector_center_y * scale)
        return all_points_in_sector(contours, scale, offset_x, offset_y, sector)

    # Start with initial scale and check if it fits
    if test_scale(initial_scale):
        # Initial scale works! Try to increase it (binary search up)
        scale_min = initial_scale
        scale_max = initial_scale * 1.5  # Try up to 50% larger

        # Find upper bound that doesn't fit
        while test_scale(scale_max):
            scale_min = scale_max
            scale_max *= 1.5
            if scale_max > initial_scale * 3:  # Safety limit
                break
    else:
        # Initial scale is too large! Binary search down
        scale_min = 0.0
        scale_max = initial_scale

    # Binary search for optimal scale
    best_scale = scale_min

    for _ in range(max_iterations):
        mid_scale = (scale_min + scale_max) / 2

        if test_scale(mid_scale):
            # This scale works, try larger
            best_scale = mid_scale
            scale_min = mid_scale
        else:
            # Too large, try smaller
            scale_max = mid_scale

        # Convergence check
        if abs(scale_max - scale_min) < 0.0001:
            break

    # Apply padding factor to leave some margin
    final_scale = best_scale * padding_factor

    return final_scale


def calculate_offset_for_centering(
    vector_center_x: float,
    vector_center_y: float,
    scale: float,
    sector_center_x: float,
    sector_center_y: float
) -> Tuple[float, float]:
    """
    Calculate translation offset to center the scaled vector at sector center.

    Args:
        vector_center_x, vector_center_y: Center of vector in original coordinates
        scale: Scale factor being applied
        sector_center_x, sector_center_y: Target center position

    Returns:
        (offset_x, offset_y) translation to apply after scaling
    """
    # After scaling, the vector center will be at (vector_center * scale)
    # We want it at (sector_center)
    # So offset = sector_center - (vector_center * scale)

    offset_x = sector_center_x - (vector_center_x * scale)
    offset_y = sector_center_y - (vector_center_y * scale)

    return offset_x, offset_y


def get_sector_bounds_stats(
    contours: List[List[Tuple[float, float]]],
    scale: float,
    offset_x: float,
    offset_y: float,
    sector: TrapezoidalSector
) -> dict:
    """
    Analyze how well the contours fit in the sector.

    Returns statistics useful for debugging.
    """
    total_points = sum(len(c) for c in contours)
    inside_points = 0
    outside_points = 0

    min_r = float('inf')
    max_r = 0.0

    for contour in contours:
        for x, y in contour:
            scaled_x = x * scale + offset_x
            scaled_y = y * scale + offset_y

            r = math.sqrt(scaled_x*scaled_x + scaled_y*scaled_y)
            min_r = min(min_r, r)
            max_r = max(max_r, r)

            if point_in_sector(scaled_x, scaled_y, sector):
                inside_points += 1
            else:
                outside_points += 1

    return {
        'total_points': total_points,
        'inside_points': inside_points,
        'outside_points': outside_points,
        'all_inside': outside_points == 0,
        'min_radius': min_r,
        'max_radius': max_r,
        'sector_inner_radius': sector.inner_radius,
        'sector_outer_radius': sector.outer_radius,
    }
