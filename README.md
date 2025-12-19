# Watch Number Generator

Generate 3D printable numbers for custom watch dials.

![GTK4 Application](https://img.shields.io/badge/GTK-4.0-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-GPL--3.0-red)

## Overview

Watch Number Generator is a GTK4/Libadwaita application for creating customizable 3D-printable watch dial numbers. Design your numbers with precise dimensions, choose from different styles, apply artistic distortion filters, and export ready-to-print STL files.

## Features

- **Precise Dimensions**: Control outer and inner radius for perfect dial fit
- **Number Styles**: Choose between decimal (1-12) or Roman numerals (I-XII)
- **Flexible Sets**: Display all numbers or just cardinals (12, 3, 6, 9)
- **Font Selection**: Use any system font for number rendering
- **Mesh Parameters**: Adjust extrusion depth and margins
- **Distortion Filters**:
  - Edge irregularity for organic feel
  - Surface roughness for texture
  - Perspective stretch for artistic effects
  - Erosion for vintage/worn appearance
- **Interactive 2D Preview**: Zoom, pan, and view technical dimensions
- **Batch Export**: Individual STL files or combined mesh with metadata

## Installation

### System Requirements

- Python 3.11 or higher
- GTK4
- Libadwaita
- Cairo

### Fedora/RHEL

```bash
sudo dnf install gtk4-devel libadwaita-devel python3-gobject
sudo dnf install cairo-devel python3-cairo python3-cairo-devel
```

### Debian/Ubuntu

```bash
sudo apt install libgtk-4-dev libadwaita-1-dev python3-gi
sudo apt install libcairo2-dev python3-cairo
```

### Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
cd src
python main.py
```

### Workflow

1. **Set Dimensions**: Enter outer and inner radius in millimeters
2. **Choose Style**: Select number system (decimal/roman) and set (all/cardinals)
3. **Pick Font**: Choose any system font for the numbers
4. **Adjust Mesh**: Set extrusion depth and margins
5. **Apply Filters** (optional): Enable distortion filters for artistic effects
6. **Preview**: View 2D layout with zoom and pan
7. **Export**: Generate ZIP archive with STL files and metadata

### Export Contents

The exported ZIP includes:
- `numbers/individual/` - Individual STL files (1.stl, 2.stl, etc.)
- `numbers/combined.stl` - Single mesh with all numbers
- `preview.png` - Screenshot of 2D layout
- `README.txt` - Project parameters and print recommendations

## Project Structure

```
WatchNumberGenerator/
├── src/
│   ├── main.py              # Application entry point
│   ├── window.py            # Main window with controls
│   ├── ui/
│   │   ├── preview_2d.py    # Cairo-based 2D preview widget
│   │   └── ...
│   ├── core/
│   │   ├── font_handler.py  # Font to polygon conversion
│   │   ├── mesh_generator.py # STL mesh generation
│   │   ├── distortion.py    # Distortion filters
│   │   └── exporter.py      # ZIP export with metadata
│   └── utils/
│       └── geometry.py      # Geometric calculations
├── data/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
```

### Type Checking

```bash
mypy src/
```

## 3D Printing Tips

### Recommended Settings

- **Layer Height**: 0.1-0.2 mm for best detail
- **Infill**: 20-30% for good strength
- **Supports**: May be needed for complex fonts
- **Orientation**: Print numbers face-up

### Material Suggestions

- **PLA**: Easy to print, good detail
- **PETG**: More durable, slightly harder to print
- **Resin**: Best detail for small numbers

## Roadmap

- [ ] 3D mesh preview widget
- [ ] More distortion filter presets
- [ ] Template library (vintage, modern, minimalist)
- [ ] Export to additional formats (OBJ, 3MF)
- [ ] Flatpak packaging

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## License

GPL-3.0-or-later

## Author

Alberto Franzin (franzinalberto01@gmail.com)

## Acknowledgments

- Built with GTK4 and Libadwaita
- Uses numpy-stl for mesh generation
- Uses trimesh for 3D operations
- Uses Cairo for 2D rendering
