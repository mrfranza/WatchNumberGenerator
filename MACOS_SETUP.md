# macOS Setup Guide

This guide explains how to run Watch Number Generator on macOS.

## Prerequisites

### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install GTK4 and System Dependencies

```bash
brew install gtk4 libadwaita cairo
```

This will install all necessary system libraries including:
- GTK4 (UI framework)
- Libadwaita (GNOME design library)
- Cairo (2D graphics)
- All their dependencies (glib, pango, harfbuzz, etc.)

## Python Environment Setup

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python Dependencies

Install PyGObject and pycairo with correct pkg-config paths:

```bash
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
pip install pycairo PyGObject
```

### 3. Install Other Requirements

```bash
pip install -r requirements.txt
```

## Running the Application

### Quick Start

```bash
./run.sh
```

### Manual Start

```bash
cd src
python3 main.py
```

## Known Issues on macOS

### GTK Warnings
You may see warnings like:
```
Gtk-WARNING **: Broken accounting of active state for widget...
```

These are normal on macOS and don't affect functionality. They occur due to differences between macOS and Linux windowing systems.

### Font Rendering
- Font rendering may look slightly different than on Linux
- Some system fonts may not be available
- Default fallback fonts are used when specified fonts are missing

### Performance
- 3D preview may be slower on macOS due to OpenGL implementation differences
- Cairo rendering is well-supported and performs well

## Troubleshooting

### "Namespace Gtk not available"

Make sure you've installed GTK4 via Homebrew:
```bash
brew install gtk4 libadwaita
```

And installed PyGObject in your venv:
```bash
source .venv/bin/activate
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
pip install PyGObject pycairo
```

### Import Errors

If you see import errors, verify your virtual environment is activated:
```bash
source .venv/bin/activate
which python  # Should show path in .venv
```

### Missing Dependencies

Install all requirements again:
```bash
pip install --upgrade -r requirements.txt
```

## Permanent Configuration

To avoid setting `PKG_CONFIG_PATH` every time, add to your `~/.zshrc` or `~/.bash_profile`:

```bash
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
```

Then reload your shell:
```bash
source ~/.zshrc  # or source ~/.bash_profile
```

## Development on macOS

All development tools work normally:

```bash
# Testing
pytest tests/

# Code formatting
black src/

# Type checking
mypy src/
```

## Platform-Specific Notes

### Differences from Linux

1. **Window Management**: macOS handles windows differently, some GTK features may behave differently
2. **Keyboard Shortcuts**: Some GTK shortcuts may conflict with macOS shortcuts
3. **File Dialogs**: Native macOS file dialogs are not used (GTK dialogs are shown)
4. **Notifications**: Toast notifications work but may look different

### Recommended Configuration

For best experience on macOS:
- Use a recent version of macOS (12+)
- Ensure Xcode Command Line Tools are installed: `xcode-select --install`
- Use the latest Homebrew packages: `brew update && brew upgrade`

## Building for Distribution (Future)

Currently, the app runs from source. For distribution options:

1. **PyInstaller**: Bundle Python + GTK (experimental on macOS)
2. **App Bundle**: Create .app bundle with GTK frameworks
3. **Homebrew Formula**: Distribute via Homebrew tap

These are not yet implemented but possible for future releases.
