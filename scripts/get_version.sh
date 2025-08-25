#!/bin/bash

# Get version from meson.build
# Usage: ./get_version.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MESON_FILE="$PROJECT_DIR/meson.build"

if [ ! -f "$MESON_FILE" ]; then
    echo "Error: meson.build not found at $MESON_FILE"
    exit 1
fi

# Extract version from meson.build
VERSION=$(grep -o "version: '[^']*'" "$MESON_FILE" | head -n1 | sed "s/version: '\([^']*\)'/\1/")

if [ -z "$VERSION" ]; then
    echo "Error: Could not extract version from meson.build"
    exit 1
fi

echo "$VERSION"
