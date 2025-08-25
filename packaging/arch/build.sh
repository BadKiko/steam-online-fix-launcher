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
    # Create source tarball for makepkg (write to dist/output directory)
    echo "Creating source tarball from git repository..."
    git -C "$PROJECT_DIR" archive --format=tar.gz \
        --prefix="steam-online-fix-launcher-$VERSION/" \
        -o "$OUTPUT_DIR/$PACKAGE_NAME-$VERSION.tar.gz" HEAD
else
    echo "Not in a git repository, creating tarball from current directory..."
    # Create tarball from current directory if not in git repo
    # Use a temporary directory to avoid issues with changing files
    TMP_DIR=$(mktemp -d)
    cp -r . "$TMP_DIR/steam-online-fix-launcher-$VERSION"
    cd "$TMP_DIR"

    # Clean up build artifacts and temporary files
    cd "steam-online-fix-launcher-$VERSION"
    rm -rf build* dist .git* *.log *.tmp cache __pycache__ *.pyc build-dir flatpak-build *.flatpak *.deb *.pkg.tar.zst .ninja* compile_commands.json meson-private meson-info meson-logs subprojects *.so *.o

    # Create the tarball from the cleaned directory (write to dist/output directory)
    tar -czf "$OUTPUT_DIR/$PACKAGE_NAME-$VERSION.tar.gz" --transform "s,^./,steam-online-fix-launcher-$VERSION/," .

    cd "$PROJECT_DIR"
    rm -rf "$TMP_DIR"
fi

# Prepare working directory for PKGBUILD edits
BUILD_WORK_DIR="$OUTPUT_DIR/arch-build-$VERSION"
# Ensure the build work directory exists and is writable
mkdir -p "$BUILD_WORK_DIR" || { echo "Error: could not create $BUILD_WORK_DIR"; exit 1; }

# Try to make it writable for the current user; bail if still not writable
chmod u+rwx "$BUILD_WORK_DIR" 2>/dev/null || true
if [ ! -w "$BUILD_WORK_DIR" ]; then
    echo "Error: $BUILD_WORK_DIR is not writable by the current user"
    exit 1
fi

# Copy PKGBUILD and update version there (avoid writing to repo directory)
echo "Preparing PKGBUILD in working directory: $BUILD_WORK_DIR"
cp "$ARCH_DIR/PKGBUILD" "$BUILD_WORK_DIR/PKGBUILD"
sed -i "s/pkgver=.*/pkgver=$VERSION/" "$BUILD_WORK_DIR/PKGBUILD"

# Sanitize PKGBUILD: remove any legacy manual install lines if present
sed -i "/data\/org.badkiko\\.sofl\\.desktop/d" "$BUILD_WORK_DIR/PKGBUILD" || true
sed -i "/data\/org.badkiko\\.sofl\\.metainfo\\.xml/d" "$BUILD_WORK_DIR/PKGBUILD" || true

echo "Using source tarball from output directory: $OUTPUT_DIR/$PACKAGE_NAME-$VERSION.tar.gz"

# Build the package
echo "Building package with makepkg..."
cd "$BUILD_WORK_DIR"

# Direct makepkg to use output directory for sources and packages
export SRCDEST="$OUTPUT_DIR"
export PKGDEST="$OUTPUT_DIR"

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
    # Run makepkg from the working directory so the edited PKGBUILD is used
    runuser -u "$BUILD_USER" -- bash -c "cd '$BUILD_WORK_DIR' && export SRCDEST='$SRCDEST' && export PKGDEST='$PKGDEST' && export PACKAGER='$PACKAGER' && export BUILDDIR='$BUILDDIR' && makepkg -f --noconfirm --skipinteg"
else
    # Non-root case: run makepkg from the working directory
    bash -c "cd '$BUILD_WORK_DIR' && export SRCDEST='$SRCDEST' && export PKGDEST='$PKGDEST' && export PACKAGER='$PACKAGER' && export BUILDDIR='$BUILDDIR' && makepkg -f --noconfirm --skipinteg"
fi

echo "Arch Linux package built successfully!"

# Move created packages if any were dropped in arch dir (fallback)
if ls *.pkg.tar.zst *.tar.gz 1>/dev/null 2>&1; then
    if [ "$OUTPUT_DIR" != "." ]; then
        mkdir -p "$OUTPUT_DIR"
        mv *.pkg.tar.zst *.tar.gz "$OUTPUT_DIR/" 2>/dev/null || true
        echo "Packages moved to: $OUTPUT_DIR"
    else
        mv *.pkg.tar.zst *.tar.gz ../ 2>/dev/null || true
    fi
fi

# List created files
if [ "$OUTPUT_DIR" != "." ]; then
    ls -la "$OUTPUT_DIR"/*.pkg.tar.zst "$OUTPUT_DIR"/*.tar.gz 2>/dev/null || echo "No packages found in $OUTPUT_DIR"
else
    ls -la ../*.pkg.tar.zst ../*.tar.gz 2>/dev/null || echo "No packages found"
fi

# No cleanup needed in arch directory when using SRCDEST

echo "Arch Linux package build completed!"
echo "Created packages in: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.pkg.tar.zst "$OUTPUT_DIR"/*.tar.gz 2>/dev/null || echo "No packages found"
