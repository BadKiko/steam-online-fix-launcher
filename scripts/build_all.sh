#!/bin/bash

# Build all package types for SOFL
# Usage: ./build_all.sh [version] [package_types]
# Example: ./build_all.sh 0.0.3 "flatpak deb arch"

set -e

PROJECT_DIR="/home/kiko/Work/steam-online-fix-launcher"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Default package types
DEFAULT_PACKAGES="flatpak deb arch"
VERSION=${1:-$("$SCRIPTS_DIR/get_version.sh")}
PACKAGE_TYPES=${2:-$DEFAULT_PACKAGES}

echo "Building SOFL version $VERSION"
echo "Package types: $PACKAGE_TYPES"

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
                ./build.sh "$VERSION"
            else
                echo "Warning: flatpak-builder not found, skipping flatpak build"
            fi
            ;;
        deb)
            if command -v dpkg-deb &> /dev/null; then
                cd "$PROJECT_DIR/packaging/debian"
                ./build.sh "$VERSION"
            else
                echo "Warning: dpkg-deb not found, skipping deb build"
            fi
            ;;
        arch)
            if command -v makepkg &> /dev/null; then
                cd "$PROJECT_DIR/packaging/arch"
                ./build.sh "$VERSION"
            else
                echo "Warning: makepkg not found, building source package only"
                cd "$PROJECT_DIR/packaging/arch"
                ./build.sh "$VERSION"
            fi
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

# List created files
echo "Created packages:"
find . -maxdepth 2 -name "*.deb" -o -name "*.flatpak" -o -name "*.pkg.tar.zst" -o -name "*.tar.gz" | sort
