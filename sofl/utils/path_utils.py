"""Utility helpers for handling executable paths."""

from pathlib import Path
import shlex
from typing import Any


def normalize_executable_path(executable_str) -> Path:
    """Return a Path object for the given executable string, handling quotes safely.

    Strategy:
    - Try to treat the string as a literal path (strip surrounding quotes first).
    - If the literal path exists, return it.
    - Otherwise, try to parse using shlex.split to respect quoted tokens.
    - Fallback to stripping quotes and taking the first whitespace-separated token.
    """
    if not executable_str:
        return Path("")
    # Accept either a string or a Path object
    if isinstance(executable_str, Path):
        s = str(executable_str)
    else:
        s = str(executable_str).strip()
    # Remove surrounding quotes if present
    if (s.startswith('"') and s.endswith('"')) or (
        s.startswith("'") and s.endswith("'")
    ):
        s = s[1:-1]

    try:
        p = Path(s)
        if p.exists():
            return p
    except Exception:
        pass

    try:
        tokens = shlex.split(executable_str)
        if tokens:
            return Path(tokens[0])
    except Exception:
        pass

    cleaned = executable_str.replace('"', "").replace("'", "").strip()
    if not cleaned:
        return Path("")
    return Path(cleaned.split()[0])
