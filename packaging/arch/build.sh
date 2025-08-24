#!/bin/bash

# Arch Linux Package Build Script for SOFL
# Usage: ./build.sh [version]

set -e

VERSION=${1:-"0.0.3"}
PACKAGE_NAME="sofl"
ARCH_DIR="packaging/arch"

echo "Building Arch Linux package for $PACKAGE_NAME version $VERSION..."

# Check if makepkg is available (Arch Linux)
if ! command -v makepkg &> /dev/null; then
    echo "Warning: makepkg not found. This script is designed for Arch Linux."
    echo "You can still use the PKGBUILD manually on Arch systems."
    echo "Building source package..."

    # Create source tarball
    cd /home/kiko/Work/steam-online-fix-launcher
    git archive --format=tar.gz --prefix="$PACKAGE_NAME-$VERSION/" -o "../$PACKAGE_NAME-$VERSION.tar.gz" HEAD

    echo "Source tarball created: $PACKAGE_NAME-$VERSION.tar.gz"
    echo "To build on Arch Linux:"
    echo "  1. Copy $PACKAGE_NAME-$VERSION.tar.gz and $ARCH_DIR/PKGBUILD to a directory"
    echo "  2. Update PKGBUILD source URL with the correct tarball name"
    echo "  3. Run: makepkg -si"
    exit 0
fi

# Update version in PKGBUILD
cd /home/kiko/Work/steam-online-fix-launcher
sed -i "s/pkgver=.*/pkgver=$VERSION/" "$ARCH_DIR/PKGBUILD"

# Build the package
echo "Building package with makepkg..."
cd "$ARCH_DIR"
makepkg -f

echo "Arch Linux package built successfully!"

# List created files
ls -la *.pkg.tar.zst *.tar.gz 2>/dev/null || true
