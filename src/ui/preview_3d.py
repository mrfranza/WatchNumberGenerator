"""3D preview widget for generated mesh."""

import gi
import math
import numpy as np

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk
import cairo


class Preview3DWidget(Gtk.DrawingArea):
    """Interactive 3D mesh viewer with rotation and zoom."""

    def __init__(self):
        super().__init__()

        # State
        self.has_mesh = False
        self.mesh_data = None

        # 3D view parameters
        self.rotation_x = -30.0  # Pitch (degrees)
        self.rotation_z = 45.0   # Yaw (degrees)
        self.zoom = 1.0
        self.auto_rotate = False

        # Debug visualization flags
        self.show_grid = True
        self.show_debug_boxes = True
        self.show_axes = True

        # Mouse interaction
        self.dragging = False
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0
        self.last_rotation_x = 0.0
        self.last_rotation_z = 0.0

        # Aggressive performance cache - cache entire rendered surface
        self._cached_surface = None
        self._cached_rotation_x = None
        self._cached_rotation_z = None
        self._cached_zoom = None
        self._cached_mesh_id = None
        self._cached_width = None
        self._cached_height = None
        self._cached_show_grid = None
        self._cached_show_debug = None

        # Redraw throttling
        self._redraw_timeout_id = None
        self._pending_redraw = False

        # Setup drawing function
        self.set_draw_func(self._on_draw)

        # Setup input handlers
        self._setup_input_handlers()

        # Set size
        self.set_size_request(400, 400)

    def _setup_input_handlers(self):
        """Setup mouse interaction."""
        # Drag for rotation
        drag_controller = Gtk.GestureDrag()
        drag_controller.connect("drag-begin", self._on_drag_begin)
        drag_controller.connect("drag-update", self._on_drag_update)
        drag_controller.connect("drag-end", self._on_drag_end)
        self.add_controller(drag_controller)

        # Scroll for zoom
        scroll_controller = Gtk.EventControllerScroll()
        scroll_controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_controller.connect("scroll", self._on_scroll)
        self.add_controller(scroll_controller)

    def set_mesh(self, mesh_data):
        """Set mesh data to display."""
        self.mesh_data = mesh_data
        self.has_mesh = True
        self.queue_draw()

    def clear(self):
        """Clear mesh preview."""
        self.has_mesh = False
        self.mesh_data = None
        self.queue_draw()

    def _on_draw(self, area, ctx: cairo.Context, width, height):
        """Draw the 3D preview with aggressive surface caching."""
        # Clear background
        ctx.set_source_rgb(0.15, 0.15, 0.15)
        ctx.paint()

        if not self.has_mesh:
            # Show placeholder text
            ctx.set_source_rgb(0.5, 0.5, 0.5)
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(16)

            text = "Click 'Generate 3D Mesh' to preview"
            extents = ctx.text_extents(text)
            x = (width - extents.width) / 2
            y = (height + extents.height) / 2

            ctx.move_to(x, y)
            ctx.show_text(text)
        else:
            # Use cached surface if nothing changed
            mesh_id = id(self.mesh_data.get("mesh")) if self.mesh_data else None

            cache_valid = (
                self._cached_surface is not None and
                self._cached_rotation_x == self.rotation_x and
                self._cached_rotation_z == self.rotation_z and
                self._cached_zoom == self.zoom and
                self._cached_mesh_id == mesh_id and
                self._cached_width == width and
                self._cached_height == height and
                self._cached_show_grid == self.show_grid and
                self._cached_show_debug == self.show_debug_boxes
            )

            if cache_valid:
                # Just blit the cached surface
                ctx.set_source_surface(self._cached_surface, 0, 0)
                ctx.paint()
            else:
                # Render to off-screen surface
                self._cached_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                cache_ctx = cairo.Context(self._cached_surface)

                # Clear cached surface background
                cache_ctx.set_source_rgb(0.15, 0.15, 0.15)
                cache_ctx.paint()

                # Render 3D content to cache
                self._render_3d_scene(cache_ctx, width, height)

                # Update cache parameters
                self._cached_rotation_x = self.rotation_x
                self._cached_rotation_z = self.rotation_z
                self._cached_zoom = self.zoom
                self._cached_mesh_id = mesh_id
                self._cached_width = width
                self._cached_height = height
                self._cached_show_grid = self.show_grid
                self._cached_show_debug = self.show_debug_boxes

                # Blit to screen
                ctx.set_source_surface(self._cached_surface, 0, 0)
                ctx.paint()

    def _render_3d_scene(self, ctx: cairo.Context, width, height):
        """Render the complete 3D scene with mesh, grid, and debug visuals."""
        cx = width / 2
        cy = height / 2

        if not self.mesh_data or "mesh" not in self.mesh_data:
            # Show message if no mesh
            ctx.set_source_rgb(0.5, 0.5, 0.5)
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_font_size(16)
            text = "No mesh data available"
            extents = ctx.text_extents(text)
            ctx.move_to(cx - extents.width/2, cy)
            ctx.show_text(text)
            return

        # Get mesh
        mesh = self.mesh_data["mesh"]
        vertices = mesh.vectors

        # Transform mesh
        transformed_triangles, view_size, R = self._transform_mesh(vertices, width, height)

        # Sort triangles by depth (painter's algorithm)
        triangles_with_depth = []
        for tri in transformed_triangles:
            avg_z = (tri[0][2] + tri[1][2] + tri[2][2]) / 3
            triangles_with_depth.append((avg_z, tri))

        triangles_with_depth.sort(key=lambda x: x[0])

        # Draw 3D grid first (behind everything)
        if self.show_grid:
            self._draw_3d_grid(ctx, width, height, view_size, R, cx, cy)

        # Draw axes
        if self.show_axes:
            self._draw_3d_axes(ctx, width, height, view_size, R, cx, cy)

        # Draw debug boxes for number sectors
        if self.show_debug_boxes and "numbers_data" in self.mesh_data:
            self._draw_debug_boxes(ctx, width, height, view_size, R, cx, cy)

        # Draw mesh triangles with two-sided lighting and wireframe
        camera_dir = np.array([0.0, 0.0, 1.0])  # Camera looking towards +Z

        for depth, tri in triangles_with_depth:
            # Calculate normal for lighting
            v1 = tri[1] - tri[0]
            v2 = tri[2] - tri[0]
            normal = np.cross(v1, v2)
            normal_len = np.linalg.norm(normal)
            if normal_len < 1e-6:
                continue  # Skip degenerate triangles

            normal = normal / normal_len

            # Project to 2D (orthographic projection)
            # Y coordinate stays as-is (Cairo already has Y inverted)
            p0 = (cx + tri[0][0] * view_size, cy - tri[0][1] * view_size)
            p1 = (cx + tri[1][0] * view_size, cy - tri[1][1] * view_size)
            p2 = (cx + tri[2][0] * view_size, cy - tri[2][1] * view_size)

            # Two-sided lighting (no backface culling, just use abs of dot product)
            light_dir = np.array([0.0, 0.3, 1.0])
            light_dir = light_dir / np.linalg.norm(light_dir)
            brightness = abs(np.dot(normal, light_dir))  # abs() for two-sided
            brightness = max(0.4, min(1.0, brightness * 0.8 + 0.2))  # Better range

            # Color based on lighting
            color = 0.75 * brightness
            ctx.set_source_rgb(color, color * 0.95, color * 0.85)

            # Fill triangle
            ctx.move_to(p0[0], p0[1])
            ctx.line_to(p1[0], p1[1])
            ctx.line_to(p2[0], p2[1])
            ctx.close_path()
            ctx.fill()

            # Draw wireframe edges
            ctx.set_source_rgba(0.2, 0.2, 0.25, 0.6)
            ctx.set_line_width(0.5)
            ctx.move_to(p0[0], p0[1])
            ctx.line_to(p1[0], p1[1])
            ctx.line_to(p2[0], p2[1])
            ctx.close_path()
            ctx.stroke()

        # Draw info overlay
        self._draw_info_overlay(ctx, width, height)

    def _transform_mesh(self, vertices, width, height):
        """Apply 3D rotation transformations to mesh vertices.

        Returns:
            tuple: (transformed_triangles, view_size, rotation_matrix)
        """
        # Convert to radians
        rx = math.radians(self.rotation_x)
        rz = math.radians(self.rotation_z)

        # Rotation matrices
        # Rotation around X axis (pitch)
        Rx = np.array([
            [1, 0, 0],
            [0, math.cos(rx), -math.sin(rx)],
            [0, math.sin(rx), math.cos(rx)]
        ])

        # Rotation around Z axis (yaw)
        Rz = np.array([
            [math.cos(rz), -math.sin(rz), 0],
            [math.sin(rz), math.cos(rz), 0],
            [0, 0, 1]
        ])

        # Combined rotation - apply X rotation first, then Z (standard order)
        R = Rx @ Rz

        # Get mesh center for centering
        all_points = vertices.reshape(-1, 3)
        center = np.mean(all_points, axis=0)

        # Get max extent for normalization
        extents = np.max(all_points, axis=0) - np.min(all_points, axis=0)
        max_extent = max(extents)

        # Calculate scale to fit in view
        view_size = min(width, height) * 0.7 * self.zoom

        # Transform each triangle
        transformed = []
        for triangle in vertices:
            # Center and normalize
            tri_centered = triangle - center
            tri_normalized = tri_centered / max_extent

            # Apply rotation
            tri_rotated = tri_normalized @ R.T

            transformed.append(tri_rotated)

        return np.array(transformed), view_size, R

    def _draw_3d_grid(self, ctx: cairo.Context, width, height, view_size, R, cx, cy):
        """Draw simplified 3D grid on XY plane."""
        grid_size = 1.0  # Normalized size
        grid_step = 0.2  # Larger spacing for fewer lines

        ctx.set_source_rgba(0.3, 0.3, 0.4, 0.4)
        ctx.set_line_width(0.5)

        # Draw fewer grid lines for performance
        # Grid lines parallel to X axis
        y = -grid_size
        while y <= grid_size:
            p1 = np.array([-grid_size, y, 0.0]) @ R.T
            p2 = np.array([grid_size, y, 0.0]) @ R.T

            x1 = cx + p1[0] * view_size
            y1 = cy - p1[1] * view_size
            x2 = cx + p2[0] * view_size
            y2 = cy - p2[1] * view_size

            ctx.move_to(x1, y1)
            ctx.line_to(x2, y2)
            ctx.stroke()

            y += grid_step

        # Grid lines parallel to Y axis
        x = -grid_size
        while x <= grid_size:
            p1 = np.array([x, -grid_size, 0.0]) @ R.T
            p2 = np.array([x, grid_size, 0.0]) @ R.T

            x1 = cx + p1[0] * view_size
            y1 = cy - p1[1] * view_size
            x2 = cx + p2[0] * view_size
            y2 = cy - p2[1] * view_size

            ctx.move_to(x1, y1)
            ctx.line_to(x2, y2)
            ctx.stroke()

            x += grid_step

    def _draw_3d_axes(self, ctx: cairo.Context, width, height, view_size, R, cx, cy):
        """Draw 3D coordinate axes."""
        axis_length = 0.8

        # X axis (red)
        p0 = np.array([0.0, 0.0, 0.0]) @ R.T
        p1 = np.array([axis_length, 0.0, 0.0]) @ R.T

        ctx.set_source_rgba(1.0, 0.3, 0.3, 0.8)
        ctx.set_line_width(2.0)
        ctx.move_to(cx + p0[0] * view_size, cy - p0[1] * view_size)
        ctx.line_to(cx + p1[0] * view_size, cy - p1[1] * view_size)
        ctx.stroke()

        # Y axis (green)
        p1 = np.array([0.0, axis_length, 0.0]) @ R.T
        ctx.set_source_rgba(0.3, 1.0, 0.3, 0.8)
        ctx.move_to(cx + p0[0] * view_size, cy - p0[1] * view_size)
        ctx.line_to(cx + p1[0] * view_size, cy - p1[1] * view_size)
        ctx.stroke()

        # Z axis (blue)
        p1 = np.array([0.0, 0.0, axis_length]) @ R.T
        ctx.set_source_rgba(0.3, 0.3, 1.0, 0.8)
        ctx.move_to(cx + p0[0] * view_size, cy - p0[1] * view_size)
        ctx.line_to(cx + p1[0] * view_size, cy - p1[1] * view_size)
        ctx.stroke()

    def _draw_debug_boxes(self, ctx: cairo.Context, width, height, view_size, R, cx, cy):
        """Draw debug visualization boxes for number sectors."""
        if "numbers_data" not in self.mesh_data:
            return

        numbers_data = self.mesh_data["numbers_data"]

        # Get mesh bounds for normalization
        mesh = self.mesh_data["mesh"]
        all_points = mesh.vectors.reshape(-1, 3)
        center = np.mean(all_points, axis=0)
        extents = np.max(all_points, axis=0) - np.min(all_points, axis=0)
        max_extent = max(extents)

        ctx.set_source_rgba(0.0, 1.0, 1.0, 0.3)
        ctx.set_line_width(1.0)

        for num_data in numbers_data:
            # Get sector box boundaries
            if "sector_box" in num_data:
                box = num_data["sector_box"]

                # Normalize coordinates to match mesh
                corners_3d = []
                for corner in box["corners"]:
                    x = (corner[0] - center[0]) / max_extent
                    y = (corner[1] - center[1]) / max_extent
                    z = 0.0
                    corners_3d.append(np.array([x, y, z]))

                # Transform and project corners
                transformed_corners = []
                for corner in corners_3d:
                    rotated = corner @ R.T
                    screen_x = cx + rotated[0] * view_size
                    screen_y = cy - rotated[1] * view_size
                    transformed_corners.append((screen_x, screen_y))

                # Draw box outline
                ctx.move_to(transformed_corners[0][0], transformed_corners[0][1])
                for i in range(1, len(transformed_corners)):
                    ctx.line_to(transformed_corners[i][0], transformed_corners[i][1])
                ctx.close_path()
                ctx.stroke()

            # Draw center marker
            if "center_x" in num_data and "center_y" in num_data:
                x = (num_data["center_x"] - center[0]) / max_extent
                y = (num_data["center_y"] - center[1]) / max_extent
                z = 0.0

                center_pt = np.array([x, y, z]) @ R.T
                screen_x = cx + center_pt[0] * view_size
                screen_y = cy - center_pt[1] * view_size

                ctx.set_source_rgba(1.0, 0.0, 1.0, 0.6)
                ctx.arc(screen_x, screen_y, 3, 0, 2 * math.pi)
                ctx.fill()

    def _draw_info_overlay(self, ctx: cairo.Context, width, height):
        """Draw info text overlay."""
        # Draw semi-transparent background for text
        ctx.set_source_rgba(0.1, 0.1, 0.1, 0.7)
        ctx.rectangle(10, 10, 250, 100)
        ctx.fill()

        # Draw text
        ctx.set_source_rgb(0.9, 0.9, 0.9)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(11)

        y = 30
        if self.mesh_data:
            if "timestamp" in self.mesh_data:
                ctx.move_to(20, y)
                ctx.show_text(f"Generated: {self.mesh_data['timestamp']}")
                y += 18

            if "numbers_count" in self.mesh_data:
                ctx.move_to(20, y)
                ctx.show_text(f"Numbers: {self.mesh_data['numbers_count']}")
                y += 18

            if "triangles" in self.mesh_data:
                ctx.move_to(20, y)
                ctx.show_text(f"Triangles: {self.mesh_data['triangles']:,}")
                y += 18

            if "dimensions" in self.mesh_data:
                dims = self.mesh_data["dimensions"]
                ctx.move_to(20, y)
                ctx.show_text(f"Size: {dims[0]:.1f}×{dims[1]:.1f}×{dims[2]:.1f}mm")

        # Draw controls hint
        ctx.set_font_size(10)
        ctx.set_source_rgba(0.7, 0.7, 0.7, 0.8)
        ctx.move_to(20, height - 20)
        ctx.show_text("Drag to rotate • Scroll to zoom")

    def _on_drag_begin(self, gesture, start_x, start_y):
        """Handle drag begin for rotation."""
        self.dragging = True
        self.drag_start_x = start_x
        self.drag_start_y = start_y
        self.last_rotation_x = self.rotation_x
        self.last_rotation_z = self.rotation_z

    def _on_drag_update(self, gesture, offset_x, offset_y):
        """Handle drag update for rotation."""
        if self.dragging:
            # Update rotation based on drag - natural trackball behavior
            self.rotation_z = self.last_rotation_z + offset_x * 0.4
            self.rotation_x = self.last_rotation_x - offset_y * 0.4

            # Clamp X rotation
            self.rotation_x = max(-90, min(90, self.rotation_x))

            self.queue_draw()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        """Handle drag end."""
        self.dragging = False

    def _on_scroll(self, controller, dx, dy):
        """Handle scroll for zoom."""
        # Zoom in/out
        zoom_factor = 1.1
        if dy < 0:  # Scroll up
            self.zoom *= zoom_factor
        else:  # Scroll down
            self.zoom /= zoom_factor

        # Clamp zoom
        self.zoom = max(0.1, min(5.0, self.zoom))

        self.queue_draw()
        return True
