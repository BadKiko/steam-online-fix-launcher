#!/bin/bash

# Build all package types for SOFL
# Usage: ./build_all.sh [version] [package_types]
# Example: ./build_all.sh 0.0.3 "flatpak deb arch"

set -e

PROJECT_DIR="/home/kiko/Work/steam-online-fix-launcher"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
BUILD_DIR="$PROJECT_DIR/dist"

# Default package types
DEFAULT_PACKAGES="flatpak deb arch"

# Determine version and package types
if [[ $# -eq 0 ]]; then
    # No arguments: use version from meson and all packages
    VERSION=$("$SCRIPTS_DIR/get_version.sh")
    PACKAGE_TYPES=$DEFAULT_PACKAGES
elif [[ $# -eq 1 ]]; then
    # One argument: could be version or package type
    if [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        # It's a version
        VERSION="$1"
        PACKAGE_TYPES=$DEFAULT_PACKAGES
    else
        # It's a package type
        VERSION=$("$SCRIPTS_DIR/get_version.sh")
        PACKAGE_TYPES="$1"
    fi
else
    # Two or more arguments: first is version, rest are package types
    VERSION="$1"
    shift
    PACKAGE_TYPES="$*"
fi

echo "Building SOFL version $VERSION"
echo "Package types: $PACKAGE_TYPES"
echo "Output directory: $BUILD_DIR"

# Create build directory
mkdir -p "$BUILD_DIR"

# Update version in all files
echo "Updating version to $VERSION..."
"$SCRIPTS_DIR/update_version.sh" "$VERSION"

# Function to build specific package type
build_package() {
    local package_type=$1
    echo "=========================================="
    echo "Building $package_type package..."

    case $package_type in
        flatpak)
            if command -v flatpak-builder &> /dev/null; then
                cd "$PROJECT_DIR/packaging/flatpak"
                ./build.sh "$VERSION" "$BUILD_DIR"
            else
                echo "Warning: flatpak-builder not found, skipping flatpak build"
            fi
            ;;
        deb)
            echo "Checking Debian build dependencies..."
            # Dependencies will be installed by the debian build.sh script
            cd "$PROJECT_DIR/packaging/debian"
            ./build.sh "$VERSION" "$BUILD_DIR"
            ;;
        arch)
            echo "Building Arch Linux package..."
            # Dependencies will be installed by the arch build.sh script
            cd "$PROJECT_DIR/packaging/arch"
            ./build.sh "$VERSION" "$BUILD_DIR"
            ;;
        *)
            echo "Warning: Unknown package type '$package_type'"
            ;;
    esac

    cd "$PROJECT_DIR"
    echo "$package_type package build completed"
}

# Build each package type
for package_type in $PACKAGE_TYPES; do
    build_package "$package_type"
done

echo "=========================================="
echo "All builds completed!"
echo "Version: $VERSION"
echo "Package types built: $PACKAGE_TYPES"
echo "Output directory: $BUILD_DIR"

# List created files in dist directory
echo "Created packages in $BUILD_DIR:"
if [ -d "$BUILD_DIR" ]; then
    ls -la "$BUILD_DIR" | grep -E "\.(deb|flatpak|pkg\.tar\.zst|tar\.gz)$" || echo "No packages found in $BUILD_DIR"
else
    echo "Build directory $BUILD_DIR not found"
fi
