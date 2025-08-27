"""Utilities package exports for sofl.utils.

Provide helper functions that are convenient to access from the package
level (e.g. `sofl.utils.get_umu_proton_path`).
"""

from __future__ import annotations

import os
from typing import Optional


def get_umu_proton_path(proton_version: Optional[str]) -> str:
    """Return a reasonable Proton executable path for UMU launcher.

    This returns the standard Steam compatibilitytools.d proton wrapper
    path under the current user's home directory. If `proton_version` is
    falsy, an empty string is returned.
    """
    if not proton_version:
        return ""

    home = os.path.expanduser("~")
    return os.path.join(
        home,
        ".local",
        "share",
        "Steam",
        "compatibilitytools.d",
        proton_version,
        "proton",
    )


__all__ = ["get_umu_proton_path"]
