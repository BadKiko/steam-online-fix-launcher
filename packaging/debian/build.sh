#!/bin/bash

# Debian Package Build Script for SOFL
# Usage: ./build.sh [version]

set -e

VERSION=${1:-"0.0.3"}
PACKAGE_NAME="sofl"
BUILD_DIR="deb-build"
DEBIAN_DIR="packaging/debian"

echo "Building Debian package for $PACKAGE_NAME version $VERSION..."

# Check if required tools are installed
if ! command -v dpkg-deb &> /dev/null; then
    echo "Error: dpkg-deb is not installed."
    echo "Install it with: sudo apt install dpkg"
    exit 1
fi

# Clean previous build
rm -rf "$BUILD_DIR" *.deb

# Update version in control file
sed -i "s/Version: .*/Version: $VERSION/" "$DEBIAN_DIR/DEBIAN/control"

# Build the application using meson
echo "Building application with Meson..."
cd /home/kiko/Work/steam-online-fix-launcher
meson setup build-dir --prefix=/usr --buildtype=release -Dprofile=release -Dtiff_compression=webp
meson compile -C build-dir
meson install --destdir="$BUILD_DIR" -C build-dir

# Copy debian control files
mkdir -p "$BUILD_DIR/DEBIAN"
cp "$DEBIAN_DIR/DEBIAN/control" "$BUILD_DIR/DEBIAN/"

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

echo "Debian package created: ${PACKAGE_NAME}_${VERSION}_all.deb"

# Optional: Check package with lintian
if command -v lintian &> /dev/null; then
    echo "Checking package with lintian..."
    lintian "${PACKAGE_NAME}_${VERSION}_all.deb" || true
fi

echo "Build completed successfully!"
