#!/bin/bash

# Debian Package Build Script for SOFL
# Usage: ./build.sh [version]

set -e

VERSION=${1:-"0.0.3"}
PACKAGE_NAME="sofl"
BUILD_DIR="deb-build"
DEBIAN_DIR="packaging/debian"
# OUTPUT_DIR is normalized to absolute path later; default is project dist directory
OUTPUT_DIR=${2:-"dist"}

echo "Building Debian package for $PACKAGE_NAME version $VERSION..."

# Install required dependencies
echo "Installing required dependencies..."
sudo apt update

# Check and install required tools
REQUIRED_TOOLS="dpkg-deb meson ninja fakeroot"
for tool in $REQUIRED_TOOLS; do
    if ! command -v $tool &> /dev/null; then
        echo "Installing $tool..."
        pkg="$tool"
        [ "$tool" = "ninja" ] && pkg="ninja-build"
        sudo apt install -y "$pkg"
    fi
done

# Install build dependencies
BUILD_DEPS="python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 python3-requests python3-pillow python3-cairo python3-psutil python3-xdg libgtk-4-dev libadwaita-1-dev desktop-file-utils"
echo "Installing build dependencies..."
sudo apt install -y $BUILD_DEPS

# Get project root directory (parent of packaging directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Normalize OUTPUT_DIR to absolute path
if [[ "$OUTPUT_DIR" != /* ]]; then
    OUTPUT_DIR="$PROJECT_ROOT/$OUTPUT_DIR"
fi
OUTPUT_DIR="$(mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)"

# Clean previous build
rm -rf "$BUILD_DIR" *.deb

# Build the application using meson
echo "Building application with Meson..."
cd "$PROJECT_ROOT"

# Create build directory if it doesn't exist
mkdir -p build-dir

meson setup build-dir --prefix=/usr --buildtype=release -Dprofile=release -Dtiff_compression=webp
meson compile -C build-dir
meson install --destdir="$BUILD_DIR" -C build-dir

# Copy debian control files
mkdir -p "$BUILD_DIR/DEBIAN"
cp "$DEBIAN_DIR/DEBIAN/control" "$BUILD_DIR/DEBIAN/"

# Update version in control file
sed -i "s/Version: .*/Version: $VERSION/" "$BUILD_DIR/DEBIAN/control"

# Create postinst script for desktop database update
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "configure" ]; then
    # Update desktop database
    update-desktop-database /usr/share/applications 2>/dev/null || true

    # Update icon cache
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true

    # Compile glib schemas
    glib-compile-schemas /usr/share/glib-2.0/schemas 2>/dev/null || true
fi

exit 0
EOF

chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# Create prerm script for cleanup
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "remove" ] || [ "$1" = "upgrade" ]; then
    # Update desktop database
    update-desktop-database /usr/share/applications 2>/dev/null || true

    # Update icon cache
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

exit 0
EOF

chmod 755 "$BUILD_DIR/DEBIAN/prerm"

# Build the package
echo "Building Debian package..."
dpkg-deb --build "$BUILD_DIR" "${PACKAGE_NAME}_${VERSION}_all.deb"

echo "Debian package created: $(pwd)/${PACKAGE_NAME}_${VERSION}_all.deb"

# Move package to absolute OUTPUT_DIR (already absolute)
mv "${PACKAGE_NAME}_${VERSION}_all.deb" "$OUTPUT_DIR/"
echo "Package moved to: $OUTPUT_DIR/${PACKAGE_NAME}_${VERSION}_all.deb"

# Optional: Check package with lintian
if command -v lintian &> /dev/null; then
    PACKAGE_PATH="${OUTPUT_DIR}/${PACKAGE_NAME}_${VERSION}_all.deb"
    echo "Checking package with lintian..."
    lintian "$PACKAGE_PATH" || true
fi

echo "Build completed successfully!"
