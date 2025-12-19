"""Font handling and text to polygon conversion for mesh generation."""

import cairo
from typing import List, Tuple, Optional
import math


class FontHandler:
    """Handles font loading and text to path conversion."""

    def __init__(self):
        self.surface = None
        self.context = None
        self._setup_cairo()

    def _setup_cairo(self):
        """Setup a Cairo surface for font operations."""
        # Create an in-memory surface for text rendering
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1000, 1000)
        self.context = cairo.Context(self.surface)

    def get_text_path(
        self, text: str, font_desc: str, target_height: float
    ) -> Tuple[List[List[Tuple[float, float]]], float, float]:
        """
        Convert text to a list of polygonal paths.

        Args:
            text: The text to convert
            font_desc: Font description string (e.g., "Sans Bold 12")
            target_height: Desired height in mm

        Returns:
            Tuple of (paths, actual_width, actual_height)
            - paths: List of contours, each contour is a list of (x, y) points
            - actual_width: Actual width of the text
            - actual_height: Actual height of the text
        """
        ctx = self.context

        # Parse font description
        font_family, font_size = self._parse_font_desc(font_desc)

        # Set font
        ctx.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(font_size)

        # Get text extents
        extents = ctx.text_extents(text)
        text_width = extents.width
        text_height = extents.height

        # Calculate scale to match target height
        if text_height > 0:
            scale = target_height / text_height
        else:
            scale = 1.0

        # Create path from text
        ctx.save()
        ctx.new_path()

        # Position text at origin
        ctx.move_to(-extents.x_bearing, -extents.y_bearing)
        ctx.text_path(text)

        # Get the path
        path = ctx.copy_path()

        # Convert Cairo path to list of contours
        contours = self._cairo_path_to_contours(path, scale)

        ctx.restore()

        # Calculate actual dimensions after scaling
        actual_width = text_width * scale
        actual_height = text_height * scale

        return contours, actual_width, actual_height

    def _parse_font_desc(self, font_desc: str) -> Tuple[str, float]:
        """
        Parse font description string.

        Args:
            font_desc: Font description like "Sans Bold 12"

        Returns:
            (font_family, font_size)
        """
        parts = font_desc.split()
        if len(parts) >= 2:
            try:
                # Last part should be size
                font_size = float(parts[-1])
                font_family = " ".join(parts[:-1])
            except ValueError:
                # If last part is not a number, use default size
                font_family = font_desc
                font_size = 12.0
        else:
            font_family = font_desc if font_desc else "Sans"
            font_size = 12.0

        return font_family, font_size

    def _cairo_path_to_contours(
        self, path: cairo.Path, scale: float = 1.0
    ) -> List[List[Tuple[float, float]]]:
        """
        Convert Cairo path to list of contours.

        Args:
            path: Cairo path object
            scale: Scale factor to apply

        Returns:
            List of contours, each contour is a list of (x, y) points
        """
        contours = []
        current_contour = []

        for path_type, points in path:
            if path_type == cairo.PATH_MOVE_TO:
                # Start new contour
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []
                x, y = points
                current_contour.append((x * scale, y * scale))

            elif path_type == cairo.PATH_LINE_TO:
                x, y = points
                current_contour.append((x * scale, y * scale))

            elif path_type == cairo.PATH_CURVE_TO:
                # Approximate Bezier curve with line segments
                # points = (x1, y1, x2, y2, x3, y3)
                if current_contour:
                    start = current_contour[-1]
                else:
                    start = (0, 0)

                curve_points = self._bezier_to_lines(
                    start, (points[0], points[1]), (points[2], points[3]), (points[4], points[5])
                )

                for x, y in curve_points:
                    current_contour.append((x * scale, y * scale))

            elif path_type == cairo.PATH_CLOSE_PATH:
                # Close current contour
                if current_contour and len(current_contour) > 0:
                    # Ensure contour is closed by adding first point at end if needed
                    if current_contour[0] != current_contour[-1]:
                        current_contour.append(current_contour[0])
                    contours.append(current_contour)
                    current_contour = []

        # Add last contour if any
        if current_contour:
            contours.append(current_contour)

        return contours

    def _bezier_to_lines(
        self,
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        num_segments: int = 10,
    ) -> List[Tuple[float, float]]:
        """
        Approximate a cubic Bezier curve with line segments.

        Args:
            p0: Start point
            p1: First control point
            p2: Second control point
            p3: End point
            num_segments: Number of line segments to use

        Returns:
            List of points approximating the curve
        """
        points = []

        for i in range(1, num_segments + 1):
            t = i / num_segments

            # Cubic Bezier formula
            x = (
                (1 - t) ** 3 * p0[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * p3[0]
            )

            y = (
                (1 - t) ** 3 * p0[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * p3[1]
            )

            points.append((x, y))

        return points

    def get_font_metrics(self, font_desc: str) -> dict:
        """
        Get metrics for a font.

        Args:
            font_desc: Font description string

        Returns:
            Dictionary with font metrics
        """
        ctx = self.context
        font_family, font_size = self._parse_font_desc(font_desc)

        ctx.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(font_size)

        font_extents = ctx.font_extents()

        return {
            "ascent": font_extents[0],
            "descent": font_extents[1],
            "height": font_extents[2],
            "max_x_advance": font_extents[3],
            "max_y_advance": font_extents[4],
        }
