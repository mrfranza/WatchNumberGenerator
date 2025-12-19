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
        Create a 3D mesh from 2D text contours.

        Args:
            contours: List of contours (polygons) representing the text
            extrusion_depth: Depth to extrude the text (mm)
            center_x: X offset for centering
            center_y: Y offset for centering

        Returns:
            numpy-stl Mesh object
        """
        if not contours or extrusion_depth <= 0:
            return self._create_empty_mesh()

        # Convert contours to Shapely polygons
        # First contour is usually the outer boundary, others might be holes
        try:
            if len(contours) == 1:
                polygon = Polygon(contours[0])
            else:
                # Try to determine which are outer boundaries and which are holes
                # For simplicity, use union of all contours
                polygons = []
                for contour in contours:
                    if len(contour) >= 3:
                        try:
                            poly = Polygon(contour)
                            if poly.is_valid:
                                polygons.append(poly)
                        except:
                            continue

                if not polygons:
                    return self._create_empty_mesh()

                # Union all polygons
                polygon = unary_union(polygons)

            # Use trimesh to create extruded mesh
            if isinstance(polygon, MultiPolygon):
                # Handle multiple separate polygons
                meshes = []
                for poly in polygon.geoms:
                    m = self._extrude_polygon(poly, extrusion_depth, center_x, center_y)
                    if m is not None:
                        meshes.append(m)

                if not meshes:
                    return self._create_empty_mesh()

                # Combine meshes
                combined = trimesh.util.concatenate(meshes)
                return self._trimesh_to_numpy_stl(combined)

            else:
                # Single polygon
                tmesh = self._extrude_polygon(polygon, extrusion_depth, center_x, center_y)
                if tmesh is None:
                    return self._create_empty_mesh()
                return self._trimesh_to_numpy_stl(tmesh)

        except Exception as e:
            print(f"Error creating mesh: {e}")
            return self._create_empty_mesh()

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
