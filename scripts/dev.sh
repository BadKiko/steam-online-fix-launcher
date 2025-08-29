#!/usr/bin/env bash

# Local development helper for SOFL
# - Sets up Meson in builddir with local prefix (.local)
# - Builds, installs, exports env vars, and runs the app

set -euo pipefail

# Get the absolute path of the script directory, regardless of how it's called
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/builddir"
PREFIX_DIR="$PROJECT_DIR/.local"
SCHEMAS_DIR="$PREFIX_DIR/share/glib-2.0/schemas"
DATA_SHARE="$PREFIX_DIR/share"

print_usage() {
    cat <<EOF
SOFL dev script

Usage:
  $(basename "$0") [command] [-- ARGS]

Commands:
  setup       Configure Meson in builddir with local prefix
  build       Build via Meson
  install     Install into .local prefix
  deps        Create .venv and install Python runtime deps (requests, pillow, rarfile, vdf)
  smart       Automatically handle setup+build+install+run with smart checks (recommended)
  rebuild-run Remove builddir, then setup+build+install+run (fast clean+run)
  run         Run app with correct env vars (auto-setup/build/install if needed)
  shell       Start an interactive shell with env vars set
  clean       Remove builddir and .local
  all         setup + build + install + run (default)
  help        Show this help

Examples:
  # Smart full cycle (recommended)
  ./scripts/dev.sh smart

  # Full cycle
  ./scripts/dev.sh

  # Just run (auto-setup/build/install if needed)
  ./scripts/dev.sh run

  # Run with app arguments
  ./scripts/dev.sh run -- --search "doom"

  # Rebuild and run
  ./scripts/dev.sh rebuild-run
EOF
}

require_bin() {
    local bin="$1"
    command -v "$bin" >/dev/null 2>&1 || {
        echo "Error: '$bin' is required but not installed." >&2
        exit 1
    }
}

do_setup() {
    require_bin meson
    require_bin ninja || true
    require_bin blueprint-compiler

    mkdir -p "$BUILD_DIR"

    if [ ! -f "$BUILD_DIR/meson-private/coredata.dat" ]; then
        echo "[dev] meson setup -> $BUILD_DIR (prefix=$PREFIX_DIR)"
        # Change to project directory for meson setup, then return
        local original_dir
        original_dir="$(pwd)"
        cd "$PROJECT_DIR"
        meson setup "$BUILD_DIR" \
            --prefix="$PREFIX_DIR" \
            -Dprofile=development
        cd "$original_dir"
    else
        echo "[dev] meson already configured in $BUILD_DIR"
    fi
}

check_build_needed() {
    # Check if build is needed by comparing timestamps
    local meson_stamp="$BUILD_DIR/meson-private/coredata.dat"
    local source_stamp="$PROJECT_DIR/meson.build"

    if [ ! -f "$meson_stamp" ]; then
        return 0  # Need build - no build dir
    fi

    if [ "$source_stamp" -nt "$meson_stamp" ]; then
        return 0  # Need build - meson.build is newer
    fi

    # Check if any source files are newer than build files
    local newest_source
    newest_source=$(find "$PROJECT_DIR" -name "*.py" -o -name "*.blp" -o -name "*.xml" -o -name "*.desktop" \
        | head -n 1 | xargs ls -t | head -n 1)

    local build_stamp="$BUILD_DIR/build.ninja"
    if [ -f "$build_stamp" ] && [ "$newest_source" -nt "$build_stamp" ]; then
        return 0  # Need build - source files are newer
    fi

    return 1  # No build needed
}

check_install_needed() {
    # Check if install is needed
    local app_bin="$PREFIX_DIR/bin/sofl"
    local build_stamp="$BUILD_DIR/build.ninja"

    if [ ! -f "$app_bin" ]; then
        return 0  # Need install - app not installed
    fi

    if [ "$build_stamp" -nt "$app_bin" ]; then
        return 0  # Need install - build is newer than installed app
    fi

    return 1  # No install needed
}

do_build() {
    echo "[dev] meson compile"
    # Change to project directory for meson compile
    local original_dir
    original_dir="$(pwd)"
    cd "$PROJECT_DIR"
    meson compile -C "$BUILD_DIR"
    cd "$original_dir"
}

do_install() {
    echo "[dev] meson install -> $PREFIX_DIR"
    # Change to project directory for meson install
    local original_dir
    original_dir="$(pwd)"
    cd "$PROJECT_DIR"
    meson install -C "$BUILD_DIR"
    cd "$original_dir"

    # Ensure schemas are compiled for local prefix
    if command -v glib-compile-schemas >/dev/null 2>&1; then
        if [ -d "$SCHEMAS_DIR" ]; then
            echo "[dev] glib-compile-schemas $SCHEMAS_DIR"
            glib-compile-schemas "$SCHEMAS_DIR"
        fi
    fi
}

