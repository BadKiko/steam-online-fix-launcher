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
import shutil
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

from gettext import gettext as _

import stat
import vdf
import binascii
import subprocess


class OnlineFixGameData(GameData):
    """Класс данных для игр Online-Fix с расширенной функциональностью"""

    def __init__(self, data: dict[str, Any]):
        super().__init__(data)

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

        launcher_type = shared.schema.get_int("online-fix-launcher-type")
        logging.info(f"[SOFL] Launcher type: {launcher_type}")

        if launcher_type == 0:
            self._launch_with_direct_steam_api()
        elif launcher_type == 1:
            self._launch_with_umu_runner()

    def _launch_with_direct_steam_api(self) -> None:
        """Запуск игры через Direct Steam API Runner"""
        logging.info("Direct Steam API Runner")

        game_exec = Path(self.executable.split()[0])
        dll_overrides = shared.schema.get_string("online-fix-dll-overrides")

        # Проверяем, запущен ли Steam (с учетом flatpak)
        try:
            # В flatpak окружении используем flatpak-spawn для проверки
            if os.path.exists("/.flatpak-info"):
                steam_process = subprocess.run(
                    ["flatpak-spawn", "--host", "pidof", "steam"],
                    capture_output=True,
                    text=True,
                )
            else:
                steam_process = subprocess.run(
                    ["pidof", "steam"], capture_output=True, text=True
                )

            if steam_process.returncode == 1:
                self.log_and_toast(_("Steam is not running"))
                return
        except Exception as e:
            logging.error(f"[SOFL] Failed to check Steam status: {str(e)}")
            # Продолжаем выполнение, даже если не удалось проверить статус Steam

        # Путь к исполняемому файлу игры
        game_exec_str = str(game_exec)

        # Получаем путь к Proton из настроек
        proton_version = shared.schema.get_string("online-fix-proton-version")
        steam_home = os.path.expanduser("~/.local/share/Steam")
        proton_path = os.path.join(
            steam_home, "compatibilitytools.d", proton_version, "proton"
        )

        # Проверяем существование Proton
        if not os.path.exists(proton_path):
            self.log_and_toast(_("Proton version not found: {}").format(proton_version))
            return

        # Настраиваем переменные окружения
        user_home = os.path.expanduser("~")
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

        # Опционально добавляем Steam Overlay
        use_steam_overlay = shared.schema.get_boolean("online-fix-use-steam-overlay")
        if use_steam_overlay:
            env["LD_PRELOAD"] = (
                f":{user_home}/.local/share/Steam/ubuntu12_32/gameoverlayrenderer.so:{user_home}/.local/share/Steam/ubuntu12_64/gameoverlayrenderer.so"
            )
            logging.info(
                f"[SOFL] Steam Overlay enabled with LD_PRELOAD={env['LD_PRELOAD']}"
            )

        # Опционально используем Steam Runtime
        use_steam_runtime = shared.schema.get_boolean("online-fix-use-steam-runtime")
        steam_runtime_path = ""
        if use_steam_runtime:
            # Пытаемся найти Steam Runtime в библиотеках Steam, как в оригинальном коде
            try:
                # Путь к файлу libraryfolders.vdf
                library_folders_path = os.path.join(
                    user_home, ".steam/steam/steamapps/libraryfolders.vdf"
                )
                if os.path.exists(library_folders_path):
                    with open(library_folders_path, "r") as f:
                        library_folders_data = vdf.load(f)

                    # Ищем SteamLinuxRuntime_sniper в библиотеках
                    if "libraryfolders" in library_folders_data:
                        for folder_id, folder_data in library_folders_data[
                            "libraryfolders"
                        ].items():
                            if (
                                "apps" in folder_data
                                and "1628350" in folder_data["apps"]
                            ):
                                runtime_path = os.path.join(
                                    folder_data["path"],
                                    "steamapps/common/SteamLinuxRuntime_sniper/run",
                                )
                                if os.path.isfile(runtime_path):
                                    steam_runtime_path = runtime_path
                                    logging.info(
                                        f"[SOFL] Found Steam Runtime at {steam_runtime_path}"
                                    )
                                    break
            except Exception as e:
                logging.error(f"[SOFL] Error finding Steam Runtime: {str(e)}")

            # Если не нашли, используем стандартный путь
            if not steam_runtime_path:
                steam_runtime_path = os.path.join(
                    steam_home, "ubuntu12_32", "steam-runtime", "run.sh"
                )
                if not os.path.exists(steam_runtime_path):
                    steam_runtime_path = ""
                    self.log_and_toast(_("Steam Runtime not found"))

        # Формируем команду запуска
        cmd = f'"{proton_path}" run "{game_exec_str}"'

        if steam_runtime_path:
            cmd = f'"{steam_runtime_path}" {cmd}'

        # Добавляем аргументы перед и после исполняемого файла
        args_before = shared.schema.get_string("online-fix-args-before")
        args_after = shared.schema.get_string("online-fix-args-after")

        if args_before:
            cmd = f"{args_before} {cmd}"
        if args_after:
            cmd = f"{cmd} {args_after}"

        # Если отладка отключена, перенаправляем вывод в /dev/null
        if not debug_mode:
            cmd = f"{cmd} > /dev/null 2>&1"

        # Запускаем через bash
        if os.path.exists("/.flatpak-info"):
            self._run_in_flatpak(cmd, env, game_exec, prefix_path)
        else:
            self._run_native(cmd, env, game_exec)

        self.create_toast(
            _("{} launched directly with Proton {}").format(self.name, proton_version)
        )

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

    def _launch_with_umu_runner(self) -> None:
        """Запуск игры через UMU Runner"""
        logging.info("Umu Runner")

        game_exec = Path(self.executable.split()[0])
        dll_overrides = shared.schema.get_string("online-fix-dll-overrides")

        # Get selected Proton version from settings
        proton_version = shared.schema.get_string("online-fix-umu-proton-version")
        proton_path = os.path.expanduser(
            f"~/.local/share/Steam/compatibilitytools.d/{proton_version}"
        )

        # Check if Proton exists, fall back to default if not
        if not os.path.exists(proton_path):
            default_proton = "GE-Proton10-3"
            proton_path = os.path.expanduser(
                f"~/.local/share/Steam/compatibilitytools.d/{default_proton}"
            )
            self.log_and_toast(
                _("Proton version not found, using {}").format(default_proton)
            )

        # Создаем директорию для префикса, если она не существует
        prefix_path = self._create_wine_prefix(game_exec)

        # Используем этот префикс вместо стандартного
        prefix_path = os.environ.get("SOFL_WINEPREFIX", prefix_path)
        prefix_path = os.path.expanduser(prefix_path)

        # Resolve umu-run path depending on environment
        flatpak_umu_path = f"{os.getenv('FLATPAK_DEST')}/bin/umu/umu-run"
        host_umu_path: Optional[str] = None
        logging.info(f"Using Proton: {proton_path}")

        if os.path.exists("/.flatpak-info") and os.path.isfile(flatpak_umu_path):
            # Inside Flatpak: copy to /tmp and execute via flatpak-spawn --host
            temp_dir = tempfile.gettempdir()
            host_umu_tmp = os.path.join(temp_dir, f"umu-run-{os.getuid()}")
            logging.info(f"Flatpak UMU path: {flatpak_umu_path}")
            logging.info(f"Host UMU temp path: {host_umu_tmp}")
            if not os.path.exists(host_umu_tmp) or os.path.getmtime(
                host_umu_tmp
            ) < os.path.getmtime(flatpak_umu_path):
                shutil.copy2(flatpak_umu_path, host_umu_tmp)
                os.chmod(host_umu_tmp, os.stat(host_umu_tmp).st_mode | stat.S_IXUSR)
            host_umu_path = host_umu_tmp
        else:
            # Native host: try PATH first, then vendored path in Arch package
            path_candidate = shutil.which("umu-run")
            vendor_candidate = "/usr/share/sofl/umu/umu-run"
            if path_candidate:
                host_umu_path = path_candidate
            elif os.path.isfile(vendor_candidate):
                host_umu_path = vendor_candidate
            else:
                self.log_and_toast(
                    _(
                        "umu-run not found. Please install umu-launcher or reinstall package."
                    )
                )
                return

        # Формируем команду с вызовом через flatpak-spawn --host
        cmd = [
            f"WINEPREFIX='{prefix_path}'",
            f'WINEDLLOVERRIDES="{dll_overrides}"',
            "GAMEID=480",
            f"PROTONPATH={proton_path}",
            host_umu_path,
            f"'{game_exec}'",
        ]
        cmd_str = " ".join(cmd)

        run_executable(cmd_str)

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

        self.create_toast(_("{} launched").format(self.name))

    def _run_in_flatpak(
        self, cmd: str, env: dict, game_exec: Path, prefix_path: str
    ) -> None:
        """Запуск команды в окружении Flatpak через временный скрипт"""
        # В flatpak окружении создаем временный скрипт для запуска
        with tempfile.NamedTemporaryFile(
            mode="w", prefix="sofl_launch_", suffix=".sh", delete=False
        ) as script_file:
            script_path = script_file.name

            # Записываем скрипт с экспортом всех переменных окружения
            script_file.write("#!/bin/bash\n\n")

            # Экспортируем все переменные окружения
            for key, value in env.items():
                # Убедимся, что пути правильно экранированы
                value = value.replace('"', '\\"')
                script_file.write(f'export {key}="{value}"\n')

            # Создаем директорию для префикса на хосте
            script_file.write(f'\nmkdir -p "{prefix_path}"\n')

            # Создаем структуру префикса для совместимости с оригинальным кодом
            pfx_user_path = os.path.join(
                prefix_path, "pfx", "drive_c", "users", "steamuser"
            )
            for dir_name in ["AppData", "Saved Games", "Documents"]:
                script_file.write(
                    f'mkdir -p "{os.path.join(pfx_user_path, dir_name)}"\n'
                )

            # Добавляем команду запуска
            script_file.write(f"\n{cmd}\n")

        # Делаем скрипт исполняемым
        os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR)

        # Запускаем скрипт через flatpak-spawn
        full_cmd = ["flatpak-spawn", "--host", script_path]
        logging.info(f"[SOFL] Created launch script: {script_path}")

        try:
            logging.info(f"[SOFL] Executing command: {' '.join(full_cmd)}")
            subprocess.Popen(
                full_cmd, cwd=str(game_exec.parent), start_new_session=True
            )

            # Планируем удаление временного файла через некоторое время
            def delayed_delete():
                import time

                time.sleep(10)  # Даем время на запуск скрипта
                try:
                    if os.path.exists(script_path):
                        os.unlink(script_path)
                except Exception as e:
                    logging.error(f"[SOFL] Failed to delete temp script: {str(e)}")

            # Запускаем удаление в отдельном потоке
            threading.Thread(target=delayed_delete, daemon=True).start()
        except Exception as e:
            self.log_and_toast(_("Failed to launch game: {}").format(str(e)))

    def _run_native(self, cmd: str, env: dict, game_exec: Path) -> None:
        """Запуск команды в нативном окружении"""
        full_cmd = ["bash", "-c", cmd]

        try:
            logging.info(f"[SOFL] Executing command: {' '.join(full_cmd)}")
            subprocess.Popen(
                full_cmd,
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
                self.log_and_toast(_("Game is not installed in Online-Fix directory"))
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
