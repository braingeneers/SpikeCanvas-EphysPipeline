#!/bin/bash

# MaxWell Dashboard Quick Start Script
# This script sets up and launches the MaxWell Ephys Pipeline Dashboard

echo "🚀 Starting MaxWell Ephys Pipeline Dashboard..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DASHBOARD_DIR="$SCRIPT_DIR/src"

# Check if we're in the right directory
if [ ! -f "$DASHBOARD_DIR/app.py" ]; then
    echo "❌ Error: app.py not found in $DASHBOARD_DIR"
    echo "Please make sure you're running this script from the MaxWell_Dashboard directory"
    exit 1
fi

# Check Python dependencies
echo "🔍 Checking Python dependencies..."

# List of required packages
REQUIRED_PACKAGES=("dash" "plotly" "dash-bootstrap-components" "braingeneers")

# Check if packages are installed
MISSING_PACKAGES=()
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! python -c "import ${package//-/_}" 2>/dev/null; then
        MISSING_PACKAGES+=("$package")
    fi
done

# Install missing packages if any
if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "📦 Installing missing packages: ${MISSING_PACKAGES[*]}"
    pip install "${MISSING_PACKAGES[@]}"
fi

# Set environment variables if needed
export PYTHONPATH="$DASHBOARD_DIR:$PYTHONPATH"

# Change to the source directory
cd "$DASHBOARD_DIR"

echo "🌐 Dashboard will be available at: http://127.0.0.1:8050/"
echo "🌍 Network access available at: http://$(hostname -I | awk '{print $1}'):8050/"
echo ""
echo "📖 Usage Instructions:"
echo "   - Open your web browser and navigate to the URL above"
echo "   - Use the Job Center to submit processing jobs"
echo "   - Monitor progress in the Status page"
echo "   - Analyze results in the Analytics page"
echo ""
echo "🛑 To stop the dashboard, press Ctrl+C"
echo ""

# Launch the dashboard
echo "🎯 Launching dashboard..."
python app.py

echo "👋 Dashboard stopped."
