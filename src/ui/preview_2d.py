"""2D preview widget using Cairo for rendering watch dial."""

import gi
import math

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk
import cairo
from typing import Optional, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.geometry import (
    calculate_number_positions,
    get_clock_numbers,
    NumberPosition,
)
from utils.vector_fit import (
    calculate_tight_sector_fit,
    calculate_vector_bounds,
    VectorBounds,
)
from utils.precise_fit import (
    TrapezoidalSector,
    calculate_precise_fit,
    calculate_offset_for_centering,
    get_sector_bounds_stats,
)
from core.distortion_2d import Distortion2D


class Preview2DWidget(Gtk.DrawingArea):
    """Interactive 2D preview of the watch dial with zoom and pan."""

    def __init__(self):
        super().__init__()

        # Drawing parameters
        self.outer_radius = 50.0
        self.inner_radius = 35.0
        self.vertical_margin = 1.0
        self.horizontal_margin = 1.0
        self.number_style = "decimal"
        self.number_set = "all"
        self.font_desc = "Sans Bold 12"

        # Distortion parameters
        self.edge_irregularity = 0.0
        self.surface_roughness = 0.0
        self.perspective_stretch = 0.0
        self.erosion = 0.0

        # Distortion filter instance
        self.distortion_filter = Distortion2D(seed=42)

        # View transformation
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        # Interaction state
        self.dragging = False
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0

        # Setup drawing function
        self.set_draw_func(self._draw)

        # Setup input handlers
        self._setup_input_handlers()

        # Request reasonable size
        self.set_content_width(600)
        self.set_content_height(600)

    def _setup_input_handlers(self):
        """Setup mouse and scroll input handlers."""
        # Scroll for zoom
        scroll_controller = Gtk.EventControllerScroll()
        scroll_controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_controller.connect("scroll", self._on_scroll)
        self.add_controller(scroll_controller)

        # Drag for pan
        drag_controller = Gtk.GestureDrag()
        drag_controller.connect("drag-begin", self._on_drag_begin)
        drag_controller.connect("drag-update", self._on_drag_update)
        drag_controller.connect("drag-end", self._on_drag_end)
        self.add_controller(drag_controller)

    def update_parameters(
        self,
        outer_radius: float,
        inner_radius: float,
        vertical_margin: float,
        horizontal_margin: float,
        number_style: str,
        number_set: str,
        font_desc: str,
        edge_irregularity: float = 0.0,
        surface_roughness: float = 0.0,
        perspective_stretch: float = 0.0,
        erosion: float = 0.0,
    ):
        """Update drawing parameters and refresh."""
        self.outer_radius = outer_radius
        self.inner_radius = inner_radius
        self.vertical_margin = vertical_margin
        self.horizontal_margin = horizontal_margin
        self.number_style = number_style
        self.number_set = number_set
        self.font_desc = font_desc
        self.edge_irregularity = edge_irregularity
        self.surface_roughness = surface_roughness
        self.perspective_stretch = perspective_stretch
        self.erosion = erosion
        self.queue_draw()

    def reset_view(self):
        """Reset zoom and pan to defaults."""
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.queue_draw()

    def _draw(self, area: Gtk.DrawingArea, ctx: cairo.Context, width: int, height: int):
        """Main drawing function."""
        # Clear background
        ctx.set_source_rgb(0.98, 0.98, 0.98)  # Light gray background
        ctx.paint()

        # Save context
        ctx.save()

        # Apply transformations: center, zoom, pan
        ctx.translate(width / 2, height / 2)
        ctx.scale(self.zoom, self.zoom)
        ctx.translate(self.pan_x, self.pan_y)

        # Calculate scale factor to fit dial in view
        # Leave some padding (80% of available space)
        max_dimension = min(width, height) * 0.8
        scale = max_dimension / (2 * self.outer_radius)
        ctx.scale(scale, scale)

        # Draw the dial elements
        self._draw_grid(ctx)
        self._draw_radii(ctx)
        self._draw_numbers(ctx)
        self._draw_dimensions(ctx)

        # Restore context
        ctx.restore()

    def _draw_grid(self, ctx: cairo.Context):
        """Draw optional grid for reference."""
        ctx.save()

        # Light grid lines
        ctx.set_source_rgba(0.85, 0.85, 0.85, 0.5)
        ctx.set_line_width(0.2)

        # Draw grid based on outer radius
        grid_spacing = self.outer_radius / 5
        max_extent = self.outer_radius * 1.5

        # Vertical lines
        x = -max_extent
        while x <= max_extent:
            ctx.move_to(x, -max_extent)
            ctx.line_to(x, max_extent)
            x += grid_spacing

        # Horizontal lines
        y = -max_extent
        while y <= max_extent:
            ctx.move_to(-max_extent, y)
            ctx.line_to(max_extent, y)
            y += grid_spacing

        ctx.stroke()
        ctx.restore()

    def _draw_radii(self, ctx: cairo.Context):
        """Draw outer and inner radius circles."""
        ctx.save()

        # Outer radius - thick blue line
        ctx.set_source_rgb(0.2, 0.4, 0.8)
        ctx.set_line_width(0.5)
        ctx.arc(0, 0, self.outer_radius, 0, 2 * math.pi)
        ctx.stroke()

        # Inner radius - thick green line
        ctx.set_source_rgb(0.2, 0.7, 0.3)
        ctx.set_line_width(0.5)
        ctx.arc(0, 0, self.inner_radius, 0, 2 * math.pi)
        ctx.stroke()

        # Center point
        ctx.set_source_rgb(0.8, 0.2, 0.2)
        ctx.arc(0, 0, 0.5, 0, 2 * math.pi)
        ctx.fill()

        ctx.restore()

    def _draw_numbers(self, ctx: cairo.Context):
        """Draw numbers fitted to trapezoidal sectors using vector paths."""
        ctx.save()

        # Get numbers
        style = "roman" if self.number_style == "roman" else "decimal"
        num_set = "cardinals" if self.number_set == "cardinals" else "all"
        numbers = get_clock_numbers(style, num_set)

        # Calculate positions
        positions = calculate_number_positions(
            self.outer_radius,
            self.inner_radius,
            self.vertical_margin,
            self.horizontal_margin,
            numbers,
        )

        # Parse font
        font_family = "Sans"
        parts = self.font_desc.split()
        if len(parts) >= 2:
            font_family = " ".join(parts[:-1])
        else:
            font_family = self.font_desc

        for pos in positions:
            # 1. Draw trapezoidal sector background
            self._draw_sector(ctx, pos)

            # 2. Draw number fitted to sector
            self._draw_fitted_number(ctx, pos, font_family)

        ctx.restore()

    def _draw_sector(self, ctx: cairo.Context, pos: NumberPosition):
        """Draw trapezoidal sector shape."""
        ctx.save()
        ctx.new_path()

        # Convert to Cairo angles (0=right, counterclockwise)
        cairo_start = pos.angle_start - math.pi/2
        cairo_end = pos.angle_end - math.pi/2

        # Start at inner arc
        x = pos.inner_radius * math.sin(pos.angle_start)
        y = -pos.inner_radius * math.cos(pos.angle_start)
        ctx.move_to(x, y)

        # Arc along inner radius
        ctx.arc(0, 0, pos.inner_radius, cairo_start, cairo_end)

        # Line to outer radius
        x = pos.outer_radius * math.sin(pos.angle_end)
        y = -pos.outer_radius * math.cos(pos.angle_end)
        ctx.line_to(x, y)

        # Arc along outer radius (reverse)
        ctx.arc_negative(0, 0, pos.outer_radius, cairo_end, cairo_start)
        ctx.close_path()

        # Fill and stroke
        ctx.set_source_rgba(0.9, 0.7, 0.3, 0.15)
        ctx.fill_preserve()
        ctx.set_source_rgba(0.9, 0.6, 0.2, 0.5)
        ctx.set_line_width(0.25)
        ctx.stroke()

        ctx.restore()

    def _draw_fitted_number(self, ctx: cairo.Context, pos: NumberPosition, font_family: str):
        """Draw number fitted to sector using precise vector analysis."""
        ctx.save()

        # Setup font
        ctx.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(100.0)

        # Create text path ONCE at origin
        ctx.move_to(0, 0)
        ctx.text_path(pos.number)

        # Get Cairo path for vector analysis
        cairo_path = ctx.copy_path()

        # Get extents for quick bounds check
        x1, y1, x2, y2 = ctx.path_extents()

        if x2 - x1 <= 0 or y2 - y1 <= 0:
            ctx.restore()
            return

        # Convert Cairo path to contours for precise vector analysis
        contours = self._cairo_path_to_contours(cairo_path)

        # Calculate EXACT vector bounds from actual path points
        vector_bounds = calculate_vector_bounds(contours)

        if not vector_bounds:
            ctx.restore()
            return

        # Clear the current path - we'll redraw it transformed
        ctx.new_path()

        # Calculate sector dimensions for debug
        text_radius = (pos.inner_radius + pos.outer_radius) / 2
        angular_span = pos.angle_end - pos.angle_start
        arc_width = text_radius * angular_span
        radial_height = pos.outer_radius - pos.inner_radius

        # First get initial scale estimate from bounding box
        initial_scale_x, initial_scale_y, fit_center_x, fit_center_y = calculate_tight_sector_fit(
            vector_bounds,
            pos.inner_radius,
            pos.outer_radius,
            pos.angle_start,
            pos.angle_end,
            padding_factor=0.95  # Start with 95% for initial estimate
        )

        # Create sector definition for precise testing
        sector = TrapezoidalSector(
            inner_radius=pos.inner_radius,
            outer_radius=pos.outer_radius,
            angle_start=pos.angle_start,
            angle_end=pos.angle_end
        )

        # Use PRECISE algorithm that tests every point
        print(f"\n{'='*60}")
        print(f"NUMBER: {pos.number}")
        print(f"{'='*60}")
        print(f"Initial scale estimate: {initial_scale_x:.4f}")

        precise_scale = calculate_precise_fit(
            contours=contours,
            vector_center_x=vector_bounds.center_x,
            vector_center_y=vector_bounds.center_y,
            sector=sector,
            sector_center_x=pos.center_x,
            sector_center_y=pos.center_y,
            initial_scale=initial_scale_x,
            padding_factor=0.95,  # Use 95% of available space
            max_iterations=50
        )

        print(f"Precise scale (after verification): {precise_scale:.4f}")

        # Get stats about fit quality
        offset_x, offset_y = calculate_offset_for_centering(
            vector_bounds.center_x,
            vector_bounds.center_y,
            precise_scale,
            pos.center_x,
            pos.center_y
        )

        stats = get_sector_bounds_stats(contours, precise_scale, offset_x, offset_y, sector)
        print(f"Fit statistics:")
        print(f"  Total points: {stats['total_points']}")
        print(f"  Inside: {stats['inside_points']}, Outside: {stats['outside_points']}")
        print(f"  All inside: {stats['all_inside']}")
        print(f"  Radius range: {stats['min_radius']:.2f} - {stats['max_radius']:.2f}")
        print(f"  Sector range: {stats['sector_inner_radius']:.2f} - {stats['sector_outer_radius']:.2f}")

        scale_x = precise_scale
        scale_y = precise_scale

        # Calculate the final font size needed (scale the base 100.0)
        final_font_size = 100.0 * scale_x

        # Apply transformations - position at SECTOR center
        ctx.translate(pos.center_x, pos.center_y)
        # Don't apply scale here - we'll use the scaled font size instead
        # Center using the vector bounds center (from actual glyph geometry)
        # but also scale the translation
        ctx.translate(-vector_bounds.center_x * scale_x, -vector_bounds.center_y * scale_y)

        # DEBUG VISUALIZATION - Draw AFTER transformations
        ctx.save()

        # Draw vector bounding box in SCALED space
        ctx.set_source_rgba(0.0, 1.0, 0.0, 0.5)  # Green
        ctx.set_line_width(0.5)
        ctx.rectangle(
            vector_bounds.min_x * scale_x,
            vector_bounds.min_y * scale_y,
            vector_bounds.width * scale_x,
            vector_bounds.height * scale_y
        )
        ctx.stroke()

        # Draw all vector points as tiny dots (magenta)
        ctx.set_source_rgba(1.0, 0.0, 1.0, 0.3)  # Magenta transparent
        for contour in contours:
            for x, y in contour:
                ctx.arc(x * scale_x, y * scale_y, 0.3, 0, 2 * math.pi)
                ctx.fill()

        # Draw vector center (blue circle)
        ctx.set_source_rgb(0.0, 0.0, 1.0)  # Blue
        ctx.arc(vector_bounds.center_x * scale_x, vector_bounds.center_y * scale_y, 2.0, 0, 2 * math.pi)
        ctx.fill()

        # Draw sector center (red crosshair) - should be at origin after translate
        ctx.set_source_rgb(1.0, 0.0, 0.0)  # Red
        ctx.set_line_width(1.0)

        sector_center_x = vector_bounds.center_x * scale_x
        sector_center_y = vector_bounds.center_y * scale_y

        ctx.move_to(sector_center_x - 5.0, sector_center_y)
        ctx.line_to(sector_center_x + 5.0, sector_center_y)
        ctx.move_to(sector_center_x, sector_center_y - 5.0)
        ctx.line_to(sector_center_x, sector_center_y + 5.0)
        ctx.stroke()

        # Draw text labels with dimensions
        label_x = vector_bounds.center_x * scale_x
        label_y = vector_bounds.min_y * scale_y - 3.0

        ctx.set_source_rgb(0.0, 0.5, 0.0)
        ctx.set_font_size(2.5)

        label_text = f"{vector_bounds.width * scale_x:.1f}x{vector_bounds.height * scale_y:.1f}"
        extents = ctx.text_extents(label_text)
        ctx.move_to(label_x - extents.width/2, label_y)
        ctx.show_text(label_text)

        ctx.restore()

        # Draw the number with SCALED font size
        ctx.set_font_size(final_font_size)
        ctx.move_to(0, 0)
        ctx.text_path(pos.number)
        ctx.set_source_rgb(0.0, 0.0, 0.0)
        ctx.fill()

        ctx.restore()

    def _cairo_path_to_contours(self, path: cairo.Path) -> List[List[Tuple[float, float]]]:
        """Convert Cairo path to list of contours for vector analysis."""
        contours = []
        current_contour = []
        current_point = (0.0, 0.0)

        for path_type, points in path:
            if path_type == cairo.PATH_MOVE_TO:
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []
                x, y = points
                current_point = (x, y)
                current_contour.append((x, y))

            elif path_type == cairo.PATH_LINE_TO:
                x, y = points
                current_point = (x, y)
                current_contour.append((x, y))

            elif path_type == cairo.PATH_CURVE_TO:
                # Sample the Bezier curve properly - DON'T use control points!
                x1, y1, x2, y2, x3, y3 = points
                p0 = current_point
                p1 = (x1, y1)
                p2 = (x2, y2)
                p3 = (x3, y3)

                # Sample curve with 20 points for precision
                for i in range(1, 21):
                    t = i / 20.0
                    # Cubic Bezier formula
                    x = (
                        (1-t)**3 * p0[0] +
                        3*(1-t)**2*t * p1[0] +
                        3*(1-t)*t**2 * p2[0] +
                        t**3 * p3[0]
                    )
                    y = (
                        (1-t)**3 * p0[1] +
                        3*(1-t)**2*t * p1[1] +
                        3*(1-t)*t**2 * p2[1] +
                        t**3 * p3[1]
                    )
                    current_contour.append((x, y))

                current_point = (x3, y3)

            elif path_type == cairo.PATH_CLOSE_PATH:
                if current_contour:
                    contours.append(current_contour)
                    current_contour = []

        if current_contour:
            contours.append(current_contour)

        return contours

    def _draw_dimensions(self, ctx: cairo.Context):
        """Draw dimension lines and labels."""
        ctx.save()

        # Dimension line color
        ctx.set_source_rgb(0.3, 0.3, 0.3)
        ctx.set_line_width(0.3)

        # Outer radius dimension (horizontal)
        self._draw_dimension_line(
            ctx, 0, 0, self.outer_radius, 0, f"R{self.outer_radius:.1f}mm", offset=5
        )

        # Inner radius dimension (vertical)
        self._draw_dimension_line(
            ctx, 0, 0, 0, -self.inner_radius, f"R{self.inner_radius:.1f}mm", offset=5
        )

        # Show padding dimensions if non-zero
        if self.vertical_margin > 0 or self.horizontal_margin > 0:
            ctx.set_source_rgb(0.8, 0.3, 0.3)

            # Vertical margin
            if self.vertical_margin > 0:
                angle_right = math.pi / 2
                inner_edge = self.inner_radius + self.vertical_margin

                x1 = self.inner_radius * math.sin(angle_right)
                y1 = -self.inner_radius * math.cos(angle_right)
                x2 = inner_edge * math.sin(angle_right)
                y2 = -inner_edge * math.cos(angle_right)

                self._draw_dimension_line(
                    ctx, x1, y1, x2, y2,
                    f"V-pad:{self.vertical_margin:.1f}mm",
                    offset=3
                )

            # Horizontal margin
            if self.horizontal_margin > 0:
                label_x = 0
                label_y = -self.outer_radius - 8
                ctx.set_font_size(2.5)
                ctx.move_to(label_x - 15, label_y)
                ctx.show_text(f"H-pad:{self.horizontal_margin:.1f}mm")

        ctx.restore()

    def _draw_dimension_line(
        self,
        ctx: cairo.Context,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        label: str,
        offset: float = 5,
    ):
        """Draw a dimension line with arrows and label."""
        # Draw line
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()

        # Draw arrows
        arrow_size = 2.0
        angle = math.atan2(y2 - y1, x2 - x1)

        # Arrow at end point
        ctx.save()
        ctx.translate(x2, y2)
        ctx.rotate(angle)
        ctx.move_to(0, 0)
        ctx.line_to(-arrow_size, -arrow_size / 2)
        ctx.line_to(-arrow_size, arrow_size / 2)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # Label
        ctx.save()
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Position label with offset
        label_x = mid_x + offset * math.cos(angle + math.pi / 2)
        label_y = mid_y + offset * math.sin(angle + math.pi / 2)

        ctx.set_font_size(3.0)
        extents = ctx.text_extents(label)
        ctx.move_to(label_x - extents.width / 2, label_y + extents.height / 2)

        # Background for label
        ctx.set_source_rgba(0.98, 0.98, 0.98, 0.9)
        ctx.rectangle(
            label_x - extents.width / 2 - 0.5,
            label_y - extents.height / 2 - 0.5,
            extents.width + 1,
            extents.height + 1,
        )
        ctx.fill()

        # Label text
        ctx.set_source_rgb(0.3, 0.3, 0.3)
        ctx.move_to(label_x - extents.width / 2, label_y + extents.height / 2)
        ctx.show_text(label)

        ctx.restore()

    # Input handlers
    def _on_scroll(self, controller, dx, dy):
        """Handle scroll events for zoom."""
        # Zoom in/out
        zoom_factor = 1.1
        if dy < 0:  # Scroll up = zoom in
            self.zoom *= zoom_factor
        else:  # Scroll down = zoom out
            self.zoom /= zoom_factor

        # Clamp zoom
        self.zoom = max(0.1, min(10.0, self.zoom))

        self.queue_draw()
        return True

    def _on_drag_begin(self, gesture, start_x, start_y):
        """Handle drag begin."""
        self.dragging = True
        self.drag_start_x = start_x
        self.drag_start_y = start_y

    def _on_drag_update(self, gesture, offset_x, offset_y):
        """Handle drag update for panning."""
        if self.dragging:
            # Update pan (scaled by zoom)
            self.pan_x += offset_x / self.zoom / 2
            self.pan_y += offset_y / self.zoom / 2
            self.queue_draw()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        """Handle drag end."""
        self.dragging = False
