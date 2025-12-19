"""Distortion filters for adding irregularities to number meshes."""

import numpy as np
from stl import mesh
from typing import Tuple
import random


class DistortionFilters:
    """Apply various distortion effects to meshes."""

    def __init__(self, seed: int = 42):
        """
        Initialize distortion filters.

        Args:
            seed: Random seed for reproducible results
        """
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def apply_edge_irregularity(
        self, mesh_obj: mesh.Mesh, intensity: float
    ) -> mesh.Mesh:
        """
        Add random irregularity to mesh edges.

        Args:
            mesh_obj: Input mesh
            intensity: Irregularity intensity (0.0 - 5.0)

        Returns:
            Modified mesh
        """
        if intensity <= 0:
            return mesh_obj

        # Create a copy to avoid modifying original
        modified_mesh = mesh.Mesh(mesh_obj.data.copy())

        # Get all vertices
        vertices = modified_mesh.vectors.reshape(-1, 3)

        # Add random displacement to each vertex
        # Scale based on intensity
        displacement = np.random.normal(0, intensity * 0.1, vertices.shape)

        # Apply displacement
        vertices += displacement

        # Reshape back
        modified_mesh.vectors = vertices.reshape(-1, 3, 3)

        return modified_mesh

    def apply_surface_roughness(
        self, mesh_obj: mesh.Mesh, intensity: float
    ) -> mesh.Mesh:
        """
        Add surface roughness using Perlin-like noise.

        Args:
            mesh_obj: Input mesh
            intensity: Roughness intensity (0.0 - 5.0)

        Returns:
            Modified mesh
        """
        if intensity <= 0:
            return mesh_obj

        # Create a copy
        modified_mesh = mesh.Mesh(mesh_obj.data.copy())

        # Get vertices
        vertices = modified_mesh.vectors.reshape(-1, 3)

        # Calculate normals for each face
        normals = modified_mesh.normals

        # Repeat normals for each vertex in face
        vertex_normals = np.repeat(normals, 3, axis=0)

        # Generate noise-based displacement along normals
        # Use position-based noise for more coherent roughness
        noise = self._generate_noise(vertices, frequency=2.0)

        # Scale by intensity
        displacement_amount = noise * intensity * 0.05

        # Displace along normals
        displacement = vertex_normals * displacement_amount[:, np.newaxis]
        vertices += displacement

        # Reshape back
        modified_mesh.vectors = vertices.reshape(-1, 3, 3)

        # Recalculate normals
        modified_mesh.update_normals()

        return modified_mesh

    def apply_perspective_stretch(
        self, mesh_obj: mesh.Mesh, intensity: float
    ) -> mesh.Mesh:
        """
        Apply radial perspective deformation.

        Args:
            mesh_obj: Input mesh
            intensity: Stretch intensity (0.0 - 3.0)

        Returns:
            Modified mesh
        """
        if intensity <= 0:
            return mesh_obj

        # Create a copy
        modified_mesh = mesh.Mesh(mesh_obj.data.copy())

        # Get vertices
        vertices = modified_mesh.vectors.reshape(-1, 3)

        # Calculate center of mesh
        center = vertices.mean(axis=0)

        # Calculate radial distance from center (XY plane)
        dx = vertices[:, 0] - center[0]
        dy = vertices[:, 1] - center[1]
        radial_dist = np.sqrt(dx**2 + dy**2)

        # Apply radial stretch (exponential)
        stretch_factor = 1.0 + (intensity * 0.1 * radial_dist / (radial_dist.max() + 1e-6))

        # Apply stretch in XY plane
        vertices[:, 0] = center[0] + dx * stretch_factor
        vertices[:, 1] = center[1] + dy * stretch_factor

        # Reshape back
        modified_mesh.vectors = vertices.reshape(-1, 3, 3)

        return modified_mesh

    def apply_erosion(self, mesh_obj: mesh.Mesh, intensity: float) -> mesh.Mesh:
        """
        Apply erosion effect for vintage/worn look.

        Args:
            mesh_obj: Input mesh
            intensity: Erosion intensity (0.0 - 5.0)

        Returns:
            Modified mesh
        """
        if intensity <= 0:
            return mesh_obj

        # Create a copy
        modified_mesh = mesh.Mesh(mesh_obj.data.copy())

        # Get vertices
        vertices = modified_mesh.vectors.reshape(-1, 3)

        # Generate wear pattern based on position
        # Edges and high points should erode more
        center = vertices.mean(axis=0)

        # Distance from center
        dx = vertices[:, 0] - center[0]
        dy = vertices[:, 1] - center[1]
        dz = vertices[:, 2] - center[2]
        dist = np.sqrt(dx**2 + dy**2 + dz**2)

        # Normalize distance
        dist_norm = dist / (dist.max() + 1e-6)

        # Generate erosion pattern
        # More erosion on edges (higher distance from center)
        erosion_amount = dist_norm * intensity * 0.1

        # Add some noise for irregularity
        noise = np.random.normal(0, intensity * 0.05, len(vertices))
        erosion_amount += noise

        # Apply erosion by scaling towards center
        scale_factor = 1.0 - erosion_amount

        vertices[:, 0] = center[0] + dx * scale_factor
        vertices[:, 1] = center[1] + dy * scale_factor
        vertices[:, 2] = center[2] + dz * scale_factor

        # Reshape back
        modified_mesh.vectors = vertices.reshape(-1, 3, 3)

        return modified_mesh

    def apply_all_filters(
        self,
        mesh_obj: mesh.Mesh,
        edge_irregularity: float = 0.0,
        surface_roughness: float = 0.0,
        perspective_stretch: float = 0.0,
        erosion: float = 0.0,
    ) -> mesh.Mesh:
        """
        Apply all distortion filters in sequence.

        Args:
            mesh_obj: Input mesh
            edge_irregularity: Edge irregularity intensity (0.0 - 5.0)
            surface_roughness: Surface roughness intensity (0.0 - 5.0)
            perspective_stretch: Perspective stretch intensity (0.0 - 3.0)
            erosion: Erosion intensity (0.0 - 5.0)

        Returns:
            Modified mesh with all filters applied
        """
        result = mesh_obj

        # Apply filters in order
        if edge_irregularity > 0:
            result = self.apply_edge_irregularity(result, edge_irregularity)

        if surface_roughness > 0:
            result = self.apply_surface_roughness(result, surface_roughness)

        if perspective_stretch > 0:
            result = self.apply_perspective_stretch(result, perspective_stretch)

        if erosion > 0:
            result = self.apply_erosion(result, erosion)

        return result

    def _generate_noise(
        self, positions: np.ndarray, frequency: float = 1.0
    ) -> np.ndarray:
        """
        Generate coherent noise values for given positions.

        Args:
            positions: Array of 3D positions (N, 3)
            frequency: Noise frequency

        Returns:
            Array of noise values (N,)
        """
        # Simple noise using sine waves with different phases
        x = positions[:, 0] * frequency
        y = positions[:, 1] * frequency
        z = positions[:, 2] * frequency

        # Combine multiple octaves
        noise = np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z) + np.sin(z) * np.cos(x)

        # Add higher frequency detail
        noise += 0.5 * (
            np.sin(x * 2.5 + 1.23) * np.cos(y * 2.5 + 4.56) +
            np.sin(y * 2.5 + 7.89) * np.cos(z * 2.5 + 2.34)
        )

        # Normalize to [-1, 1]
        if noise.max() - noise.min() > 0:
            noise = (noise - noise.min()) / (noise.max() - noise.min()) * 2 - 1

        return noise
