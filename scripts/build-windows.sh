#!/usr/bin/env bash
# Build SOFL for Windows. Run inside an MSYS2 UCRT64 shell from the repo root.
set -euo pipefail

pacman -S --noconfirm --needed \
  mingw-w64-ucrt-x86_64-{gtk4,libadwaita,python-gobject,python-requests,python-pillow,python-yaml,python-pip,blueprint-compiler,meson,ninja,desktop-file-utils,librsvg}
pip install --break-system-packages vdf rarfile

export PYTHONUTF8=1  # blueprint-compiler crashes reading UTF-8 files under cp1252
export 'ProgramFiles(x86)=C:\Program Files (x86)'  # meson crashes looking for vswhere without it

meson setup _build --prefix="$HOME/sofl-install" -Dprofile=development --reconfigure 2>/dev/null \
  || meson setup _build --prefix="$HOME/sofl-install" -Dprofile=development
meson install -C _build
echo "Built. Run scripts\\run-windows.bat"
