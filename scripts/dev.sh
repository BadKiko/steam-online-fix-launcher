#!/usr/bin/env bash

# Local development helper for SOFL
# - Sets up Meson in builddir with local prefix (.local)
# - Builds, installs, exports env vars, and runs the app

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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
  rebuild-run Remove builddir, then setup+build+install+run (fast clean+run)
  run         Run app with correct env vars
  shell       Start an interactive shell with env vars set
  clean       Remove builddir and .local
  all         setup + build + install + run (default)
  help        Show this help

Examples:
  # Full cycle
  ./scripts/dev.sh

  # Run with app arguments
  ./scripts/dev.sh run -- --search "doom"

  # Rebuild and run
  ./scripts/dev.sh build && ./scripts/dev.sh install && ./scripts/dev.sh run
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
        meson setup "$BUILD_DIR" \
            --prefix="$PREFIX_DIR" \
            -Dprofile=development
    else
        echo "[dev] meson already configured in $BUILD_DIR"
    fi
}

do_build() {
    echo "[dev] meson compile"
    meson compile -C "$BUILD_DIR"
}

do_install() {
    echo "[dev] meson install -> $PREFIX_DIR"
    meson install -C "$BUILD_DIR"

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
    local app_bin="$PREFIX_DIR/bin/sofl"
    if [ ! -x "$app_bin" ]; then
        echo "[dev] App not installed yet, running install step..."
        do_install
    fi
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


