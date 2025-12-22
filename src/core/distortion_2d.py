"""2D distortion filters for path/contour manipulation."""

import numpy as np
import math
from typing import List, Tuple
import random


class Distortion2D:
    """Apply distortion effects to 2D vector paths."""

    def __init__(self, seed: int = 42):
        """
        Initialize 2D distortion filters.

        Args:
            seed: Random seed for reproducible results
        """
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def apply_edge_irregularity(
        self,
        contours: List[List[Tuple[float, float]]],
        intensity: float
    ) -> List[List[Tuple[float, float]]]:
        """
        Add random irregularity to path edges.

        Args:
            contours: List of contours (each is list of (x, y) points)
            intensity: Irregularity intensity (0.0 - 5.0)

        Returns:
            Modified contours
        """
        if intensity <= 0:
            return contours

        result = []
        for contour in contours:
            modified = []
            for x, y in contour:
                # Add random displacement
                dx = np.random.normal(0, intensity * 0.5)
                dy = np.random.normal(0, intensity * 0.5)
                modified.append((x + dx, y + dy))
            result.append(modified)

        return result

    def apply_roughness(
        self,
        contours: List[List[Tuple[float, float]]],
        intensity: float
    ) -> List[List[Tuple[float, float]]]:
        """
        Add surface roughness using coherent noise.

        Args:
            contours: List of contours
            intensity: Roughness intensity (0.0 - 5.0)

        Returns:
            Modified contours
        """
        if intensity <= 0:
            return contours

        result = []
        for contour in contours:
            modified = []
            for i, (x, y) in enumerate(contour):
                # Calculate normal direction (perpendicular to path)
                if i < len(contour) - 1:
                    next_x, next_y = contour[i + 1]
                else:
                    next_x, next_y = contour[0]

                # Tangent vector
                tx = next_x - x
                ty = next_y - y
                length = math.sqrt(tx*tx + ty*ty)

                if length > 0:
                    # Normal (perpendicular)
                    nx = -ty / length
                    ny = tx / length

                    # Noise based on position
                    noise = self._coherent_noise(x, y, frequency=2.0)

                    # Displace along normal
                    displacement = noise * intensity * 0.3
                    modified.append((x + nx * displacement, y + ny * displacement))
                else:
                    modified.append((x, y))

            result.append(modified)

        return result

    def apply_perspective_stretch(
        self,
        contours: List[List[Tuple[float, float]]],
        intensity: float,
        center: Tuple[float, float] = None
    ) -> List[List[Tuple[float, float]]]:
        """
        Apply radial perspective stretch.

        Args:
            contours: List of contours
            intensity: Stretch intensity (0.0 - 3.0)
            center: Center point for radial stretch (auto-calculated if None)

        Returns:
            Modified contours
        """
        if intensity <= 0:
            return contours

        # Calculate center if not provided
        if center is None:
            all_points = [p for contour in contours for p in contour]
            if not all_points:
                return contours
            cx = sum(p[0] for p in all_points) / len(all_points)
            cy = sum(p[1] for p in all_points) / len(all_points)
            center = (cx, cy)

        # Find max distance for normalization
        max_dist = 0
        for contour in contours:
            for x, y in contour:
                dist = math.sqrt((x - center[0])**2 + (y - center[1])**2)
                max_dist = max(max_dist, dist)

        if max_dist == 0:
            return contours

        result = []
        for contour in contours:
            modified = []
            for x, y in contour:
                dx = x - center[0]
                dy = y - center[1]
                dist = math.sqrt(dx*dx + dy*dy)

                # Radial stretch factor
                stretch = 1.0 + (intensity * 0.1 * dist / max_dist)

                new_x = center[0] + dx * stretch
                new_y = center[1] + dy * stretch
                modified.append((new_x, new_y))

            result.append(modified)

        return result

    def apply_erosion(
        self,
        contours: List[List[Tuple[float, float]]],
        intensity: float,
        center: Tuple[float, float] = None
    ) -> List[List[Tuple[float, float]]]:
        """
        Apply erosion effect (scaling towards center with noise).

        Args:
            contours: List of contours
            intensity: Erosion intensity (0.0 - 5.0)
            center: Center point (auto-calculated if None)

        Returns:
            Modified contours
        """
        if intensity <= 0:
            return contours

        # Calculate center if not provided
        if center is None:
            all_points = [p for contour in contours for p in contour]
            if not all_points:
                return contours
            cx = sum(p[0] for p in all_points) / len(all_points)
            cy = sum(p[1] for p in all_points) / len(all_points)
            center = (cx, cy)

        # Find max distance
        max_dist = 0
        for contour in contours:
            for x, y in contour:
                dist = math.sqrt((x - center[0])**2 + (y - center[1])**2)
                max_dist = max(max_dist, dist)

        if max_dist == 0:
            return contours

        result = []
        for contour in contours:
            modified = []
            for x, y in contour:
                dx = x - center[0]
                dy = y - center[1]
                dist = math.sqrt(dx*dx + dy*dy)

                # Erosion amount (more on edges)
                dist_norm = dist / max_dist
                erosion = dist_norm * intensity * 0.05

                # Add noise
                noise = np.random.normal(0, intensity * 0.02)
                erosion += noise

                # Scale towards center
                scale = 1.0 - erosion

                new_x = center[0] + dx * scale
                new_y = center[1] + dy * scale
                modified.append((new_x, new_y))

            result.append(modified)

        return result

    def apply_all(
        self,
        contours: List[List[Tuple[float, float]]],
        edge_irregularity: float = 0.0,
        surface_roughness: float = 0.0,
        perspective_stretch: float = 0.0,
        erosion: float = 0.0,
        center: Tuple[float, float] = None
    ) -> List[List[Tuple[float, float]]]:
        """
        Apply all distortion filters in sequence.

        Args:
            contours: Input contours
            edge_irregularity: Edge irregularity intensity
            surface_roughness: Surface roughness intensity
            perspective_stretch: Perspective stretch intensity
            erosion: Erosion intensity
            center: Center point for radial effects

        Returns:
            Modified contours with all filters applied
        """
        result = contours

        if edge_irregularity > 0:
            result = self.apply_edge_irregularity(result, edge_irregularity)

        if surface_roughness > 0:
            result = self.apply_roughness(result, surface_roughness)

        if perspective_stretch > 0:
            result = self.apply_perspective_stretch(result, perspective_stretch, center)

        if erosion > 0:
            result = self.apply_erosion(result, erosion, center)

        return result

    def _coherent_noise(self, x: float, y: float, frequency: float = 1.0) -> float:
        """
        Generate coherent 2D noise value.

        Args:
            x, y: Coordinates
            frequency: Noise frequency

        Returns:
            Noise value in range [-1, 1]
        """
        x *= frequency
        y *= frequency

        # Simple noise using sine waves
        noise = math.sin(x) * math.cos(y) + math.sin(y * 1.5 + 3.7) * math.cos(x * 1.5 + 2.1)

        # Add octave
        noise += 0.5 * (math.sin(x * 2.5 + 1.23) * math.cos(y * 2.5 + 4.56))

        # Normalize
        noise = max(-1.0, min(1.0, noise / 2.0))

        return noise
