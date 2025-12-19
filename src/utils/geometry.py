"""Geometric calculations for watch dial number positioning."""

import math
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class NumberPosition:
    """Position and size information for a number on the dial."""

    number: str  # The actual number/numeral to display
    angle: float  # Angle in radians (0 = 12 o'clock, clockwise)
    center_x: float  # X coordinate of number center
    center_y: float  # Y coordinate of number center
    max_height: float  # Maximum allowed height (radial direction)
    max_width: float  # Maximum allowed width (tangential direction)
    inner_radius: float  # Inner boundary of this number's sector
    outer_radius: float  # Outer boundary of this number's sector
    angle_start: float  # Start angle of sector
    angle_end: float  # End angle of sector


def get_clock_numbers(style: str, number_set: str) -> List[str]:
    """
    Get list of numbers to display based on style and set.

    Args:
        style: "decimal" or "roman"
        number_set: "all" or "cardinals"

    Returns:
        List of number strings to display
    """
    if number_set == "cardinals":
        positions = [12, 3, 6, 9]
    else:  # all
        positions = list(range(1, 13))

    if style == "roman":
        roman_numerals = {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
            11: "XI",
            12: "XII",
        }
        return [roman_numerals[i] for i in positions]
    else:  # decimal
        return [str(i) for i in positions]


def get_number_angle(hour: int) -> float:
    """
    Get the angle for a given hour position.

    Args:
        hour: Hour position (1-12)

    Returns:
        Angle in radians (0 = top/12 o'clock, increases clockwise)
    """
    # 12 o'clock is at 0 degrees (top)
    # Each hour is 30 degrees (360/12)
    # Hour 12 should be at angle 0 (top)
    # Hour 1 at 30 degrees, Hour 2 at 60 degrees, etc.
    # Formula: (hour % 12) * 30 degrees
    # For hour 12, we get 0 degrees (correct!)
    degrees = (hour % 12) * 30
    return math.radians(degrees)


def calculate_number_positions(
    outer_radius: float,
    inner_radius: float,
    vertical_margin: float,
    horizontal_margin: float,
    numbers: List[str],
) -> List[NumberPosition]:
    """
    Calculate positions and maximum sizes for all numbers.

    Each number occupies a trapezoidal sector between two circles.

    Args:
        outer_radius: Outer radius of the dial (mm)
        inner_radius: Inner radius for number placement (mm)
        vertical_margin: Radial margin from circles (mm) - this is PADDING
        horizontal_margin: Angular margin between numbers (mm) - this is PADDING
        numbers: List of numbers to position

    Returns:
        List of NumberPosition objects with sector boundaries
    """
    positions = []
    num_count = len(numbers)

    # Map numbers to hours (1-12 or subset)
    if num_count == 4:  # Cardinals only
        hour_positions = [12, 3, 6, 9]
    else:  # All numbers
        hour_positions = list(range(1, 13))

    # Calculate sector boundaries ACCOUNTING FOR MARGINS
    # Inner boundary: inner circle + vertical margin (padding from inner circle)
    sector_inner_radius = inner_radius + vertical_margin
    # Outer boundary: outer circle - vertical margin (padding from outer circle)
    sector_outer_radius = outer_radius - vertical_margin

    # Radial height available for the number
    available_height = sector_outer_radius - sector_inner_radius

    # Total angle per number
    angle_per_number = 2 * math.pi / num_count

    for number, hour in zip(numbers, hour_positions):
        # Center angle for this number
        center_angle = get_number_angle(hour)

        # Calculate angular padding (convert horizontal_margin from mm to radians)
        # Use average radius for conversion
        avg_radius = (sector_inner_radius + sector_outer_radius) / 2
        angular_padding = horizontal_margin / avg_radius if avg_radius > 0 else 0

        # Sector angle boundaries (with angular padding)
        angle_start = center_angle - (angle_per_number / 2) + angular_padding
        angle_end = center_angle + (angle_per_number / 2) - angular_padding

        # Available angular span
        available_angle = angle_end - angle_start

        # Calculate arc length at average radius (this is approximate max width)
        arc_length = avg_radius * available_angle
        available_width = max(arc_length, 0.1)

        # Center position (midpoint of the sector in both radial and angular directions)
        center_radius = (sector_inner_radius + sector_outer_radius) / 2
        center_x = center_radius * math.sin(center_angle)
        center_y = -center_radius * math.cos(center_angle)

        # Ensure non-negative dimensions
        available_height = max(available_height, 0.1)

        positions.append(
            NumberPosition(
                number=number,
                angle=center_angle,
                center_x=center_x,
                center_y=center_y,
                max_height=available_height,
                max_width=available_width,
                inner_radius=sector_inner_radius,
                outer_radius=sector_outer_radius,
                angle_start=angle_start,
                angle_end=angle_end,
            )
        )

    return positions


def point_to_cartesian(radius: float, angle: float) -> Tuple[float, float]:
    """
    Convert polar coordinates to Cartesian.

    Args:
        radius: Distance from origin
        angle: Angle in radians (0 = top, clockwise)

    Returns:
        (x, y) coordinates
    """
    x = radius * math.sin(angle)
    y = -radius * math.cos(angle)  # Negative for screen coordinates
    return x, y


def get_bounding_box(
    center_x: float, center_y: float, width: float, height: float
) -> Tuple[float, float, float, float]:
    """
    Get bounding box coordinates from center and dimensions.

    Args:
        center_x: X coordinate of center
        center_y: Y coordinate of center
        width: Width of box
        height: Height of box

    Returns:
        (x1, y1, x2, y2) - top-left and bottom-right corners
    """
    half_w = width / 2
    half_h = height / 2
    return (
        center_x - half_w,
        center_y - half_h,
        center_x + half_w,
        center_y + half_h,
    )


def scale_to_fit(
    actual_width: float,
    actual_height: float,
    max_width: float,
    max_height: float,
) -> Tuple[float, float]:
    """
    Scale dimensions to fit within maximum bounds while maintaining aspect ratio.

    Args:
        actual_width: Original width
        actual_height: Original height
        max_width: Maximum allowed width
        max_height: Maximum allowed height

    Returns:
        (scaled_width, scaled_height)
    """
    # Calculate scale factors for both dimensions
    scale_w = max_width / actual_width if actual_width > 0 else 1.0
    scale_h = max_height / actual_height if actual_height > 0 else 1.0

    # Use the smaller scale factor to fit within bounds
    scale = min(scale_w, scale_h, 1.0)  # Don't upscale

    return actual_width * scale, actual_height * scale
