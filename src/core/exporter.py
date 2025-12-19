"""Export functionality for STL files and project archives."""

import os
import zipfile
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import tempfile


class ProjectExporter:
    """Handles exporting of STL files and project metadata."""

    def __init__(self):
        pass

    def export_project(
        self,
        output_path: str,
        individual_meshes: Dict[str, any],
        combined_mesh: any,
        parameters: dict,
        preview_image_path: str = None,
    ) -> bool:
        """
        Export complete project as ZIP archive.

        Args:
            output_path: Path to output ZIP file
            individual_meshes: Dict mapping number -> mesh object
            combined_mesh: Combined mesh of all numbers
            parameters: Project parameters dictionary
            preview_image_path: Optional path to preview image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create subdirectories
                individual_dir = temp_path / "numbers" / "individual"
                individual_dir.mkdir(parents=True, exist_ok=True)

                combined_dir = temp_path / "numbers"

                # Export individual meshes
                for number, mesh_obj in individual_meshes.items():
                    filename = individual_dir / f"{number}.stl"
                    mesh_obj.save(str(filename))

                # Export combined mesh
                combined_filename = combined_dir / "combined.stl"
                combined_mesh.save(str(combined_filename))

                # Generate README
                readme_path = temp_path / "README.txt"
                self._generate_readme(readme_path, parameters)

                # Copy preview image if provided
                if preview_image_path and os.path.exists(preview_image_path):
                    import shutil
                    preview_dest = temp_path / "preview.png"
                    shutil.copy(preview_image_path, preview_dest)

                # Create ZIP archive
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from temp directory
                    for root, dirs, files in os.walk(temp_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(temp_path)
                            zipf.write(file_path, arcname)

            return True

        except Exception as e:
            print(f"Error exporting project: {e}")
            return False

    def _generate_readme(self, output_path: Path, parameters: dict):
        """
        Generate README file with project metadata.

        Args:
            output_path: Path to README file
            parameters: Project parameters
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Map parameter values to readable strings
        number_system_str = "Roman" if parameters.get("number_system") == 1 else "Decimal"
        number_set_str = (
            "Cardinals Only (12, 3, 6, 9)"
            if parameters.get("number_set") == 1
            else "All Numbers (1-12)"
        )

        # Build filter list
        filters = []
        if parameters.get("distortion_enabled", False):
            if parameters.get("edge_irregularity", 0) > 0:
                filters.append(
                    f"Edge Irregularity: {parameters['edge_irregularity']:.2f}"
                )
            if parameters.get("surface_roughness", 0) > 0:
                filters.append(
                    f"Surface Roughness: {parameters['surface_roughness']:.2f}"
                )
            if parameters.get("perspective_stretch", 0) > 0:
                filters.append(
                    f"Perspective Stretch: {parameters['perspective_stretch']:.2f}"
                )
            if parameters.get("erosion", 0) > 0:
                filters.append(f"Erosion: {parameters['erosion']:.2f}")

        filters_str = "\n  - ".join(filters) if filters else "None"
        if filters:
            filters_str = "\n  - " + filters_str

        content = f"""Watch Number Generator Export
==============================
Generated: {timestamp}

Project Parameters
------------------
Dial Dimensions:
  - Outer Radius: {parameters.get('outer_radius', 0):.1f} mm
  - Inner Radius: {parameters.get('inner_radius', 0):.1f} mm

Number Style:
  - Number System: {number_system_str}
  - Numbers Display: {number_set_str}
  - Font: {parameters.get('font', 'Sans Bold 12')}

Mesh Parameters:
  - Extrusion Depth: {parameters.get('extrusion_depth', 0):.1f} mm
  - Vertical Margin: {parameters.get('vertical_margin', 0):.1f} mm
  - Horizontal Margin: {parameters.get('horizontal_margin', 0):.1f} mm

Distortion Filters:{filters_str}

Random Seed: {parameters.get('random_seed', 42)}

Exported Files
--------------
- numbers/individual/*.stl - Individual number meshes
- numbers/combined.stl - Combined mesh with all numbers
- preview.png - 2D preview of the dial layout

Usage
-----
The STL files are ready for 3D printing. Import them into your
preferred slicing software (Cura, PrusaSlicer, etc.).

Individual Files:
  Use individual number files if you want to:
  - Print numbers in different colors
  - Position numbers separately
  - Use only specific numbers

Combined File:
  Use the combined file if you want to:
  - Print all numbers at once
  - Ensure consistent positioning

Recommended Print Settings
--------------------------
- Layer Height: 0.1-0.2 mm
- Infill: 20-30% (depending on desired strength)
- Supports: May be needed depending on font complexity
- Orientation: Numbers should be printed face-up for best detail

Notes
-----
- All dimensions are in millimeters
- STL files use standard coordinate system (Z-up)
- Numbers are oriented vertically (upright text)

Generated with Watch Number Generator
https://github.com/yourusername/watch-number-generator
"""

        with open(output_path, 'w') as f:
            f.write(content)

    def export_individual_stl(
        self, mesh_obj: any, output_path: str
    ) -> bool:
        """
        Export a single mesh to STL file.

        Args:
            mesh_obj: Mesh object to export
            output_path: Path to output STL file

        Returns:
            True if successful, False otherwise
        """
        try:
            mesh_obj.save(output_path)
            return True
        except Exception as e:
            print(f"Error exporting STL: {e}")
            return False

    def create_preview_image(
        self, cairo_surface, output_path: str
    ) -> bool:
        """
        Save Cairo surface as PNG preview image.

        Args:
            cairo_surface: Cairo surface to save
            output_path: Path to output PNG file

        Returns:
            True if successful, False otherwise
        """
        try:
            cairo_surface.write_to_png(output_path)
            return True
        except Exception as e:
            print(f"Error creating preview image: {e}")
            return False
