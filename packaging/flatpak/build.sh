#!/bin/bash

# Flatpak Build Script for SOFL
# Usage: ./build.sh [version] [output_dir] [install]

set -euo pipefail

PROJECT_NAME="org.badkiko.sofl"
REPO_NAME="sofl-repo"
VERSION=${1:-"0.0.3"}
OUTPUT_DIR=${2:-"."}
# Branch to be used for the repository commits and bundle; can be overridden via FLATPAK_BRANCH env var
BRANCH="${FLATPAK_BRANCH:-stable}"

echo "Building Flatpak package for $PROJECT_NAME version $VERSION..."

# Check if flatpak and flatpak-builder are installed
if ! command -v flatpak &> /dev/null; then
    echo "Installing flatpak..."
    sudo apt update
    sudo apt install -y flatpak
fi

if ! command -v flatpak-builder &> /dev/null; then
    echo "Installing flatpak-builder..."
    sudo apt install -y flatpak-builder
fi

# Initialize flatpak user installation (ensure flathub exists for user)
echo "Ensuring flathub remote exists for user..."
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Add Flathub remote if not exists
echo "Setting up Flathub remote..."
if ! flatpak remotes --user | grep -q flathub; then
    echo "Adding Flathub remote..."
    flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo --if-not-exists
else
    echo "Flathub remote already exists"
fi

# Update remotes to ensure we have latest info
flatpak update --appstream --user || true

# Check and install required runtimes
echo "Checking and installing required runtimes..."

# Check org.gnome.Platform
if ! flatpak list --user | grep -q "org.gnome.Platform//48"; then
    echo "Installing org.gnome.Platform//48..."
    flatpak install --user flathub org.gnome.Platform//48 -y --noninteractive
else
    echo "org.gnome.Platform//48 already installed"
fi

# Check org.gnome.Sdk
if ! flatpak list --user | grep -q "org.gnome.Sdk//48"; then
    echo "Installing org.gnome.Sdk//48..."
    flatpak install --user flathub org.gnome.Sdk//48 -y --noninteractive
else
    echo "org.gnome.Sdk//48 already installed"
fi

# blueprint-compiler is now available from the host system via flatpak manifest

# Clean previous build
rm -rf build-dir flatpak-build $REPO_NAME


# Build the flatpak with better error handling
echo "Building Flatpak (branch: $BRANCH)..."
if ! flatpak-builder --force-clean --user --repo=$REPO_NAME --default-branch=$BRANCH --install-deps-from=flathub --disable-rofiles-fuse flatpak-build $PROJECT_NAME.yml; then
    echo "Error: Flatpak build failed"
    echo "Trying with additional flags..."
    flatpak-builder --force-clean --user --repo=$REPO_NAME --default-branch=$BRANCH --install-deps-from=flathub --disable-rofiles-fuse --ccache flatpak-build $PROJECT_NAME.yml
fi

# Create bundle
echo "Creating bundle..."
flatpak build-bundle $REPO_NAME $PROJECT_NAME.flatpak $PROJECT_NAME $BRANCH

echo "Flatpak bundle created: $PROJECT_NAME.flatpak"

# Move bundle to output directory
if [ "$OUTPUT_DIR" != "." ]; then
    mkdir -p "$OUTPUT_DIR"
    mv "$PROJECT_NAME.flatpak" "$OUTPUT_DIR/"
    echo "Bundle moved to: $OUTPUT_DIR/$PROJECT_NAME.flatpak"
fi

# Optional: Install locally for testing (check third argument)
if [ "${3:-}" == "install" ]; then
    echo "Installing locally..."
    flatpak-builder --install --user flatpak-build $PROJECT_NAME.yml
fi

echo "Build completed successfully!"
