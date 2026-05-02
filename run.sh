#!/bin/bash
#
# Ajan OCR Annotation Tool - Run Script for Linux/Mac
# Quick launcher for the application
#

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}[ERROR]${NC} Virtual environment not found!"
    echo "Please run install.sh first:"
    echo "  ./install.sh"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}[INFO]${NC} Starting Ajan OCR Annotation Tool..."
source venv/bin/activate

# Run the application
python main.py

# Deactivate when done
deactivate 2>/dev/null || true
