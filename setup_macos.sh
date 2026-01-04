#!/bin/bash
# Automated setup script for macOS
set -e

echo "🍎 Watch Number Generator - macOS Setup"
echo "========================================"
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found!"
    echo "Please install Homebrew first: https://brew.sh"
    echo ""
    echo "Run this command:"
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo "✅ Homebrew found"
echo ""

# Check if GTK4 is installed
if ! brew list gtk4 &> /dev/null; then
    echo "📦 Installing GTK4 and dependencies..."
    brew install gtk4 libadwaita cairo
    echo "✅ GTK4 installed"
else
    echo "✅ GTK4 already installed"
fi
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment and install packages
echo "📦 Installing Python packages..."
source .venv/bin/activate

# Set pkg-config path for GTK libraries
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"

# Install PyGObject and pycairo first
echo "  - Installing PyGObject and pycairo..."
pip install --quiet --upgrade pip
pip install --quiet pycairo PyGObject

# Install other requirements
echo "  - Installing project requirements..."
pip install --quiet -r requirements.txt

echo "✅ All Python packages installed"
echo ""

# Check if mapbox-earcut is installed (needed for mesh generation)
if ! python -c "import mapbox_earcut" 2>/dev/null; then
    echo "📦 Installing mapbox-earcut for mesh generation..."
    pip install --quiet mapbox_earcut
    echo "✅ mapbox-earcut installed"
else
    echo "✅ mapbox-earcut already installed"
fi
echo ""

echo "🎉 Setup complete!"
echo ""
echo "To run the application:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  source .venv/bin/activate"
echo "  cd src"
echo "  python3 main.py"
echo ""
echo "📖 For troubleshooting, see MACOS_SETUP.md"
