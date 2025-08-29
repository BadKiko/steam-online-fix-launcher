# onlinefix_game.py
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

import logging
import shlex
import os
import subprocess
import tempfile
import struct
import threading
from typing import Any, Optional
from pathlib import Path
from time import time

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.utils.run_executable import run_executable
from sofl.utils.create_dialog import create_dialog
from sofl.utils.path_utils import normalize_executable_path

from gettext import gettext as _

import stat
import vdf
import binascii
import shutil


class OnlineFixGameData(GameData):
    """Класс данных для игр Online-Fix с расширенной функциональностью"""

    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play with Online-Fix")

    def _create_wine_prefix(self, game_exec: Path) -> str:
        """Создает структуру префикса Wine для игры

        Args:
            game_exec: Путь к исполняемому файлу игры

        Returns:
            str: Путь к созданному префиксу
        """
        prefix_path = os.path.join(game_exec.parent, "OFME Prefix")
        os.makedirs(prefix_path, exist_ok=True)

        # Создаем структуру префикса для совместимости с оригинальным кодом
        pfx_user_path = os.path.join(
            prefix_path, "pfx", "drive_c", "users", "steamuser"
        )
        for dir_name in ["AppData", "Saved Games", "Documents"]:
            os.makedirs(os.path.join(pfx_user_path, dir_name), exist_ok=True)

        return prefix_path

    def launch(self) -> None:
        """Запускает игру с Online-Fix"""
        self.last_played = int(time())
        self.save()
        self.update()

        # Launch directly with Steam API (only supported method)
        self._launch_with_direct_steam_api()

    def _launch_with_direct_steam_api(self) -> None:
        """Запуск игры через Direct Steam API Runner"""
        logging.info("Direct Steam API Runner")

        game_exec = normalize_executable_path(self.executable)
        game_exec_str = str(game_exec) if game_exec else ""
        if not game_exec_str:
            self.log_and_toast(_("Invalid executable path"))
            return
        dll_overrides = shared.schema.get_string("online-fix-dll-overrides")

        # Detect Flatpak environment and, if present, try to run host checks
        in_flatpak = os.path.exists("/.flatpak-info")
        host_home = os.path.expanduser("~")
        if in_flatpak:
            try:
                host_home_proc = subprocess.run(
                    ["flatpak-spawn", "--host", "printenv", "HOME"],
                    capture_output=True,
                    text=True,
                )
                if host_home_proc.returncode == 0:
                    host_home = host_home_proc.stdout.strip()
            except Exception as e:
                logging.error(f"[SOFL] Failed to get host home: {e}")

        # Проверяем, запущен ли Steam (use host pidof when inside Flatpak)
        try:
            if in_flatpak:
                steam_process = subprocess.run(
                    ["flatpak-spawn", "--host", "pidof", "steam"],
                    capture_output=True,
                    text=True,
                )
            else:
                steam_process = subprocess.run(
                    ["pidof", "steam"], capture_output=True, text=True
                )
            if steam_process.returncode == 1 or not steam_process.stdout.strip():
                self.log_and_toast(_("Steam is not running"))
                return
        except Exception as e:
            logging.error(f"[SOFL] Failed to check Steam status: {str(e)}")
            # Продолжаем выполнение, даже если не удалось проверить статус Steam

        # Получаем путь к Proton из настроек
        proton_version = shared.schema.get_string("online-fix-proton-version")
        # Use host Steam home when running inside Flatpak
        steam_home = os.path.join(host_home, ".local/share/Steam")
        proton_path = os.path.join(
            steam_home, "compatibilitytools.d", proton_version, "proton"
        )

        # Проверяем существование Proton (check on host when in Flatpak)
        try:
            if in_flatpak:
                check = subprocess.run(
                    ["flatpak-spawn", "--host", "test", "-e", proton_path],
                    capture_output=True,
                )
                proton_exists = check.returncode == 0
            else:
                proton_exists = os.path.exists(proton_path)
        except Exception:
            proton_exists = False

        if not proton_exists:
            self.log_and_toast(_("Proton version not found: {}").format(proton_version))
            return

        # Настраиваем переменные окружения
        # Use host home for Steam-related envs when inside Flatpak
        user_home = host_home if in_flatpak else os.path.expanduser("~")
        dx_overrides = "d3d11=n;d3d10=n;d3d10core=n;dxgi=n;openvr_api_dxvk=n;d3d12=n;d3d12core=n;d3d9=n;d3d8=n;"

        # Создаем директорию для префикса, если она не существует
        prefix_path = self._create_wine_prefix(game_exec)

        # Проверяем, включен ли режим отладки
        debug_mode = shared.schema.get_boolean("online-fix-debug-mode")

        # Настраиваем переменные окружения точно как в оригинальном коде
        env = {
            "WINEDLLOVERRIDES": f"{dx_overrides}{dll_overrides}",
            "WINEDEBUG": "+warn,+err,+trace" if debug_mode else "-all",
            "STEAM_COMPAT_DATA_PATH": prefix_path,
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": f"{user_home}/.steam/steam",
        }

        # Optional: Add Steam Overlay
        use_steam_overlay = shared.schema.get_boolean("online-fix-use-steam-overlay")
        if use_steam_overlay and not in_flatpak:

            existing_preload = env.get("LD_PRELOAD", "")
            new_preload_paths = f"{user_home}/.local/share/Steam/ubuntu12_32/gameoverlayrenderer.so:{user_home}/.local/share/Steam/ubuntu12_64/gameoverlayrenderer.so"

            preload_parts = [part for part in [existing_preload, new_preload_paths] if part]
            env["LD_PRELOAD"] = ":".join(preload_parts)

            logging.info(
                f"[SOFL] Steam Overlay enabled with LD_PRELOAD={env['LD_PRELOAD']}"
            )
        elif use_steam_overlay and in_flatpak:
            logging.info("[SOFL] Steam Overlay disabled in Flatpak environment")

        # Optional: Use Steam Runtime
        use_steam_runtime = shared.schema.get_boolean("online-fix-use-steam-runtime")
        steam_runtime_path = ""
        if use_steam_runtime:
            # Try to find Steam Runtime in Steam libraries, as in the original code
            try:
                # Path to libraryfolders.vdf
                library_folders_path = os.path.join(
                    user_home, ".steam/steam/steamapps/libraryfolders.vdf"
                )
                library_folders_data = None
                if in_flatpak:
                    # Try to read the host file via flatpak-spawn
                    try:
                        cat = subprocess.run(
                            ["flatpak-spawn", "--host", "cat", library_folders_path],
                            capture_output=True,
                            text=True,
                        )
                        if cat.returncode == 0 and cat.stdout:
                            try:
                                library_folders_data = vdf.loads(cat.stdout)
                            except Exception:
                                # fallback to load via file-like object
                                import io

                                library_folders_data = vdf.load(io.StringIO(cat.stdout))
                    except Exception as e:
                        logging.debug(
                            f"[SOFL] Could not read host libraryfolders.vdf: {e}"
                        )
                else:
                    if os.path.exists(library_folders_path):
                        with open(library_folders_path, "r") as f:
                            library_folders_data = vdf.load(f)

                # Search for SteamLinuxRuntime_sniper in Steam libraries
                if library_folders_data and "libraryfolders" in library_folders_data:
                    for folder_id, folder_data in library_folders_data[
                        "libraryfolders"
                    ].items():
                        if "apps" in folder_data and "1628350" in folder_data["apps"]:
                            runtime_path = os.path.join(
                                folder_data["path"],
                                "steamapps/common/SteamLinuxRuntime_sniper/run",
                            )
                            # check file existence on host when in Flatpak
                            try:
                                if in_flatpak:
                                    check_runtime = subprocess.run(
                                        ["flatpak-spawn", "--host", "test", "-f", runtime_path],
                                        capture_output=True,
                                    )
                                    exists_runtime = check_runtime.returncode == 0
                                else:
                                    exists_runtime = os.path.isfile(runtime_path)
                            except Exception:
                                exists_runtime = False

                            if exists_runtime:
                                steam_runtime_path = runtime_path
                                logging.info(
                                    f"[SOFL] Found Steam Runtime at {steam_runtime_path}"
                                )
                                break
            except Exception as e:
                logging.error(f"[SOFL] Error finding Steam Runtime: {str(e)}")

            # If not found, use standard path
            if not steam_runtime_path:
                steam_runtime_path = os.path.join(
                    steam_home, "ubuntu12_32", "steam-runtime", "run.sh"
                )

                # Check if file exists (consider Flatpak environment)
                try:
                    if in_flatpak:
                        check_proc = subprocess.run(
                            [
                                "flatpak-spawn",
                                "--host",
                                "test",
                                "-f",
                                steam_runtime_path,
                            ],
                            capture_output=True,
                        )
                        file_exists = check_proc.returncode == 0
                    else:
                        file_exists = os.path.exists(steam_runtime_path)
                except Exception:
                    file_exists = False

                if not file_exists:
                    steam_runtime_path = ""
                    logging.info("[SOFL] Steam Runtime not found at standard location")

        # Form the launch command as argument list for security
        cmd_argv = [proton_path, "run", game_exec_str]

        if steam_runtime_path:
            cmd_argv.insert(0, steam_runtime_path)

        # Add arguments before and after the executable safely
        args_before = shared.schema.get_string("online-fix-args-before")
        args_after = shared.schema.get_string("online-fix-args-after")

        # Parse args_before and args_after safely using shlex.split
        args_before_list = []
        if args_before:
            try:
                args_before_list = shlex.split(args_before)
            except ValueError as e:
                logging.warning(f"[SOFL] Failed to parse args_before '{args_before}': {e}")
                args_before_list = []

        args_after_list = []
        if args_after:
            try:
                args_after_list = shlex.split(args_after)
            except ValueError as e:
                logging.warning(f"[SOFL] Failed to parse args_after '{args_after}': {e}")
                args_after_list = []

        # Insert args_before at the beginning, append args_after at the end
        cmd_argv = args_before_list + cmd_argv + args_after_list

        # Launch the game
        self._run_game(cmd_argv, env, game_exec)

        self.create_toast(
            _("{} launched directly with Proton {}").format(self.name, proton_version)
        )

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

    def _run_game(self, cmd_argv: list, env: dict, game_exec: Path) -> None:
        """Launch the game in any environment"""
        # Create the prefix directory
        prefix_path = self._create_wine_prefix(game_exec)
        if not os.path.exists(prefix_path):
            os.makedirs(prefix_path, exist_ok=True)

        # Create the prefix structure for compatibility
        pfx_user_path = os.path.join(
            prefix_path, "pfx", "drive_c", "users", "steamuser"
        )
        for dir_name in ["AppData", "Saved Games", "Documents"]:
            os.makedirs(os.path.join(pfx_user_path, dir_name), exist_ok=True)

        if os.path.exists("/.flatpak-info"):
            # In Flatpak environment, run the command on the host via flatpak-spawn
            logging.debug(f"[SOFL] Raw environment dict: {env}")

            # Convert environment variables to --env=KEY=VALUE format
            env_args = []
            for key, value in env.items():
                # Skip empty values and None
                str_value = str(value) if value is not None else ""
                if str_value.strip():
                    # No escaping needed for flatpak-spawn (it parses args directly)
                    env_args.append(f"--env={key}={str_value}")
                    logging.debug(f"[SOFL] Adding env var: {key}={repr(str_value)}")
                else:
                    logging.debug(f"[SOFL] Skipping empty env var: {key}={repr(value)}")

            logging.debug(f"[SOFL] Environment variables to pass: {env_args}")

            # Add the current working directory
            game_dir = str(game_exec.parent)

            # Form the command as argument list
            if game_dir:
                # Prepend cd command as separate arguments
                cmd_argv = ["sh", "-c", f"cd {shlex.quote(game_dir)} && exec \"$@\"", "sh"] + cmd_argv

            full_cmd = ["flatpak-spawn", "--host"] + env_args + cmd_argv

            try:
                logging.info(
                    f"[SOFL] Executing command via flatpak-spawn: {' '.join(shlex.quote(str(arg)) for arg in full_cmd)}"
                )
                subprocess.Popen(
                    full_cmd,
                    start_new_session=True,
                )
            except Exception as e:
                self.log_and_toast(_("Failed to launch game: {}").format(str(e)))
        else:
            # In native environment, run the command directly
            try:
                logging.info(f"[SOFL] Executing command: {' '.join(shlex.quote(str(arg)) for arg in cmd_argv)}")
                subprocess.Popen(
                    cmd_argv,
                    cwd=str(game_exec.parent),
                    env={**os.environ, **env},
                    start_new_session=True,
                )
            except Exception as e:
                self.log_and_toast(_("Failed to launch game: {}").format(str(e)))

    def uninstall_game(self) -> None:
        """Uninstall the game by removing its root directory after confirmation"""
        # Check if the game is from online-fix
        if "online-fix" not in self.source:
            self.log_and_toast(_("Cannot uninstall non-online-fix games"))
            return
        # Get the path to online-fix installations
        onlinefix_path = shared.schema.get_string("online-fix-install-path")
        # Expand tilde to full home directory path
        onlinefix_root = Path(os.path.expanduser(onlinefix_path))
        try:
            # Check if the game is inside the online-fix folder
            if not str(self.executable).startswith(str(onlinefix_root)):
                self.log_and_toast(
                    _(
                        "Game is not installed in Online-Fix directory, removing it from the list"
                    )
                )
                self.removed = True
                self.save()
                self.update()
                return
            # Get a more reliable game root folder
            game_root = self._detect_game_root_folder(onlinefix_root)
            # Create a confirmation dialog
            dialog = create_dialog(
                shared.win,
                _("Uninstall Game"),
                _("This will remove folder {}, and can't be undone.").format(game_root),
                "uninstall",
                _("Uninstall"),
            )

            dialog.set_response_appearance(
                "uninstall", Adw.ResponseAppearance.DESTRUCTIVE
            )

            def on_response(dialog, response):
                if response == "uninstall":
                    self.log_and_toast(_("{} started uninstalling").format(self.name))
                    try:
                        # Remove the game's root folder
                        shutil.rmtree(game_root)
                        self.log_and_toast(_("{} uninstalled").format(self.name))
                    except Exception as e:
                        self.log_and_toast(
                            _("Error uninstalling {}: {}").format(self.name, str(e))
                        )
                    finally:
                        # Mark the game as removed
                        self.removed = True
                        self.save()
                        self.update()

            dialog.connect("response", on_response)
        except Exception as e:
            self.log_and_toast(_("Error: {}").format(str(e)))

    def _detect_game_root_folder(self, onlinefix_root: Path) -> Path:
        """
        Detects the game's root folder more reliably
        Args:
            onlinefix_root: Path to the online-fix installation directory
        Returns:
            Path: Path to the detected game folder
        """
        try:
            # Get the path to the executable
            exec_path = Path(self.executable.split()[0])
            # Make sure it's relative to the online-fix root
            if not str(exec_path).startswith(str(onlinefix_root)):
                # Fallback to parent directory of executable
                return exec_path.parent
            # Get relative path from online-fix root
            rel_path = exec_path.relative_to(onlinefix_root)
            # First try to use first directory component
            if len(rel_path.parts) > 0:
                candidate = rel_path.parts[0]
                game_dir = onlinefix_root / candidate
                # Verify that this is actually a directory
                if game_dir.is_dir():
                    return game_dir
            # If first component isn't suitable, fall back to executable's parent
            return exec_path.parent
        except Exception as e:
            logging.error(f"Error detecting game root folder: {str(e)}")
            # Always fall back to parent directory of executable if something goes wrong
            return Path(self.executable.split()[0]).parent

    def log_and_toast(self, message: str) -> None:
        """Log a message and show a toast notification"""
        logging.info(f"[SOFL] {message}")
        self.create_toast(message)