do_deps() {
    require_bin python3
    if [ ! -d "$PROJECT_DIR/.venv" ]; then
        echo "[dev] creating venv: $PROJECT_DIR/.venv"
        python3 -m venv "$PROJECT_DIR/.venv"
    fi
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
    python -m pip install -U pip setuptools wheel
    python -m pip install requests pillow rarfile vdf
}

export_env() {
    # Export runtime env so the app sees local schemas/resources
    export GSETTINGS_SCHEMA_DIR="$SCHEMAS_DIR"
    # Prepend our .local/share to XDG_DATA_DIRS
    if [ -n "${XDG_DATA_DIRS:-}" ]; then
        export XDG_DATA_DIRS="$DATA_SHARE:$XDG_DATA_DIRS"
    else
        export XDG_DATA_DIRS="$DATA_SHARE:/usr/local/share:/usr/share"
    fi

    # Ensure Python can import modules installed into local prefix
    local pyver
    pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local site_pkgs="$PREFIX_DIR/lib/python${pyver}/site-packages"
    if [ -d "$site_pkgs" ]; then
        if [ -n "${PYTHONPATH:-}" ]; then
            export PYTHONPATH="$site_pkgs:$PYTHONPATH"
        else
            export PYTHONPATH="$site_pkgs"
        fi
    fi

    # Also include venv site-packages if present so wrapper python can find them
    if [ -d "$PROJECT_DIR/.venv" ]; then
        local venv_site
        venv_site="$PROJECT_DIR/.venv/lib/python${pyver}/site-packages"
        if [ -d "$venv_site" ]; then
            if [ -n "${PYTHONPATH:-}" ]; then
                export PYTHONPATH="$venv_site:$PYTHONPATH"
            else
                export PYTHONPATH="$venv_site"
            fi
        fi
    fi
}

do_run() {
    export_env

    # Auto-setup if needed
    if [ ! -f "$BUILD_DIR/meson-private/coredata.dat" ]; then
        echo "[dev] Build directory not configured, running setup..."
        do_setup
    fi

    # Auto-build if needed
    if check_build_needed; then
        echo "[dev] Build is outdated or missing, running build..."
        do_build
    fi

    # Auto-install if needed
    if check_install_needed; then
        echo "[dev] App not installed or outdated, running install..."
        do_install
    fi

    local app_bin="$PREFIX_DIR/bin/sofl"
    echo "[dev] running: $app_bin ${*:-}"
    "$app_bin" "$@"
}

do_shell() {
    export_env
    echo "[dev] starting shell with dev environment"
    echo "    GSETTINGS_SCHEMA_DIR=$GSETTINGS_SCHEMA_DIR"
    echo "    XDG_DATA_DIRS=$XDG_DATA_DIRS"
    ${SHELL:-/bin/bash}
}

do_clean() {
    echo "[dev] cleaning builddir and .local"
    rm -rf "$BUILD_DIR" "$PREFIX_DIR"
}

do_rebuild_run() {
    echo "[dev] rebuild-run: cleaning builddir and redoing full cycle"
    rm -rf "$BUILD_DIR"
    do_setup
    do_build
    do_install
    do_run "$@"
}

do_smart() {
    echo "[dev] Smart mode - automatically handling all steps..."

    # Auto-setup if needed
    if [ ! -f "$BUILD_DIR/meson-private/coredata.dat" ]; then
        echo "[dev] Build directory not configured, running setup..."
        do_setup
    fi

    # Auto-build if needed
    if check_build_needed; then
        echo "[dev] Build is outdated or missing, running build..."
        do_build
    else
        echo "[dev] Build is up to date"
    fi

    # Auto-install if needed
    if check_install_needed; then
        echo "[dev] App not installed or outdated, running install..."
        do_install
    else
        echo "[dev] App is up to date"
    fi

    do_run "$@"
}

cmd="${1:-all}"
shift || true

case "$cmd" in
    help|-h|--help)
        print_usage
        ;;
    setup)
        do_setup
        ;;
    build)
        do_build
        ;;
    install)
        do_install
        ;;
    deps)
        do_deps
        ;;
    smart)
        do_smart "$@"
        ;;
    run)
        do_run "$@"
        ;;
    rebuild-run)
        do_rebuild_run "$@"
        ;;
    shell)
        do_shell
        ;;
    clean)
        do_clean
        ;;
    all|*)
        do_setup
        do_build
        do_install
        do_run "$@"
        ;;
esac


