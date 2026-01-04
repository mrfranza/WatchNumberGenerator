"""Unified mesh generation pipeline for consistent 2D/3D representation.

This module provides a single source of truth for mesh generation, ensuring
that 2D preview and 3D mesh show identical geometry with correct positioning.
"""

import numpy as np
from stl import mesh
from typing import List, Dict, Tuple
import logging

from core.font_handler import FontHandler
from core.mesh_generator import MeshGenerator
from utils.geometry import NumberPosition

logger = logging.getLogger(__name__)


class UnifiedMeshPipeline:
    """
    Unified pipeline for generating positioned 3D meshes.

    This ensures 2D preview and 3D mesh use identical transformations:
    - Font to vector conversion
    - Scaling to fit sector
    - Rotation around dial
    - Positioning at correct radius
    - Extrusion to 3D
    """

    def __init__(self):
        self.font_handler = FontHandler()
        self.mesh_generator = MeshGenerator()

    def generate_positioned_numbers(
        self,
        positions: List[NumberPosition],
        font_desc: str,
        extrusion_depth: float,
    ) -> Tuple[mesh.Mesh, List[Dict]]:
        """
        Generate 3D mesh with numbers positioned on dial.

        Args:
            positions: List of NumberPosition objects with sector geometry
            font_desc: Font description string (e.g., "Sans Bold 12")
            extrusion_depth: Z-depth for extrusion (mm)

        Returns:
            Tuple of (combined_mesh, numbers_data_list)
            - combined_mesh: Single STL mesh with all numbers
            - numbers_data_list: List of dicts with per-number metadata
        """
        logger.info(f"Generating {len(positions)} numbers with depth {extrusion_depth}mm")

        all_meshes = []
        numbers_data = []

        for pos in positions:
            try:
                # Generate single number mesh with correct positioning
                number_mesh, metadata = self._generate_single_number(
                    pos, font_desc, extrusion_depth
                )

                if number_mesh is not None:
                    all_meshes.append(number_mesh)
                    numbers_data.append(metadata)
                    logger.debug(f"Generated number '{pos.number}' at angle {np.degrees(pos.angle):.1f}°")
                else:
                    logger.warning(f"Failed to generate number '{pos.number}'")

            except Exception as e:
                logger.error(f"Error generating number '{pos.number}': {e}")
                continue

        if not all_meshes:
            logger.error("No meshes generated!")
            return self.mesh_generator._create_empty_mesh(), []

        # Combine all meshes into one
        logger.info(f"Combining {len(all_meshes)} meshes...")
        combined = mesh.Mesh(np.concatenate([m.data for m in all_meshes]))

        logger.info(f"Combined mesh: {len(combined.vectors)} triangles")

        return combined, numbers_data

    def _generate_single_number(
        self,
        pos: NumberPosition,
        font_desc: str,
        extrusion_depth: float,
    ) -> Tuple[mesh.Mesh, Dict]:
        """
        Generate mesh for a single number with correct positioning.

        Pipeline:
        1. Convert text to vector paths using font
        2. Scale paths to fit in sector (max_width, max_height)
        3. Rotate paths to align with dial angle
        4. Translate paths to position on dial (center_x, center_y)
        5. Extrude to 3D with depth
        6. Return positioned mesh + metadata

        Args:
            pos: NumberPosition with sector geometry
            font_desc: Font description
            extrusion_depth: Extrusion depth

        Returns:
            Tuple of (mesh, metadata_dict)
        """
        # Step 1: Get vector paths from font
        # Use max_height as target for font rendering
        contours, actual_width, actual_height = self.font_handler.get_text_path(
            pos.number,
            font_desc,
            target_height=pos.max_height  # Use sector height as initial target
        )

        if not contours:
            logger.warning(f"No contours for number '{pos.number}'")
            return None, {}

        # Step 2: Calculate scaling to fit sector
        # Font handler returns paths scaled to max_height, but we need to fit in BOTH dimensions
        width_scale = pos.max_width / actual_width if actual_width > 0 else 1.0
        height_scale = pos.max_height / actual_height if actual_height > 0 else 1.0

        # Use minimum scale to ensure it fits in sector
        final_scale = min(width_scale, height_scale) * 0.95  # 95% for small margin

        logger.debug(
            f"Number '{pos.number}': "
            f"actual={actual_width:.2f}x{actual_height:.2f}, "
            f"sector={pos.max_width:.2f}x{pos.max_height:.2f}, "
            f"scale={final_scale:.3f}"
        )

        # Apply scaling to contours
        scaled_contours = []
        for contour in contours:
            scaled = [(x * final_scale, y * final_scale) for x, y in contour]
            scaled_contours.append(scaled)

        # Step 3: Calculate rotation angle
        # pos.angle is from geometry (0 = 12 o'clock, clockwise)
        # We need to rotate text to align radially
        rotation_angle = pos.angle

        # Step 4: Apply rotation and translation
        positioned_contours = self._transform_contours(
            scaled_contours,
            rotation_angle=rotation_angle,
            center_x=pos.center_x,
            center_y=pos.center_y,
        )

        # Step 5: Extrude to 3D
        # Note: Y coordinate needs to be inverted for STL (Cairo uses Y-down, STL uses Y-up)
        stl_contours = []
        for contour in positioned_contours:
            # Invert Y for STL coordinate system
            stl_contour = [(x, -y) for x, y in contour]
            stl_contours.append(stl_contour)

        # Create 3D mesh
        number_mesh = self.mesh_generator.create_text_mesh(
            stl_contours,
            extrusion_depth,
            center_x=0.0,  # Already positioned in contours
            center_y=0.0,
        )

        # Step 6: Create metadata
        metadata = {
            "number": pos.number,
            "angle": pos.angle,
            "center_x": pos.center_x,
            "center_y": -pos.center_y,  # Inverted for STL
            "contours": stl_contours,
            "sector": {
                "inner_radius": pos.inner_radius,
                "outer_radius": pos.outer_radius,
                "angle_start": pos.angle_start,
                "angle_end": pos.angle_end,
                "max_width": pos.max_width,
                "max_height": pos.max_height,
            },
        }

        return number_mesh, metadata

    def _transform_contours(
        self,
        contours: List[List[Tuple[float, float]]],
        rotation_angle: float,
        center_x: float,
        center_y: float,
    ) -> List[List[Tuple[float, float]]]:
        """
        Apply rotation and translation to contours.

        Transformation order (matching preview_2d.py):
        1. Calculate bounding box center of contours
        2. Rotate around bounding box center (not origin)
        3. Translate to final position (center_x, center_y)

        Args:
            contours: Input contours (list of point lists)
            rotation_angle: Rotation angle in radians (0 = top, clockwise)
            center_x: X translation (final position)
            center_y: Y translation (final position)

        Returns:
            Transformed contours
        """
        # Step 1: Calculate bounding box center of all contours
        all_x = [x for contour in contours for x, y in contour]
        all_y = [y for contour in contours for x, y in contour]

        if not all_x:
            return contours

        bbox_center_x = (min(all_x) + max(all_x)) / 2.0
        bbox_center_y = (min(all_y) + max(all_y)) / 2.0

        # Step 2: Create rotation matrix
        cos_a = np.cos(rotation_angle)
        sin_a = np.sin(rotation_angle)

        transformed = []

        for contour in contours:
            transformed_contour = []
            for x, y in contour:
                # Translate to center at bounding box origin
                x_centered = x - bbox_center_x
                y_centered = y - bbox_center_y

                # Apply rotation around bounding box center
                x_rot = x_centered * cos_a - y_centered * sin_a
                y_rot = x_centered * sin_a + y_centered * cos_a

                # Translate to final position
                x_final = x_rot + center_x
                y_final = y_rot + center_y

                transformed_contour.append((x_final, y_final))

            transformed.append(transformed_contour)

        return transformed

    def generate_2d_preview_data(
        self,
        positions: List[NumberPosition],
        font_desc: str,
    ) -> List[Dict]:
        """
        Generate data for 2D preview (same transforms as 3D but without extrusion).

        Args:
            positions: List of NumberPosition objects
            font_desc: Font description

        Returns:
            List of dicts with contours and positioning for each number
        """
        preview_data = []

        for pos in positions:
            # Get vector paths
            contours, actual_width, actual_height = self.font_handler.get_text_path(
                pos.number,
                font_desc,
                target_height=pos.max_height
            )

            if not contours:
                continue

            # Calculate scaling
            width_scale = pos.max_width / actual_width if actual_width > 0 else 1.0
            height_scale = pos.max_height / actual_height if actual_height > 0 else 1.0
            final_scale = min(width_scale, height_scale) * 0.95

            # Scale contours
            scaled_contours = []
            for contour in contours:
                scaled = [(x * final_scale, y * final_scale) for x, y in contour]
                scaled_contours.append(scaled)

            # Transform (rotate + translate)
            positioned_contours = self._transform_contours(
                scaled_contours,
                rotation_angle=pos.angle,
                center_x=pos.center_x,
                center_y=pos.center_y,
            )

            preview_data.append({
                "number": pos.number,
                "contours": positioned_contours,
                "position": pos,
            })

        return preview_data
