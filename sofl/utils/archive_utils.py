# archive_utils.py
#
# Copyright 2023-2024 badkiko
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

import subprocess
import shutil
import rarfile
import logging
import re
from typing import Optional


class ArchiveVerifier:
    """Utilities for checking and verifying archives"""

    ONLINE_FIX_PASSWORD = "online-fix.me"

    @staticmethod
    def verify_rar_password_quick(path: str) -> bool:
        """Quick RAR archive password verification via unrar"""
        try:
            unrar_path = ArchiveVerifier._get_unrar_path()
            if not unrar_path:
                return False

            result = subprocess.run(
                [unrar_path, "t", "-p" + ArchiveVerifier.ONLINE_FIX_PASSWORD, "-idp", path],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            if result.returncode == 0:
                logging.info("Archive passed verification via unrar")
                return True
            else:
                logging.warning(
                    f"Archive failed verification via unrar (exit code {result.returncode}): {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            logging.warning("Archive verification took too long, cancelling")
            return False
        except Exception as e:
            logging.error(f"Error during verification via unrar: {str(e)}")
            return False

    @staticmethod
    def verify_rar_password_fallback(path: str) -> bool:
        """RAR archive password verification via rarfile (fallback)"""
        try:
            with rarfile.RarFile(path) as rf:
                rf.setpassword(ArchiveVerifier.ONLINE_FIX_PASSWORD)
                info_list = rf.infolist()

                if not info_list:
                    logging.warning("Archive is empty")
                    return False

                # Check password by trying to read the first file
                try:
                    with rf.open(info_list[0]) as f:
                        f.read(1)  # Read at least 1 byte
                    logging.info("Archive verified successfully via rarfile")
                    return True
                except rarfile.PasswordRequired:
                    logging.warning("Archive requires different password")
                    return False
                except Exception as e:
                    logging.error(f"Failed to read archive content: {str(e)}")
                    return False

        except rarfile.PasswordRequired:
            logging.warning("Archive is protected by a different password")
            return False
        except Exception as e:
            logging.error(f"Error during verification via rarfile: {str(e)}")
            return False

    @staticmethod
    def verify_archive_password(path: str) -> bool:
        """Verifies Online-Fix archive password"""
        if not path.lower().endswith(".rar"):
            return False

        # First try quick method via unrar
        if ArchiveVerifier.verify_rar_password_quick(path):
            return True

        # If not successful, use rarfile
        logging.info("Using rarfile fallback for archive verification")
        return ArchiveVerifier.verify_rar_password_fallback(path)

    @staticmethod
    def _get_unrar_path() -> Optional[str]:
        """Gets unrar path"""
        return rarfile.UNRAR_TOOL if rarfile.UNRAR_TOOL else shutil.which("unrar")

    @staticmethod
    def extract_game_title(filename: str) -> str:
        """Extracts game title from filename"""
        GAME_TITLE_REGEX = r"(^.*?)\.v"
        match = re.search(GAME_TITLE_REGEX, filename)
        if match:
            return match.group(1).replace(".", " ")
        return ""
