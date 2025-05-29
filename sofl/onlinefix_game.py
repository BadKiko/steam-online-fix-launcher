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
from typing import Any, Optional
from pathlib import Path
from time import time

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.utils.run_executable import run_executable
from sofl.utils.create_dialog import create_dialog

from gettext import gettext as _

import os
import shutil
import stat
import tempfile
from pathlib import Path
import logging

class OnlineFixGameData(GameData):
    """Класс данных для игр Online-Fix с расширенной функциональностью"""
    
    def __init__(self, data: dict[str, Any]):
        super().__init__(data)
    
    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play with Online-Fix")


    def launch(self) -> None:
        self.last_played = int(time())
        self.save()
        self.update()

        launcher_type = shared.schema.get_int("online-fix-launcher-type")

        logging.info(f"[SOFL] Launcher type: {launcher_type}")
        
        game_exec = Path(self.executable.split()[0])

        proton_path = os.environ.get("SOFL_PROTON_PATH", "~/.local/share/Steam/compatibilitytools.d/GE-Proton9-26")
        proton_path = os.path.expanduser(proton_path)

        prefix_path = os.environ.get("SOFL_WINEPREFIX", "~/.local/share/Steam/steamapps/compatdata/480")
        prefix_path = os.path.expanduser(prefix_path)

        dll_overrides = shared.schema.get_string("online-fix-dll-overrides")

        # Путь к umu-run внутри Flatpak
        flatpak_umu_path = f"{os.getenv('FLATPAK_DEST')}/bin/umu/umu-run"
        # Копируем umu-run во временную папку на хосте (в /tmp)
        temp_dir = tempfile.gettempdir()
        
        logging.info(flatpak_umu_path)
        logging.info(temp_dir)
        shutil.copy(flatpak_umu_path, temp_dir)
        
        host_umu_path = os.path.join(temp_dir, f"umu-run-{os.getuid()}")
    

        # Копируем только если файл отсутствует или отличается
        if not os.path.exists(host_umu_path) or \
           os.path.getmtime(host_umu_path) < os.path.getmtime(flatpak_umu_path):
            shutil.copy2(flatpak_umu_path, host_umu_path)
            os.chmod(host_umu_path, os.stat(host_umu_path).st_mode | stat.S_IXUSR)
        # Формируем команду с вызовом через flatpak-spawn --host
        cmd = [
            f"WINEPREFIX='{prefix_path}'",
            f"WINEDLLOVERRIDES=\"{dll_overrides}\"",
            "GAMEID=480",
            f"PROTONPATH={proton_path}",
            host_umu_path,
            f"'{game_exec}'"
        ]
        cmd_str = " ".join(cmd)
    
        run_executable(cmd_str)

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

        self.create_toast(_("{} launched").format(self.name))


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
                _("Uninstall")
            )

            dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
            def on_response(dialog, response):
                if response == "uninstall":
                    self.log_and_toast(_("{} started uninstalling").format(self.name))
                    try:
                        # Remove the game's root folder
                        shutil.rmtree(game_root)
                        self.log_and_toast(_("{} uninstalled").format(self.name))
                    except Exception as e:
                        self.log_and_toast(_("Error uninstalling {}: {}").format(self.name, str(e)))
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