#!/bin/bash
#
# Ajan OCR Annotation Tool - Installation Script for Linux/Mac
# This script automates the installation process
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════"
echo "  Ajan OCR Annotation Tool - Installation Script"
echo "  Version 3.0.0"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION or higher is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing virtual environment..."
        rm -rf venv
    else
        print_info "Using existing virtual environment..."
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Install dependencies
print_info "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Ask about GPU support
echo ""
read -p "Do you want to install GPU support (CUDA required)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Installing PaddlePaddle GPU version..."
    pip uninstall -y paddlepaddle
    pip install paddlepaddle-gpu
    print_success "GPU support installed"
fi

# Install package in development mode
print_info "Installing package in development mode..."
pip install -e .

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p data/workspaces
mkdir -p output_det
mkdir -p output_rec
mkdir -p logs
mkdir -p models

print_success "Directories created"

# Make run script executable
if [ -f "run.sh" ]; then
    chmod +x run.sh
    print_info "Made run.sh executable"
fi

# Installation complete
echo ""
echo -e "${GREEN}"
echo "═══════════════════════════════════════════════════════════"
echo "  Installation Complete!"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"
echo ""
echo "To run the application:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run: python main.py"
echo "     OR: ./run.sh"
echo ""
echo "For more information, see README.md"
echo ""

# Deactivate virtual environment
deactivate 2>/dev/null || true
