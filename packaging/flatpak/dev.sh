#!/usr/bin/env bash

# SOFL Flatpak development helper
# Usage: ./dev.sh [command] [options]
#
# Commands:
#   build      - Build flatpak package (creates .flatpak bundle)
#   install    - Install built package
#   run        - Run installed package
#   clean      - Remove installed package
#   full-clean - Remove all build artifacts and caches
#   dev        - Full development cycle: build + install + run
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR/flatpak-build"
CACHE_DIR="$SCRIPT_DIR/.flatpak-builder"
REPO_DIR="$SCRIPT_DIR/sofl-repo"

APP_ID="org.badkiko.sofl"
VERSION="0.0.3.3a"
DIST_FILE="$DIST_DIR/$APP_ID.flatpak"

do_build() {
    echo "Building Flatpak package..."
    mkdir -p "$DIST_DIR"
    ./build.sh "$VERSION" "$DIST_DIR" fast
}

do_install() {
    echo "Installing Flatpak package..."
    if [ -f "$DIST_FILE" ]; then
        flatpak remove "$APP_ID" -y 2>/dev/null || true
        flatpak install "$DIST_FILE" --user -y
    else
        echo "Package file not found: $DIST_FILE"
        echo "Installing from build directory..."
        flatpak remove "$APP_ID" -y 2>/dev/null || true
        flatpak-builder --install --user "$BUILD_DIR" org.badkiko.sofl.yml
    fi
}

do_run() {
    echo "Running $APP_ID..."
    flatpak run "$APP_ID"
}

do_clean() {
    echo "Removing installed package..."
    flatpak remove "$APP_ID" -y 2>/dev/null || echo "Package not installed"
}

do_full_clean() {
    echo "Performing full clean of all build artifacts..."

    # Remove installed package
    do_clean

    # Remove build artifacts
    echo "Removing build directory..."
    rm -rf "$BUILD_DIR"

    echo "Removing flatpak cache..."
    rm -rf "$CACHE_DIR"

    echo "Removing repository..."
    rm -rf "$REPO_DIR"

    echo "Removing dist files..."
    rm -f "$DIST_FILE"

    # Remove meson build artifacts from parent directory
    echo "Removing meson build artifacts..."
    rm -rf "$PROJECT_DIR/builddir"
    rm -rf "$PROJECT_DIR/.local"

    echo "Full clean completed!"
}

do_dev() {
    do_build
    do_install
    do_run
}

# Main command handling
CMD="${1:-dev}"
shift || true

case "$CMD" in
    build)
        do_build
        ;;
    install)
        do_install
        ;;
    run)
        do_run
        ;;
    clean)
        do_clean
        ;;
    full-clean)
        do_full_clean
        ;;
    dev)
        do_dev
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Available commands: build, install, run, clean, full-clean, dev"
        exit 1
        ;;
esac 