# flatpak.py
#
# Copyright 2025 badkiko
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import re
import logging
import subprocess
from gi.repository import GLib

# Constants
FLATPAK_PATH_PATTERN = r"/run/user/\d+/doc/"

# Logger setup
logger = logging.getLogger(__name__)

def log_message(message, level=logging.INFO):
    """Log message with designated level
    
    Args:
        message: Message text
        level: Log level (from logging module)
    """
    logger.log(level, message)
    print(f"[SOFL] {message}")

def is_flatpak_path(path: str) -> bool:
    """Checks if the path is a Flatpak path
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if the path is a Flatpak path, False otherwise
    """
    return bool(re.search(FLATPAK_PATH_PATTERN, path))

def copy_flatpak_file(path: str) -> str:
    """Copies a file from Flatpak to an accessible directory
    
    Args:
        path: Path to the file in Flatpak
        
    Returns:
        str: Path to the copied file or original path in case of error
    """
    try:
        # Create temporary directory if it doesn't exist yet
        temp_dir = os.path.join(GLib.get_user_cache_dir(), "sofl-temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Get filename from path
        filename = os.path.basename(path)
        new_path = os.path.join(temp_dir, filename)
        
        log_message(f"Copying file from Flatpak to: {new_path}")
        
        try:
            log_message("Trying to copy via flatpak-spawn...")
            # For accessing host files through Flatpak
            result = subprocess.run(
                ["flatpak-spawn", "--host", "cp", path, new_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                log_message("flatpak-spawn: File successfully copied")
                return new_path
            else:
                log_message(f"flatpak-spawn: Copy error: {result.stderr}", logging.ERROR)
        except Exception as e:
            log_message(f"flatpak-spawn: Error: {str(e)}", logging.ERROR)
        
        # All methods failed, return original path
        log_message("All copy methods failed. Proceeding with original file.", logging.WARNING)
        return path
    except Exception as e:
        log_message(f"General error when copying file: {str(e)}", logging.ERROR)
        return path 