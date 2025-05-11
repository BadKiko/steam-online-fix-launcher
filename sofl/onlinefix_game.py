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
from typing import Any, Optional
from pathlib import Path
from time import time

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.utils.run_executable import run_executable
from sofl.utils.create_dialog import create_dialog

from gettext import gettext as _

class OnlineFixGameData(GameData):
    """Класс данных для игр Online-Fix с расширенной функциональностью"""
    
    def __init__(self, data: dict[str, Any]):
        super().__init__(data)
    
    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play with Online-Fix")
    
    def launch(self) -> None:
        """Launch the Online-Fix game with its specific launcher logic"""
        # First record last played time and save/update the game
        self.last_played = int(time())
        self.save()
        self.update()
        
        # Run the online-fix executable with any potential special handling
        run_executable(self.executable)
        
        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()
        
        # Create toast notification
        self.create_toast(_("{} launched with Online-Fix").format(self.name))
    
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