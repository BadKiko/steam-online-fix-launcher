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
        
        # Check if we should use Steam/Proton for launching
        launcher_type = shared.schema.get_int("online-fix-launcher-type")
        if launcher_type == 1:  # Steam API option
            self.launch_with_steam_proton()
        else:
            # Run the online-fix executable with default handling
            run_executable(self.executable)
        
        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()
        
        # Create toast notification
        self.create_toast(_("{} launched with Online-Fix").format(self.name))
    
    def launch_with_steam_proton(self) -> None:
        """Launch the game through Steam with Proton"""
        try:
            # Get the path to the executable
            exec_path = Path(self.executable.split()[0])
            
            # Generate a unique AppID for this game based on its path
            # This will help ensure we get a consistent Steam shortcut ID
            import hashlib
            game_hash = hashlib.md5(str(exec_path).encode()).hexdigest()
            shortcut_id = int(game_hash[:8], 16) % 1000000  # Create a shorter number for AppID
            
            # Prepare launch options with DLL overrides
            launch_options = ""
            
            # Add WINEDLLOVERRIDES if auto-patch is disabled
            if not shared.schema.get_boolean("online-fix-auto-patch"):
                dll_overrides = shared.schema.get_string("online-fix-dll-overrides")
                if dll_overrides:
                    launch_options += f"WINEDLLOVERRIDES=\"{dll_overrides}\" "
            
            # Add SteamAppID environment variable if enabled
            if shared.schema.get_boolean("online-fix-steam-appid-patch"):
                launch_options += "SteamAppId=480 "  # Use generic AppID 480 (Spacewar)
                
            # Add Steam-Fix-64 patch if enabled
            if shared.schema.get_boolean("online-fix-steamfix64-patch"):
                # Set path to Steam installation - adjust path if needed
                steam_path = "~/.steam/steam"
                launch_options += f"STEAM_COMPAT_CLIENT_INSTALL_PATH=\"{steam_path}\" "
            
            # Create Steam directories if they don't exist
            steam_config_dir = Path(os.path.expanduser("~/.steam/steam/userdata"))
            if not steam_config_dir.exists():
                # Try alternative path for Flatpak
                steam_config_dir = Path(os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/userdata"))
            
            # Find the first user directory
            user_dirs = [d for d in steam_config_dir.glob("*") if d.is_dir() and d.name.isdigit()]
            if not user_dirs:
                self.log_and_toast(_("Could not find Steam user directory"))
                raise Exception("Steam user directory not found")
                
            user_config_dir = user_dirs[0] / "config"
            
            # Ensure the directory exists
            user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a temporary VDF file to add the game to Steam
            vdf_path = user_config_dir / "shortcuts.vdf"
            
            # Create a simple VDF structure to add the non-Steam game
            vdf_content = f"""
            "shortcuts"
            {{
                "{shortcut_id}"
                {{
                    "AppName"		"{self.name}"
                    "Exe"		"{str(exec_path)}"
                    "StartDir"		"{str(exec_path.parent)}"
                    "LaunchOptions"		"{launch_options} %command%"
                    "IsHidden"		"0"
                    "AllowDesktopConfig"		"1"
                    "AllowOverlay"		"1"
                    "OpenVR"		"0"
                    "Devkit"       "0"
                    "DevkitGameID" ""
                    "LastPlayTime" "{self.last_played}"
                    "ShortcutID"   "{shortcut_id}"
                    "appid"        "{shortcut_id + 989400000}"
                    "Tags"
                    {{
                        "0"		"Online-Fix"
                    }}
                }}
            }}
            """
            
            # First, back up the original shortcuts.vdf if it exists
            backup_path = None
            if vdf_path.exists():
                backup_path = vdf_path.with_suffix('.vdf.bak')
                shutil.copy2(vdf_path, backup_path)
                
            # Write the new shortcuts.vdf
            with open(vdf_path, 'w') as f:
                f.write(vdf_content)
            
            # Set Proton compatibility in config.vdf
            config_vdf_path = user_config_dir / "config.vdf"
            
            # Simple content for config.vdf to set Proton compatibility
            proton_id = "Proton 8"  # Use latest Proton by default
            config_content = f"""
            "InstallConfigStore"
            {{
                "Software"
                {{
                    "Valve"
                    {{
                        "Steam"
                        {{
                            "CompatToolMapping"
                            {{
                                "{shortcut_id + 989400000}"
                                {{
                                    "name"		"{proton_id}"
                                    "config"		""
                                    "priority"		"250"
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            
            # Backup config.vdf if it exists
            config_backup_path = None
            if config_vdf_path.exists():
                config_backup_path = config_vdf_path.with_suffix('.vdf.bak')
                shutil.copy2(config_vdf_path, config_backup_path)
                
            # Write the new config.vdf
            with open(config_vdf_path, 'w') as f:
                f.write(config_content)
                
            # Find Steam executable
            steam_exe = "steam"
                
            # Log the launch attempt
            logging.info(f"Added {self.name} to Steam with shortcut ID: {shortcut_id}")
            logging.info(f"Launch options: {launch_options}")
            
            # Restart Steam and launch the game
            cmd = [steam_exe, "-silent"]
            
            # Use Flatpak spawn if running in Flatpak
            if os.getenv("FLATPAK_ID") == shared.APP_ID:
                cmd = ["flatpak-spawn", "--host"] + cmd
            
            # Launch Steam
            subprocess.Popen(
                cmd,
                start_new_session=True,
                shell=False
            )
            
            # Show toast notification
            self.log_and_toast(_("Game added to Steam, start it from your Steam library"))
            
            # Schedule restoration of the original files after some time
            if backup_path or config_backup_path:
                restore_script = "#!/bin/sh\n"
                restore_script += "sleep 300\n"  # Wait 5 minutes
                
                if backup_path:
                    restore_script += f"mv '{backup_path}' '{vdf_path}'\n"
                
                if config_backup_path:
                    restore_script += f"mv '{config_backup_path}' '{config_vdf_path}'\n"
                
                # Create a temporary script file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                    script_path = script_file.name
                    script_file.write(restore_script)
                
                # Make it executable
                os.chmod(script_path, 0o755)
                
                # Run the script in background
                subprocess.Popen(
                    [script_path],
                    start_new_session=True,
                    shell=False
                )
            
        except Exception as e:
            self.log_and_toast(_("Error launching with Steam: {}").format(str(e)))
            # Fallback to standard launch method
            run_executable(self.executable)
    
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