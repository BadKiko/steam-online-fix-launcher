#!/bin/bash

# Update version in all packaging files
# Usage: ./update_version.sh [new_version]

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Get current version from meson.build
CURRENT_VERSION=$("$SCRIPTS_DIR/get_version.sh")

# Use provided version or current version
NEW_VERSION=${1:-$CURRENT_VERSION}

echo "Updating version to: $NEW_VERSION"

# Update meson.build - only project version, not meson_version or dependencies
# First, backup the original file
cp "$PROJECT_DIR/meson.build" "$PROJECT_DIR/meson.build.backup"

# Replace only the project version line (first version line after project()
sed -i '1,/^)/ {
    /^  version: / {
        s/version: '\''[^'\'']+'\''/version: '\'''"$NEW_VERSION"''\''/
        b done
    }
    :done
}' "$PROJECT_DIR/meson.build"


# Update Debian control
DEBIAN_CONTROL="$PROJECT_DIR/packaging/debian/DEBIAN/control"
if [ -f "$DEBIAN_CONTROL" ]; then
    sed -i "s/Version: .*/Version: $NEW_VERSION/" "$DEBIAN_CONTROL"
fi

# Update Arch PKGBUILD
ARCH_PKGBUILD="$PROJECT_DIR/packaging/arch/PKGBUILD"
if [ -f "$ARCH_PKGBUILD" ]; then
    sed -i "s/pkgver=.*/pkgver=$NEW_VERSION/" "$ARCH_PKGBUILD"
fi

# Update metainfo file
METAINFO_FILE="$PROJECT_DIR/data/org.badkiko.sofl.metainfo.xml.in"
if [ -f "$METAINFO_FILE" ]; then
    # Update the first release entry
    sed -i "s/<release version=\"[0-9]\+\.[0-9]\+\.[0-9]\+\"/<release version=\"$NEW_VERSION\"/" "$METAINFO_FILE"
fi

echo "Version updated to $NEW_VERSION in all packaging files"
