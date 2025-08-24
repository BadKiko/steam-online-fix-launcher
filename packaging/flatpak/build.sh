#!/bin/bash

# Flatpak Build Script for SOFL
# Usage: ./build.sh [version]

set -e

PROJECT_NAME="org.badkiko.sofl"
REPO_NAME="sofl-repo"
VERSION=${1:-"0.0.3"}

echo "Building Flatpak package for $PROJECT_NAME version $VERSION..."

# Check if flatpak-builder is installed
if ! command -v flatpak-builder &> /dev/null; then
    echo "Error: flatpak-builder is not installed."
    echo "Install it with: sudo apt install flatpak-builder"
    exit 1
fi

# Clean previous build
rm -rf build-dir flatpak-build $REPO_NAME

# Update manifest with current version if needed
if [ "$1" ]; then
    sed -i "s/tag: v[0-9]\+\.[0-9]\+\.[0-9]\+/tag: v$VERSION/g" "$PROJECT_NAME.yml"
    sed -i "s/commit: HEAD/commit: HEAD/g" "$PROJECT_NAME.yml"
fi

# Build the flatpak
echo "Building Flatpak..."
flatpak-builder --repo=$REPO_NAME flatpak-build $PROJECT_NAME.yml

# Create bundle
echo "Creating bundle..."
flatpak build-bundle $REPO_NAME $PROJECT_NAME.flatpak $PROJECT_NAME

echo "Flatpak bundle created: $PROJECT_NAME.flatpak"

# Optional: Install locally for testing
if [ "$2" == "install" ]; then
    echo "Installing locally..."
    flatpak-builder --install --user flatpak-build $PROJECT_NAME.yml
fi

echo "Build completed successfully!"
