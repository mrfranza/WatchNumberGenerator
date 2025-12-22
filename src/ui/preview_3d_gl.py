"""OpenGL-based 3D mesh preview widget for high performance rendering."""

import math
import numpy as np
from gi.repository import Gtk, Gdk
from OpenGL.GL import *
from OpenGL.GLU import *


class Preview3DGL(Gtk.GLArea):
    """OpenGL-accelerated 3D mesh preview widget."""

    def __init__(self):
        super().__init__()

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

        # OpenGL data
        self.vertex_buffer = None
        self.normal_buffer = None
        self.vertex_count = 0

        # Connect signals
        self.connect("realize", self._on_realize)
        self.connect("render", self._on_render)
        self.connect("unrealize", self._on_unrealize)

        # Setup input handlers
        self._setup_input_handlers()

        # Set size
        self.set_size_request(400, 400)

    def _setup_input_handlers(self):
        """Setup mouse and scroll input handlers."""
        # Drag gesture for rotation
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        # Scroll for zoom
        scroll = Gtk.EventControllerScroll()
        scroll.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self.add_controller(scroll)

    def set_mesh(self, mesh_data: dict):
        """Update the mesh to display."""
        self.has_mesh = True
        self.mesh_data = mesh_data

        # Extract mesh data
        if mesh_data and "mesh" in mesh_data:
            mesh = mesh_data["mesh"]
            vertices = mesh.vectors  # Shape: (n_triangles, 3, 3)

            # Flatten to vertex array
            self.vertex_buffer = vertices.reshape(-1, 3).astype(np.float32)
            self.vertex_count = len(self.vertex_buffer)

            # Calculate normals per triangle
            normals = []
            for triangle in vertices:
                v1 = triangle[1] - triangle[0]
                v2 = triangle[2] - triangle[0]
                normal = np.cross(v1, v2)
                normal_len = np.linalg.norm(normal)
                if normal_len > 1e-6:
                    normal = normal / normal_len
                else:
                    normal = np.array([0.0, 0.0, 1.0])

                # Repeat normal for each vertex of the triangle
                normals.extend([normal, normal, normal])

            self.normal_buffer = np.array(normals, dtype=np.float32)

        self.queue_draw()

    def clear(self):
        """Clear mesh preview."""
        self.has_mesh = False
        self.mesh_data = None
        self.vertex_buffer = None
        self.normal_buffer = None
        self.vertex_count = 0
        self.queue_draw()

    def _on_realize(self, area):
        """Called when GLArea is realized - setup OpenGL context."""
        self.make_current()

        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        # Enable lighting
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        # Setup light
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.3, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])

        # Enable two-sided lighting
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        # Material properties
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.7, 0.68, 0.65, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 20.0)

        # Background color
        glClearColor(0.15, 0.15, 0.15, 1.0)

    def _on_render(self, area, context):
        """Render the 3D scene using OpenGL."""
        # Clear buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Setup viewport and projection
        width = self.get_width()
        height = self.get_height()

        glViewport(0, 0, width, height)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect = width / height if height > 0 else 1.0
        fov = 45.0
        gluPerspective(fov, aspect, 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # Camera position
        camera_distance = 2.5 / self.zoom
        gluLookAt(0, 0, camera_distance,  # Eye position
                  0, 0, 0,                # Look at center
                  0, 1, 0)                # Up vector

        # Apply rotations
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_z, 0, 0, 1)

        if not self.has_mesh:
            # No mesh - just clear screen (already done)
            return True

        # Draw grid if enabled
        if self.show_grid:
            self._draw_grid()

        # Draw axes if enabled
        if self.show_axes:
            self._draw_axes()

        # Draw mesh
        if self.vertex_buffer is not None and self.vertex_count > 0:
            self._draw_mesh()

        # Draw debug boxes if enabled
        if self.show_debug_boxes and self.mesh_data and "numbers_data" in self.mesh_data:
            self._draw_debug_boxes()

        glFlush()
        return True

    def _draw_mesh(self):
        """Draw the mesh using vertex arrays."""
        # Center and normalize mesh
        vertices = self.vertex_buffer
        center = np.mean(vertices, axis=0)
        centered = vertices - center

        extents = np.max(centered, axis=0) - np.min(centered, axis=0)
        max_extent = max(extents)
        if max_extent > 0:
            normalized = centered / max_extent
        else:
            normalized = centered

        # Enable vertex and normal arrays
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glVertexPointer(3, GL_FLOAT, 0, normalized)
        glNormalPointer(GL_FLOAT, 0, self.normal_buffer)

        # Draw triangles
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)

        # Disable arrays
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)

        # Draw wireframe on top
        glDisable(GL_LIGHTING)
        glColor3f(0.2, 0.2, 0.25)
        glLineWidth(0.5)

        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, normalized)
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
        glDisableClientState(GL_VERTEX_ARRAY)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glEnable(GL_LIGHTING)

    def _draw_grid(self):
        """Draw 3D grid on XY plane."""
        glDisable(GL_LIGHTING)
        glColor4f(0.3, 0.3, 0.4, 0.4)
        glLineWidth(0.5)

        grid_size = 1.0
        grid_step = 0.2

        glBegin(GL_LINES)

        # Lines parallel to X axis
        y = -grid_size
        while y <= grid_size:
            glVertex3f(-grid_size, y, 0.0)
            glVertex3f(grid_size, y, 0.0)
            y += grid_step

        # Lines parallel to Y axis
        x = -grid_size
        while x <= grid_size:
            glVertex3f(x, -grid_size, 0.0)
            glVertex3f(x, grid_size, 0.0)
            x += grid_step

        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_axes(self):
        """Draw 3D coordinate axes."""
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)

        axis_length = 0.8

        glBegin(GL_LINES)

        # X axis (red)
        glColor3f(1.0, 0.3, 0.3)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(axis_length, 0.0, 0.0)

        # Y axis (green)
        glColor3f(0.3, 1.0, 0.3)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, axis_length, 0.0)

        # Z axis (blue)
        glColor3f(0.3, 0.3, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, axis_length)

        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_debug_boxes(self):
        """Draw debug visualization boxes for number sectors."""
        if "numbers_data" not in self.mesh_data:
            return

        numbers_data = self.mesh_data["numbers_data"]

        # Get mesh bounds for normalization
        vertices = self.vertex_buffer
        center = np.mean(vertices, axis=0)
        centered = vertices - center
        extents = np.max(centered, axis=0) - np.min(centered, axis=0)
        max_extent = max(extents)

        glDisable(GL_LIGHTING)
        glColor4f(0.0, 1.0, 1.0, 0.3)
        glLineWidth(1.0)

        for num_data in numbers_data:
            # Get sector box boundaries
            if "sector_box" in num_data:
                box = num_data["sector_box"]

                # Normalize coordinates
                glBegin(GL_LINE_LOOP)
                for corner in box["corners"]:
                    x = (corner[0] - center[0]) / max_extent if max_extent > 0 else 0
                    y = (corner[1] - center[1]) / max_extent if max_extent > 0 else 0
                    glVertex3f(x, y, 0.0)
                glEnd()

            # Draw center marker
            if "center_x" in num_data and "center_y" in num_data:
                x = (num_data["center_x"] - center[0]) / max_extent if max_extent > 0 else 0
                y = (num_data["center_y"] - center[1]) / max_extent if max_extent > 0 else 0

                glColor3f(1.0, 0.0, 1.0)
                glPointSize(5.0)
                glBegin(GL_POINTS)
                glVertex3f(x, y, 0.0)
                glEnd()

        glEnable(GL_LIGHTING)

    def _on_unrealize(self, area):
        """Called when GLArea is unrealized - cleanup OpenGL resources."""
        self.make_current()
        # Cleanup any GL resources here if needed

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
            # Update rotation based on drag
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
        zoom_factor = 1.1

        if dy < 0:  # Scroll up
            self.zoom *= zoom_factor
        else:  # Scroll down
            self.zoom /= zoom_factor

        # Clamp zoom
        self.zoom = max(0.1, min(5.0, self.zoom))

        self.queue_draw()
        return True
