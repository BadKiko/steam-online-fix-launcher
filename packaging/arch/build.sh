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

# Install build dependencies if possible (only when running as root)
if command -v pacman &> /dev/null && [ "$(id -u)" -eq 0 ]; then
    echo "Installing build dependencies..."
    pacman -Sy --noconfirm --needed meson ninja git || echo "Could not install dependencies, continuing anyway..."
else
    echo "Skipping dependency installation (not root or pacman unavailable)"
fi

# Fix git safe directory issue
git config --global --add safe.directory "$PROJECT_DIR" || true

# Check if we're in a git repository
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Create source tarball for makepkg (write to arch directory)
    echo "Creating source tarball from git repository..."
    git -C "$PROJECT_DIR" archive --format=tar.gz \
        --prefix="$PACKAGE_NAME-$VERSION/" \
        -o "$ARCH_DIR/$PACKAGE_NAME-$VERSION.tar.gz" HEAD
else
    echo "Not in a git repository, creating tarball from current directory..."
    # Create tarball from current directory if not in git repo
    # Use a temporary directory to avoid issues with changing files
    TMP_DIR=$(mktemp -d)
    cp -r . "$TMP_DIR/$PACKAGE_NAME-$VERSION"
    cd "$TMP_DIR"

    # Clean up build artifacts and temporary files
    cd "$PACKAGE_NAME-$VERSION"
    rm -rf build* dist .git* *.log *.tmp cache __pycache__ *.pyc build-dir flatpak-build *.flatpak *.deb *.pkg.tar.zst .ninja* compile_commands.json meson-private meson-info meson-logs subprojects *.so *.o

    # Create the tarball from the cleaned directory (write to arch directory)
    tar -czf "$ARCH_DIR/$PACKAGE_NAME-$VERSION.tar.gz" --transform "s,^./,$PACKAGE_NAME-$VERSION/," .

    cd "$PROJECT_DIR"
    rm -rf "$TMP_DIR"
fi

# Update version in PKGBUILD
echo "Updating PKGBUILD..."
sed -i "s/pkgver=.*/pkgver=$VERSION/" "$ARCH_DIR/PKGBUILD"

# Ensure tarball exists in arch directory
echo "Ensuring source tarball is in build directory..."
if [ ! -f "$ARCH_DIR/$PACKAGE_NAME-$VERSION.tar.gz" ] && [ -f "$PACKAGE_NAME-$VERSION.tar.gz" ]; then
    cp "$PACKAGE_NAME-$VERSION.tar.gz" "$ARCH_DIR/"
fi

# Build the package
echo "Building package with makepkg..."
cd "$ARCH_DIR"

# Set PKGDEST to current directory so makepkg puts the package here
export PKGDEST="$PWD"

# Ensure we have an unprivileged user for makepkg
if id -u builder &>/dev/null; then
    BUILD_USER=builder
elif [ "$(id -u)" -eq 0 ]; then
    echo "Creating temporary 'builder' user for packaging..."
    useradd -m -s /bin/bash builder || true
    BUILD_USER=builder
else
    echo "No 'builder' user found, using current user: $(id -un)"
    BUILD_USER=$(id -un)
fi

# Configure makepkg environment
export PACKAGER="CI Builder <ci@localhost>"
export BUILDDIR="/tmp/makepkg-build"
mkdir -p "$BUILDDIR"

# Change ownership of project directory to build user when running as root
if [ "$(id -u)" -eq 0 ] && [ -n "$BUILD_USER" ]; then
    chown -R "$BUILD_USER":"$BUILD_USER" "$PROJECT_DIR" || echo "Warning: Could not change ownership of project directory"
fi

# Run makepkg as unprivileged user
if [ "$(id -u)" -eq 0 ] && [ "$BUILD_USER" != "root" ]; then
    runuser -u "$BUILD_USER" -- bash -c "cd '$ARCH_DIR' && export PKGDEST='$PWD' && export PACKAGER='$PACKAGER' && export BUILDDIR='$BUILDDIR' && makepkg -f --noconfirm --skipinteg"
else
    bash -c "cd '$ARCH_DIR' && export PKGDEST='$PWD' && export PACKAGER='$PACKAGER' && export BUILDDIR='$BUILDDIR' && makepkg -f --noconfirm --skipinteg"
fi

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
