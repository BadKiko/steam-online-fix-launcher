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
import shlex
import shutil
import sys
from pathlib import Path
from time import time
from typing import Any, Optional

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.proton.proton_manager import ProtonManager
from sofl.utils.create_dialog import create_dialog
from sofl.utils.path_utils import normalize_executable_path
from sofl.utils.steam_launcher import SteamLauncher

from gettext import gettext as _


class OnlineFixGameData(GameData):
    """Data class for Online-Fix games with extended functionality"""

    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play with Online-Fix")

    def _create_wine_prefix(self, game_exec: Path) -> str:
        """Creates Wine prefix structure for the game

        Args:
            game_exec: Path to game executable

        Returns:
            str: Path to created prefix
        """
        # In Flatpak, we can't create prefix next to the game executable
        # because the game path might be read-only. Use a writable location instead.
        in_flatpak = os.path.exists("/.flatpak-info")
        if in_flatpak:
            # Use Flatpak data directory for Wine prefixes
            import hashlib
            game_path_hash = hashlib.md5(str(game_exec).encode()).hexdigest()[:8]
            prefix_path = os.path.join(shared.home, ".var", "app", "org.badkiko.sofl", "data", "wine-prefixes", game_path_hash)
        else:
            # Use the traditional approach for native installations
            prefix_path = os.path.join(game_exec.parent, "OFME Prefix")

        os.makedirs(prefix_path, exist_ok=True)

        # Create prefix structure for compatibility with original code
        pfx_user_path = os.path.join(
            prefix_path, "pfx", "drive_c", "users", "steamuser"
        )
        for dir_name in ["AppData", "Saved Games", "Documents"]:
            os.makedirs(os.path.join(pfx_user_path, dir_name), exist_ok=True)

        return prefix_path

    def launch(self) -> None:
        """Launches game with Online-Fix"""
        self.last_played = int(time())
        self.save()
        self.update()

        # Launch directly with Steam API (only supported method)
        self._launch_with_direct_steam_api()

    def _launch_with_direct_steam_api(self) -> None:
        """Launch game through Direct Steam API Runner"""
        logging.info("Direct Steam API Runner")

        # Check executable path
        game_exec = normalize_executable_path(self.executable)
        if not game_exec:
            self.log_and_toast(_("Invalid executable path"))
            return

        # Determine environment
        in_flatpak = os.path.exists("/.flatpak-info")
        host_home = SteamLauncher.get_host_home(in_flatpak)

        # Check if Steam is running
        if not SteamLauncher.check_steam_running(in_flatpak):
            self._show_steam_not_running_dialog(in_flatpak)
            return

        if sys.platform == "win32":
            self._launch_native_windows(game_exec)
            return

        # Get Proton settings
        proton_version = shared.schema.get_string("online-fix-proton-version")
        steam_home = os.path.join(host_home, ".local/share/Steam")

        # If no Proton version is selected, try to use the first available one
        if not proton_version:
            proton_manager = ProtonManager()
            available_versions = proton_manager.get_installed_versions()
            if available_versions:
                proton_version = available_versions[0]
                shared.schema.set_string("online-fix-proton-version", proton_version)
            else:
                self._show_proton_manager_dialog()
                return

        # Check if Proton version is selected and available
        if not self._check_proton_available(proton_version, steam_home, in_flatpak):
            self._show_proton_manager_dialog()
            return

        # Get Proton path
        proton_manager = ProtonManager()
        proton_path = proton_manager.get_proton_path(proton_version)
        if not proton_path:
            self.log_and_toast(_("Failed to find Proton executable for version {}").format(proton_version))
            return

        # Create Wine prefix
        prefix_path = self._create_wine_prefix(game_exec)
        user_home = host_home if in_flatpak else os.path.expanduser("~")

        # Prepare environment variables
        env = SteamLauncher.prepare_environment(prefix_path, user_home)

        # Find Steam Runtime if enabled
        steam_runtime_path = None
        if shared.schema.get_boolean("online-fix-use-steam-runtime"):
            steam_runtime_path = SteamLauncher.find_steam_runtime(steam_home, in_flatpak)
            if not steam_runtime_path:
                # Check default location
                default_runtime = os.path.join(steam_home, "ubuntu12_32", "steam-runtime", "run.sh")
                if SteamLauncher._check_file_exists(default_runtime, in_flatpak):
                    steam_runtime_path = default_runtime
                else:
                    logging.info("[SOFL] Steam Runtime not found")

        # Build launch command
        args_before = shared.schema.get_string("online-fix-args-before")
        args_after = shared.schema.get_string("online-fix-args-after")

        cmd_argv = SteamLauncher.build_launch_command(
            proton_path,
            str(game_exec),
            steam_runtime_path,
            args_before,
            args_after
        )

        # Launch game with tracking
        process = SteamLauncher.launch_game_with_tracking(cmd_argv, env, game_exec.parent, in_flatpak)

        # Notify window about game launch for tracking
        if hasattr(shared, 'win') and shared.win and process:
            shared.win.on_game_launched(self, process)

        self.create_toast(
            _("{} launched directly with Proton {}").format(self.name, proton_version)
        )

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()


    def _launch_native_windows(self, game_exec: Path) -> None:
        """Windows runs Online-Fix games natively, so no Proton or prefix"""
        try:
            cmd_argv = (
                shlex.split(shared.schema.get_string("online-fix-args-before"))
                + [str(game_exec)]
                + shlex.split(shared.schema.get_string("online-fix-args-after"))
            )
            process = SteamLauncher.launch_game_with_tracking(cmd_argv, {}, game_exec.parent)
        except (OSError, ValueError) as e:
            self.log_and_toast(_("Failed to launch {}: {}").format(self.name, str(e)))
            return

        if hasattr(shared, 'win') and shared.win and process:
            shared.win.on_game_launched(self, process)

        self.create_toast(_("{} launched").format(self.name))

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

    def uninstall_game(self) -> None:
        """Uninstall game with confirmation"""
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
        """Removes game from list only"""
        self.log_and_toast(
            _("Game is not installed in Online-Fix directory, removing it from the list")
        )
        self.removed = True
        self.save()
        self.update()

    def _show_uninstall_confirmation(self, game_root: Path) -> None:
        """Shows uninstall confirmation dialog"""
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
        """Handles user response in uninstall dialog"""
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

    def _check_proton_available(self, proton_version: str, steam_home: str, in_flatpak: bool) -> bool:
        """Check if Proton version is available using ProtonManager"""
        try:
            proton_manager = ProtonManager()
            return proton_manager.check_proton_exists(proton_version)
        except Exception as e:
            logging.error(f"[SOFL] Error checking Proton availability: {e}")
            # Fallback to old method
            return SteamLauncher.check_proton_exists(proton_version, steam_home, in_flatpak)

    def _show_steam_not_running_dialog(self, in_flatpak: bool) -> None:
        """Show dialog when Steam is not running"""
        dialog = Adw.MessageDialog()
        dialog.set_transient_for(shared.win)
        dialog.set_heading(_("Steam is not running"))
        dialog.set_body(_("Steam must be running to play online-fix games. Would you like to start Steam?"))

        # Add responses
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("start_steam", _("Start Steam"))
        dialog.set_response_appearance("start_steam", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("start_steam")
        dialog.connect("response", lambda d, r: self._on_steam_dialog_response(r, in_flatpak))
        dialog.present()

    def _on_steam_dialog_response(self, response: str, in_flatpak: bool) -> None:
        """Handle Steam dialog response"""
        if response == "start_steam":
            import subprocess
            try:
                if sys.platform == "win32":
                    os.startfile("steam://open/main")
                elif in_flatpak:
                    # Launch Steam through flatpak-spawn
                    subprocess.Popen(["flatpak-spawn", "--host", "steam"], start_new_session=True)
                else:
                    # Launch Steam directly
                    subprocess.Popen(["steam"], start_new_session=True)

                self.log_and_toast(_("Starting Steam..."))
            except Exception as e:
                self.log_and_toast(_("Failed to start Steam: {}").format(str(e)))

    def _show_proton_manager_dialog(self) -> None:
        """Show dialog to open Proton Manager"""
        dialog = create_dialog(
            shared.win,
            _("Proton Not Available"),
            _("No Proton version is selected or installed. Please download and select a Proton version to run this game."),
            "open_proton_manager",
            _("Open Proton Manager"),
        )
        dialog.set_response_appearance("open_proton_manager", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_proton_manager_dialog_response)

    def _on_proton_manager_dialog_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        """Handle Proton Manager dialog response"""
        if response == "open_proton_manager":
            # Open preferences dialog on Proton Manager page
            if hasattr(shared.win, 'preferences') and shared.win.preferences:
                shared.win.preferences.set_visible_page(shared.win.preferences.proton_page)
                shared.win.preferences.present()
            else:
                # Create new preferences dialog if it doesn't exist
                from sofl.preferences import SOFLPreferences
                prefs = SOFLPreferences()
                prefs.set_visible_page(prefs.proton_page)
                prefs.present(shared.win)  # Pass parent window to make it a dialog
                shared.win.preferences = prefs
