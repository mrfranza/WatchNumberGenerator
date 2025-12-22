"""3D mesh generation from text paths."""

import numpy as np
from stl import mesh
from typing import List, Tuple, Optional
import math
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import trimesh


class MeshGenerator:
    """Generates 3D STL meshes from 2D text contours."""

    def __init__(self):
        pass

    def create_text_mesh(
        self,
        contours: List[List[Tuple[float, float]]],
        extrusion_depth: float,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> mesh.Mesh:
        """
        Create a 3D mesh from 2D text contours by manual extrusion.

        Args:
            contours: List of contours (polygons) representing the text WITH DISTORTIONS
            extrusion_depth: Depth to extrude the text (mm)
            center_x: X offset for centering (not used, contours are already positioned)
            center_y: Y offset for centering (not used, contours are already positioned)

        Returns:
            numpy-stl Mesh object
        """
        if not contours or extrusion_depth <= 0:
            return self._create_empty_mesh()

        try:
            # Manually extrude contours to preserve distortions
            all_faces = []

            if not contours:
                return self._create_empty_mesh()

            # Group contours by winding order: outer (CW) vs holes (CCW)
            # For multi-character text like "XII", each letter is a separate group
            contour_groups = self._group_contours_with_holes(contours)

            # Process each group (character/glyph) separately
            all_bottom_vertices = []
            all_top_vertices = []
            global_offset = 0

            for group_contours in contour_groups:
                # Flatten contours in this group
                group_vertices = []
                group_ring_indices = []
                vertex_offset = 0

                for contour in group_contours:
                    if len(contour) < 3:
                        continue
                    group_vertices.extend(contour)
                    vertex_offset += len(contour)
                    group_ring_indices.append(vertex_offset)

                if not group_vertices:
                    continue

                group_vertices_array = np.array(group_vertices, dtype=np.float64)
                group_ring_indices_array = np.array(group_ring_indices, dtype=np.uint32)

                # Create 3D vertices for this group
                n_points = len(group_vertices)
                bottom_verts = np.column_stack([
                    group_vertices_array[:, 0],
                    group_vertices_array[:, 1],
                    np.zeros(n_points)
                ])

                top_verts = np.column_stack([
                    group_vertices_array[:, 0],
                    group_vertices_array[:, 1],
                    np.full(n_points, extrusion_depth)
                ])

                all_bottom_vertices.append(bottom_verts)
                all_top_vertices.append(top_verts)

                # Create side walls for each contour in this group
                offset = 0
                for contour in group_contours:
                    n_points_contour = len(contour)
                    if n_points_contour < 3:
                        continue

                    for i in range(n_points_contour):
                        i_next = (i + 1) % n_points_contour
                        i_global = global_offset + offset + i
                        i_next_global = global_offset + offset + i_next

                        # For side walls, use concatenated vertex arrays
                        # We'll build them after collecting all vertices
                        pass  # Will create walls after collecting all vertices

                    offset += n_points_contour

                # Triangulate caps for this group
                try:
                    indices_2d = self._triangulate_polygon_with_holes(
                        group_vertices_array,
                        group_ring_indices_array
                    )

                    # Create top/bottom caps using group-local indices offset by global offset
                    for tri_indices in indices_2d:
                        # Adjust indices for global vertex array
                        idx0 = tri_indices[0] + global_offset
                        idx1 = tri_indices[1] + global_offset
                        idx2 = tri_indices[2] + global_offset

                        # Bottom cap (reversed winding)
                        all_faces.append([
                            bottom_verts[tri_indices[2]],
                            bottom_verts[tri_indices[1]],
                            bottom_verts[tri_indices[0]]
                        ])

                        # Top cap
                        all_faces.append([
                            top_verts[tri_indices[0]],
                            top_verts[tri_indices[1]],
                            top_verts[tri_indices[2]]
                        ])
                except Exception as e:
                    print(f"Warning: Could not triangulate group: {e}")

                global_offset += len(group_vertices)

            # Now create side walls using the collected vertices
            # Concatenate all vertex arrays
            if all_bottom_vertices:
                all_bottom = np.vstack(all_bottom_vertices)
                all_top = np.vstack(all_top_vertices)

                # Create side walls for each contour
                offset = 0
                for contour in contours:
                    n_points = len(contour)
                    if n_points < 3:
                        continue

                    for i in range(n_points):
                        i_next = (i + 1) % n_points
                        i_global = offset + i
                        i_next_global = offset + i_next

                        # Side wall triangles
                        all_faces.append([
                            all_bottom[i_global],
                            all_bottom[i_next_global],
                            all_top[i_global]
                        ])

                        all_faces.append([
                            all_bottom[i_next_global],
                            all_top[i_next_global],
                            all_top[i_global]
                        ])

                    offset += n_points


            if not all_faces:
                return self._create_empty_mesh()

            # Convert to numpy-stl mesh
            num_faces = len(all_faces)
            stl_mesh = mesh.Mesh(np.zeros(num_faces, dtype=mesh.Mesh.dtype))

            for i, face in enumerate(all_faces):
                for j in range(3):
                    stl_mesh.vectors[i][j] = face[j]

            return stl_mesh

        except Exception as e:
            print(f"Error creating mesh: {e}")
            import traceback
            traceback.print_exc()
            return self._create_empty_mesh()

    def _group_contours_with_holes(self, contours: List[List[Tuple[float, float]]]) -> List[List[List[Tuple[float, float]]]]:
        """
        Group contours into separate polygons with their holes.

        For multi-character text like "XII", each character is a separate polygon.
        Within each polygon, the first contour is the outer boundary (CW winding),
        and subsequent contours are holes (CCW winding).

        Args:
            contours: List of all contours from the text path

        Returns:
            List of groups, where each group is [outer_contour, hole1, hole2, ...]
        """
        if not contours:
            return []

        # Calculate signed area to determine winding order
        def signed_area(contour):
            """Calculate signed area using shoelace formula."""
            area = 0.0
            n = len(contour)
            for i in range(n):
                j = (i + 1) % n
                area += contour[i][0] * contour[j][1]
                area -= contour[j][0] * contour[i][1]
            return area / 2.0

        # Separate outer contours (positive area) from holes (negative area)
        outer_contours = []
        hole_contours = []

        for contour in contours:
            if len(contour) < 3:
                continue
            area = signed_area(contour)
            if area > 0:  # Counter-clockwise = outer boundary in Cairo
                outer_contours.append(contour)
            else:  # Clockwise = hole
                hole_contours.append(contour)

        # If no outer contours, treat all as outer (shouldn't happen with valid text)
        if not outer_contours and hole_contours:
            return [[hole] for hole in hole_contours]

        # Group each outer contour with its holes
        # For now, simple approach: assign holes to nearest outer contour
        groups = []

        for outer in outer_contours:
            group = [outer]

            # Find holes that are inside this outer contour
            # Simple heuristic: check if hole's first point is inside outer
            for hole in hole_contours:
                if len(hole) > 0:
                    # Check if hole is inside outer using point-in-polygon test
                    if self._point_in_contour(hole[0], outer):
                        group.append(hole)

            groups.append(group)

        # If we have no groups but have contours, treat all contours as one group
        if not groups and contours:
            groups = [contours]

        return groups

    def _point_in_contour(self, point: Tuple[float, float], contour: List[Tuple[float, float]]) -> bool:
        """
        Check if a point is inside a contour using ray casting algorithm.
        """
        x, y = point
        n = len(contour)
        inside = False

        p1x, p1y = contour[0]
        for i in range(1, n + 1):
            p2x, p2y = contour[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _triangulate_polygon_with_holes(self, points_2d, ring_end_indices):
        """
        Triangulate a 2D polygon with holes using mapbox-earcut.

        Args:
            points_2d: (N, 2) numpy array of ALL vertices (outer + holes)
            ring_end_indices: uint32 array indicating where each ring ends
                             [end_of_ring1, end_of_ring2, ...]
                             First ring is outer boundary, rest are holes

        Returns:
            Array of triangle indices shaped (-1, 3)
        """
        try:
            import mapbox_earcut as earcut
            # Triangulate - earcut returns flat array of indices
            triangle_indices = earcut.triangulate_float64(points_2d, ring_end_indices)
            # Reshape to groups of 3 indices
            return triangle_indices.reshape(-1, 3)
        except Exception as e:
            print(f"Triangulation error: {e}")
            raise

    def _extrude_polygon(
        self, polygon: Polygon, depth: float, offset_x: float = 0.0, offset_y: float = 0.0
    ) -> Optional[trimesh.Trimesh]:
        """
        Extrude a Shapely polygon to create a 3D mesh.

        Args:
            polygon: 2D polygon to extrude
            depth: Extrusion depth
            offset_x: X offset
            offset_y: Y offset

        Returns:
            Trimesh object or None if failed
        """
        try:
            # Get exterior coordinates
            coords = np.array(polygon.exterior.coords)

            # Offset coordinates
            coords[:, 0] += offset_x
            coords[:, 1] += offset_y

            # Create path for extrusion
            path = trimesh.path.Path2D(entities=[trimesh.path.entities.Line(np.arange(len(coords)))],
                                       vertices=coords)

            # Extrude
            extruded = trimesh.creation.extrude_polygon(polygon, depth)

            # Translate to center
            extruded.apply_translation([offset_x, offset_y, 0])

            return extruded

        except Exception as e:
            print(f"Error extruding polygon: {e}")
            return None

    def _trimesh_to_numpy_stl(self, tmesh: trimesh.Trimesh) -> mesh.Mesh:
        """
        Convert trimesh to numpy-stl mesh.

        Args:
            tmesh: Trimesh object

        Returns:
            numpy-stl Mesh object
        """
        # Create numpy-stl mesh from vertices and faces
        num_faces = len(tmesh.faces)
        stl_mesh = mesh.Mesh(np.zeros(num_faces, dtype=mesh.Mesh.dtype))

        for i, face in enumerate(tmesh.faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = tmesh.vertices[face[j]]

        return stl_mesh

    def _create_empty_mesh(self) -> mesh.Mesh:
        """Create an empty mesh (single degenerate triangle)."""
        return mesh.Mesh(np.zeros(1, dtype=mesh.Mesh.dtype))

    def create_numbers_mesh(
        self,
        numbers_data: List[dict],
        extrusion_depth: float,
    ) -> mesh.Mesh:
        """
        Create a combined mesh for multiple numbers.

        Args:
            numbers_data: List of dicts with keys: contours, center_x, center_y
            extrusion_depth: Depth to extrude

        Returns:
            Combined numpy-stl Mesh object
        """
        meshes = []

        for data in numbers_data:
            m = self.create_text_mesh(
                data["contours"],
                extrusion_depth,
                data.get("center_x", 0.0),
                data.get("center_y", 0.0),
            )
            meshes.append(m)

        if not meshes:
            return self._create_empty_mesh()

        # Combine all meshes
        combined = mesh.Mesh(np.concatenate([m.data for m in meshes]))
        return combined

    def save_mesh(self, mesh_obj: mesh.Mesh, filename: str):
        """
        Save mesh to STL file.

        Args:
            mesh_obj: numpy-stl Mesh object
            filename: Output filename
        """
        mesh_obj.save(filename)

    def get_mesh_bounds(self, mesh_obj: mesh.Mesh) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get bounding box of mesh.

        Args:
            mesh_obj: numpy-stl Mesh object

        Returns:
            (min_bounds, max_bounds) as numpy arrays
        """
        min_bounds = mesh_obj.min_
        max_bounds = mesh_obj.max_
        return min_bounds, max_bounds

    def get_mesh_dimensions(self, mesh_obj: mesh.Mesh) -> Tuple[float, float, float]:
        """
        Get dimensions of mesh.

        Args:
            mesh_obj: numpy-stl Mesh object

        Returns:
            (width, height, depth) in mm
        """
        min_bounds, max_bounds = self.get_mesh_bounds(mesh_obj)
        dimensions = max_bounds - min_bounds
        return tuple(dimensions)
