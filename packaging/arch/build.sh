#!/bin/bash

# Arch Linux Package Build Script for SOFL
# Usage: ./build.sh [version] [output_dir]

set -e

VERSION=${1:-"0.0.3"}
PACKAGE_NAME="sofl"
OUTPUT_DIR=${2:-"../../dist"}

echo "Building Arch Linux package for $PACKAGE_NAME version $VERSION..."

# Check if we're running on Arch Linux (has makepkg)
if ! command -v makepkg &> /dev/null; then
    echo "Error: Arch Linux package can only be built on Arch Linux systems"
    echo "This script requires 'makepkg' which is only available on Arch Linux"
    echo "For CI/CD builds, use GitHub Actions with Arch Linux container"
    echo ""
    echo "To build on Arch Linux:"
    echo "  1. Install Arch Linux"
    echo "  2. Install base-devel: sudo pacman -S base-devel"
    echo "  3. Run this script: ./build.sh"
    exit 1
fi

echo "Detected Arch Linux system - building directly with makepkg"

# Get absolute paths
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$(cd "$PROJECT_DIR" && mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)"

echo "Project directory: $PROJECT_DIR"
echo "Arch directory: $ARCH_DIR"
echo "Output directory: $OUTPUT_DIR"

cd "$PROJECT_DIR"

# Install build dependencies if possible
if command -v pacman &> /dev/null; then
    echo "Installing build dependencies..."
    sudo pacman -Sy --needed meson ninja git || echo "Could not install dependencies, continuing anyway..."
fi

# Fix git safe directory issue
git config --global --add safe.directory "$PROJECT_DIR" || true

# Create source tarball for makepkg
echo "Creating source tarball..."
git archive --format=tar.gz --prefix="$PACKAGE_NAME-$VERSION/" -o "$PACKAGE_NAME-$VERSION.tar.gz" HEAD

# Update version in PKGBUILD
echo "Updating PKGBUILD..."
sed -i "s/pkgver=.*/pkgver=$VERSION/" "$ARCH_DIR/PKGBUILD"

# Copy tarball to arch directory
echo "Copying source tarball to build directory..."
cp "$PACKAGE_NAME-$VERSION.tar.gz" "$ARCH_DIR/"

# Build the package
echo "Building package with makepkg..."
cd "$ARCH_DIR"

# Set PKGDEST to current directory so makepkg puts the package here
export PKGDEST="$PWD"

makepkg -f --noconfirm

echo "Arch Linux package built successfully!"

# Move created packages to output directory
if [ "$OUTPUT_DIR" != "." ]; then
    mkdir -p "$OUTPUT_DIR"
    mv *.pkg.tar.zst *.tar.gz "$OUTPUT_DIR/" 2>/dev/null || true
    echo "Packages moved to: $OUTPUT_DIR"
else
    # If no output directory specified, move to project root
    mv *.pkg.tar.zst *.tar.gz ../ 2>/dev/null || true
fi

# List created files
if [ "$OUTPUT_DIR" != "." ]; then
    ls -la "$OUTPUT_DIR"/*.pkg.tar.zst "$OUTPUT_DIR"/*.tar.gz 2>/dev/null || echo "No packages found in $OUTPUT_DIR"
else
    ls -la ../*.pkg.tar.zst ../*.tar.gz 2>/dev/null || echo "No packages found"
fi

# Clean up tarball from arch directory
rm -f "$PACKAGE_NAME-$VERSION.tar.gz"

echo "Arch Linux package build completed!"
echo "Created packages in: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.pkg.tar.zst "$OUTPUT_DIR"/*.tar.gz 2>/dev/null || echo "No packages found"
