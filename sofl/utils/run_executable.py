# run_executable.py
#
# Copyright 2023 badkiko
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

import logging
import os
import subprocess
from shlex import quote

from sofl.utils.path_utils import normalize_executable_path

from sofl import shared


def run_executable(executable) -> None:
    """Safely launches executable file"""
    import shlex

    executable_path = normalize_executable_path(executable)

    if not executable_path:
        logging.error("Invalid executable path: %s", executable)
        return

    # If executable is a string with arguments, safely parse it
    if isinstance(executable, str) and " " in str(executable):
        try:
            # Try to parse as command with arguments
            cmd_args = shlex.split(str(executable))
            if len(cmd_args) > 1:
                # There are arguments - use them
                logging.info("Launching command with args: %s", cmd_args)
                subprocess.Popen(
                    cmd_args,
                    cwd=shared.home,
                    shell=False,
                    start_new_session=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,  # type: ignore
                )
                return
        except ValueError:
            # If parsing failed, continue with path
            pass

    # Launch executable file without arguments only
    logging.info("Launching `%s`", executable_path)
    subprocess.Popen(
        str(executable_path),
        cwd=shared.home,
        shell=False,
        start_new_session=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,  # type: ignore
    )
