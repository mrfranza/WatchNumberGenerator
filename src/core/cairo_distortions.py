"""Smooth distortions that work directly on Cairo rendering."""

import cairo
import math
import numpy as np


class CairoDistortions:
    """Apply smooth, subtle distortions to Cairo-rendered text."""

    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducibility."""
        self.seed = seed
        np.random.seed(seed)

    def apply_wave_distortion(
        self,
        ctx: cairo.Context,
        intensity: float,
        frequency: float = 2.0,
        direction: str = "horizontal"
    ):
        """
        Apply a smooth wave/sine distortion.

        This creates gentle curves in the text.

        Args:
            ctx: Cairo context
            intensity: Wave amplitude (0.0 - 5.0), in pixels
            frequency: Number of waves
            direction: "horizontal" or "vertical"
        """
        if intensity <= 0:
            return

        # This is a conceptual approach - Cairo doesn't support
        # direct path manipulation, so we'll implement this differently
        # For now, we can apply small rotations that vary with position
        pass

    def create_distorted_surface(
        self,
        source_surface: cairo.ImageSurface,
        edge_irregularity: float = 0.0,
        wave_amount: float = 0.0,
        bulge_amount: float = 0.0,
    ) -> cairo.ImageSurface:
        """
        Create a distorted version of a surface using pixel manipulation.

        This is a post-processing approach that distorts the rendered glyph.

        Args:
            source_surface: Source Cairo surface with rendered number
            edge_irregularity: Random edge noise (0.0 - 3.0)
            wave_amount: Sine wave distortion (0.0 - 5.0)
            bulge_amount: Radial bulge/pinch effect (0.0 - 3.0)

        Returns:
            Distorted surface
        """
        width = source_surface.get_width()
        height = source_surface.get_height()

        # Create output surface
        output = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        # Get pixel data
        source_data = np.ndarray(
            shape=(height, width, 4),
            dtype=np.uint8,
            buffer=source_surface.get_data()
        )

        output_data = np.ndarray(
            shape=(height, width, 4),
            dtype=np.uint8,
            buffer=output.get_data()
        )

        # Center of image
        cx = width / 2
        cy = height / 2

        # For each output pixel, find where it comes from in source
        for y in range(height):
            for x in range(width):
                # Start with identity mapping
                src_x = float(x)
                src_y = float(y)

                # Apply wave distortion
                if wave_amount > 0:
                    # Horizontal wave
                    wave_offset = math.sin(y / height * math.pi * 4) * wave_amount
                    src_x += wave_offset

                    # Vertical wave (perpendicular)
                    wave_offset_y = math.sin(x / width * math.pi * 3) * wave_amount * 0.5
                    src_y += wave_offset_y

                # Apply bulge/pinch
                if bulge_amount > 0:
                    dx = src_x - cx
                    dy = src_y - cy
                    dist = math.sqrt(dx*dx + dy*dy)

                    if dist > 0:
                        # Bulge formula (outward distortion)
                        max_dist = math.sqrt(cx*cx + cy*cy)
                        normalized_dist = dist / max_dist
                        bulge_factor = 1.0 + (bulge_amount * 0.1 * normalized_dist)

                        src_x = cx + dx * bulge_factor
                        src_y = cy + dy * bulge_factor

                # Apply edge irregularity (noise)
                if edge_irregularity > 0:
                    noise_x = (np.random.random() - 0.5) * edge_irregularity
                    noise_y = (np.random.random() - 0.5) * edge_irregularity
                    src_x += noise_x
                    src_y += noise_y

                # Sample from source (with bounds checking)
                src_x_int = int(round(src_x))
                src_y_int = int(round(src_y))

                if 0 <= src_x_int < width and 0 <= src_y_int < height:
                    output_data[y, x] = source_data[src_y_int, src_x_int]
                else:
                    # Transparent pixel
                    output_data[y, x] = [0, 0, 0, 0]

        output.mark_dirty()
        return output

    def apply_subtle_rotation_field(
        self,
        ctx: cairo.Context,
        center_x: float,
        center_y: float,
        max_rotation: float = 0.05
    ):
        """
        Apply a subtle rotation that varies with distance from center.

        Creates a gentle "twist" effect.

        Args:
            ctx: Cairo context
            center_x, center_y: Center point
            max_rotation: Maximum rotation in radians (keep small, like 0.05 = ~3 degrees)
        """
        # Get current position (this is tricky with Cairo)
        # We can't easily apply position-dependent transforms with Cairo
        # This would need to be done during path creation
        pass


def render_number_with_distortion(
    number: str,
    font_family: str,
    font_size: float,
    edge_irregularity: float = 0.0,
    wave_amount: float = 0.0,
    bulge_amount: float = 0.0,
    width: int = 500,
    height: int = 500
) -> cairo.ImageSurface:
    """
    Render a number with distortion effects applied.

    This is a helper function that demonstrates the workflow:
    1. Render clean to a surface
    2. Apply distortion to the surface
    3. Return distorted surface

    Args:
        number: Text to render
        font_family: Font name
        font_size: Font size
        edge_irregularity: Edge noise amount
        wave_amount: Wave distortion amount
        bulge_amount: Bulge effect amount
        width, height: Surface dimensions

    Returns:
        Distorted surface with rendered number
    """
    # Create surface and render clean text
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    # Clear
    ctx.set_source_rgba(0, 0, 0, 0)
    ctx.paint()

    # Render text centered
    ctx.set_source_rgb(0, 0, 0)
    ctx.select_font_face(font_family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(font_size)

    extents = ctx.text_extents(number)
    x = (width - extents.width) / 2 - extents.x_bearing
    y = (height - extents.height) / 2 - extents.y_bearing

    ctx.move_to(x, y)
    ctx.show_text(number)

    # Apply distortions if any
    if edge_irregularity > 0 or wave_amount > 0 or bulge_amount > 0:
        distorter = CairoDistortions()
        surface = distorter.create_distorted_surface(
            surface,
            edge_irregularity=edge_irregularity,
            wave_amount=wave_amount,
            bulge_amount=bulge_amount
        )

    return surface
