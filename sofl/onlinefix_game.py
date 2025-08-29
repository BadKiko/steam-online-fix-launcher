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
import os
import shutil
from pathlib import Path
from time import time
from typing import Any, Optional

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.utils.create_dialog import create_dialog
from sofl.utils.path_utils import normalize_executable_path
from sofl.utils.steam_launcher import SteamLauncher

from gettext import gettext as _


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

        # Проверяем путь к исполняемому файлу
        game_exec = normalize_executable_path(self.executable)
        if not game_exec:
            self.log_and_toast(_("Invalid executable path"))
            return

        # Определяем окружение
        in_flatpak = os.path.exists("/.flatpak-info")
        host_home = SteamLauncher.get_host_home(in_flatpak)

        # Проверяем, запущен ли Steam
        if not SteamLauncher.check_steam_running(in_flatpak):
            self.log_and_toast(_("Steam is not running"))
            return

        # Получаем настройки Proton
        proton_version = shared.schema.get_string("online-fix-proton-version")
        steam_home = os.path.join(host_home, ".local/share/Steam")

        # Проверяем существование Proton
        proton_path = os.path.join(
            steam_home, "compatibilitytools.d", proton_version, "proton"
        )
        if not SteamLauncher.check_proton_exists(proton_version, steam_home, in_flatpak):
            self.log_and_toast(_("Proton version not found: {}").format(proton_version))
            return

        # Создаем префикс Wine
        prefix_path = self._create_wine_prefix(game_exec)
        user_home = host_home if in_flatpak else os.path.expanduser("~")

        # Подготавливаем переменные окружения
        env = SteamLauncher.prepare_environment(prefix_path, user_home)

        # Ищем Steam Runtime если включен
        steam_runtime_path = None
        if shared.schema.get_boolean("online-fix-use-steam-runtime"):
            steam_runtime_path = SteamLauncher.find_steam_runtime(steam_home, in_flatpak)
            if not steam_runtime_path:
                # Проверяем стандартное расположение
                default_runtime = os.path.join(steam_home, "ubuntu12_32", "steam-runtime", "run.sh")
                if SteamLauncher._check_file_exists(default_runtime, in_flatpak):
                    steam_runtime_path = default_runtime
                else:
                    logging.info("[SOFL] Steam Runtime not found")

        # Строим команду запуска
        args_before = shared.schema.get_string("online-fix-args-before")
        args_after = shared.schema.get_string("online-fix-args-after")

        cmd_argv = SteamLauncher.build_launch_command(
            proton_path,
            str(game_exec),
            steam_runtime_path,
            args_before,
            args_after
        )

        # Запускаем игру
        SteamLauncher.launch_game(cmd_argv, env, game_exec.parent, in_flatpak)

        self.create_toast(
            _("{} launched directly with Proton {}").format(self.name, proton_version)
        )

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

    def _run_game(self, cmd_argv: list, env: dict, game_exec: Path) -> None:
        """Launch the game in any environment"""

        # Создаем префикс Wine
        prefix_path = self._create_wine_prefix(game_exec)
        if not os.path.exists(prefix_path):
            os.makedirs(prefix_path, exist_ok=True)

        # Создаем структуру префикса для совместимости
        pfx_user_path = os.path.join(
            prefix_path, "pfx", "drive_c", "users", "steamuser"
        )
        for dir_name in ["AppData", "Saved Games", "Documents"]:
            os.makedirs(os.path.join(pfx_user_path, dir_name), exist_ok=True)

        # Запускаем игру через SteamLauncher
        in_flatpak = os.path.exists("/.flatpak-info")
        SteamLauncher.launch_game(cmd_argv, env, game_exec.parent, in_flatpak)

    def uninstall_game(self) -> None:
        """Удаление игры с подтверждением"""
        if "online-fix" not in self.source:
            self.log_and_toast(_("Cannot uninstall non-online-fix games"))
            return

        onlinefix_path = shared.schema.get_string("online-fix-install-path")
        onlinefix_root = Path(os.path.expanduser(onlinefix_path))

        try:
            if not str(self.executable).startswith(str(onlinefix_root)):
                self._remove_from_list_only()
                return

            game_root = self._detect_game_root_folder(onlinefix_root)
            self._show_uninstall_confirmation(game_root)

        except Exception as e:
            self.log_and_toast(_("Error: {}").format(str(e)))

    def _remove_from_list_only(self) -> None:
        """Удаляет игру только из списка"""
        self.log_and_toast(
            _("Game is not installed in Online-Fix directory, removing it from the list")
        )
        self.removed = True
        self.save()
        self.update()

    def _show_uninstall_confirmation(self, game_root: Path) -> None:
        """Показывает диалог подтверждения удаления"""
        dialog = create_dialog(
            shared.win,
            _("Uninstall Game"),
            _("This will remove folder {}, and can't be undone.").format(game_root),
            "uninstall",
            _("Uninstall"),
        )
        dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: self._handle_uninstall_response(r, game_root))

    def _handle_uninstall_response(self, response: str, game_root: Path) -> None:
        """Обрабатывает ответ пользователя в диалоге удаления"""
        if response != "uninstall":
            return

        self.log_and_toast(_("{} started uninstalling").format(self.name))

        try:
            shutil.rmtree(game_root)
            self.log_and_toast(_("{} uninstalled").format(self.name))
        except Exception as e:
            self.log_and_toast(_("Error uninstalling {}: {}").format(self.name, str(e)))
        finally:
            self.removed = True
            self.save()
            self.update()

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
