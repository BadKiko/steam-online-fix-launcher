# steam_launcher.py
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

import os
import subprocess
import logging
import shlex
import vdf
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sofl import shared


class SteamLauncher:
    """Utilities for launching games through Steam API"""

    @staticmethod
    def check_steam_running(in_flatpak: bool = False) -> bool:
        """Checks if Steam is running"""
        try:
            if in_flatpak:
                result = subprocess.run(
                    ["flatpak-spawn", "--host", "pidof", "steam"],
                    capture_output=True,
                    text=True,
                )
            else:
                result = subprocess.run(
                    ["pidof", "steam"], capture_output=True, text=True
                )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception as e:
            logging.error(f"[SOFL] Failed to check Steam status: {str(e)}")
            return False

    @staticmethod
    def get_host_home(in_flatpak: bool = False) -> str:
        """Gets host home directory"""
        if not in_flatpak:
            return os.path.expanduser("~")

        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "printenv", "HOME"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logging.error(f"[SOFL] Failed to get host home: {e}")

        return os.path.expanduser("~")

    @staticmethod
    def check_proton_exists(proton_version: str, steam_home: str, in_flatpak: bool = False) -> bool:
        """Checks Proton version existence"""
        proton_path = os.path.join(
            steam_home, "compatibilitytools.d", proton_version, "proton"
        )

        try:
            if in_flatpak:
                result = subprocess.run(
                    ["flatpak-spawn", "--host", "test", "-e", proton_path],
                    capture_output=True,
                )
                return result.returncode == 0
            else:
                return os.path.exists(proton_path)
        except Exception:
            return False

    @staticmethod
    def find_steam_runtime(steam_home: str, in_flatpak: bool = False) -> Optional[str]:
        """Finds Steam Runtime in Steam libraries"""
        library_folders_path = os.path.join(
            steam_home, ".steam/steam/steamapps/libraryfolders.vdf"
        )

        try:
            library_data = None
            if in_flatpak:
                try:
                    result = subprocess.run(
                        ["flatpak-spawn", "--host", "cat", library_folders_path],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        try:
                            library_data = vdf.loads(result.stdout)
                        except Exception:
                            library_data = vdf.load(StringIO(result.stdout))
                except Exception as e:
                    logging.debug(f"[SOFL] Could not read host libraryfolders.vdf: {e}")
            else:
                if os.path.exists(library_folders_path):
                    with open(library_folders_path, "r") as f:
                        library_data = vdf.load(f)

            # Look for SteamLinuxRuntime_sniper
            if library_data and "libraryfolders" in library_data:
                for folder_data in library_data["libraryfolders"].values():
                    if "apps" in folder_data and "1628350" in folder_data["apps"]:
                        runtime_path = os.path.join(
                            folder_data["path"],
                            "steamapps/common/SteamLinuxRuntime_sniper/run",
                        )
                        if SteamLauncher._check_file_exists(runtime_path, in_flatpak):
                            return runtime_path
        except Exception as e:
            logging.error(f"[SOFL] Error finding Steam Runtime: {str(e)}")

        return None

    @staticmethod
    def _check_file_exists(file_path: str, in_flatpak: bool = False) -> bool:
        """Checks file existence"""
        try:
            if in_flatpak:
                result = subprocess.run(
                    ["flatpak-spawn", "--host", "test", "-f", file_path],
                    capture_output=True,
                )
                return result.returncode == 0
            else:
                return os.path.isfile(file_path)
        except Exception:
            return False

    @staticmethod
    def prepare_environment(prefix_path: str, user_home: str) -> Dict[str, str]:
        """Prepares environment variables for launch"""
        dll_overrides = shared.schema.get_string("online-fix-dll-overrides")
        debug_mode = shared.schema.get_boolean("online-fix-debug-mode")

        # Base environment variables
        env = {
            "WINEDLLOVERRIDES": f"d3d11=n;d3d10=n;d3d10core=n;dxgi=n;openvr_api_dxvk=n;d3d12=n;d3d12core=n;d3d9=n;d3d8=n;{dll_overrides}",
            "WINEDEBUG": "+warn,+err,+trace" if debug_mode else "-all",
            "STEAM_COMPAT_DATA_PATH": prefix_path,
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": f"{user_home}/.steam/steam",
        }

        # Add Steam Overlay if enabled
        use_steam_overlay = shared.schema.get_boolean("online-fix-use-steam-overlay")
        if use_steam_overlay:
            existing_preload = env.get("LD_PRELOAD", "")
            new_preload_paths = f"{user_home}/.local/share/Steam/ubuntu12_32/gameoverlayrenderer.so:{user_home}/.local/share/Steam/ubuntu12_64/gameoverlayrenderer.so"

            preload_parts = [part for part in [existing_preload, new_preload_paths] if part]
            env["LD_PRELOAD"] = ":".join(preload_parts)

        return env

    @staticmethod
    def build_launch_command(
        proton_path: str,
        game_exec: str,
        steam_runtime_path: Optional[str] = None,
        args_before: Optional[str] = None,
        args_after: Optional[str] = None,
    ) -> List[str]:
        """Builds game launch command"""
        cmd_argv = [proton_path, "run", game_exec]

        if steam_runtime_path:
            cmd_argv.insert(0, steam_runtime_path)

        # Safely add arguments
        if args_before:
            try:
                args_before_list = shlex.split(args_before)
                cmd_argv = args_before_list + cmd_argv
            except ValueError as e:
                logging.warning(f"[SOFL] Failed to parse args_before '{args_before}': {e}")

        if args_after:
            try:
                args_after_list = shlex.split(args_after)
                cmd_argv.extend(args_after_list)
            except ValueError as e:
                logging.warning(f"[SOFL] Failed to parse args_after '{args_after}': {e}")

        return cmd_argv

    @staticmethod
    def launch_game(cmd_argv: List[str], env: Dict[str, str], game_dir: Path, in_flatpak: bool = False) -> None:
        """Launches game in appropriate environment"""
        if in_flatpak:
            # In Flatpak use flatpak-spawn
            env_args = []
            for key, value in env.items():
                str_value = str(value) if value is not None else ""
                if str_value.strip():
                    env_args.append(f"--env={key}={str_value}")

            full_cmd = ["flatpak-spawn", "--host"] + env_args + cmd_argv

            # Add directory change
            if game_dir:
                full_cmd = ["sh", "-c", f"cd {shlex.quote(str(game_dir))} && exec \"$@\"", "sh"] + full_cmd[1:]

            logging.info(f"[SOFL] Executing command via flatpak-spawn: {' '.join(shlex.quote(str(arg)) for arg in full_cmd)}")
            subprocess.Popen(full_cmd, start_new_session=True)
        else:
            # In native environment launch directly
            logging.info(f"[SOFL] Executing command: {' '.join(shlex.quote(str(arg)) for arg in cmd_argv)}")
            subprocess.Popen(cmd_argv, cwd=str(game_dir), env={**os.environ, **env}, start_new_session=True)
