# details_window.py
#
# Copyright 2022-2024 badkiko
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

# pyright: reportAssignmentType=none

import os
import re
import rarfile
import subprocess
import tempfile
import logging
import threading
from pathlib import Path
from sys import platform
from typing import Any, Optional, Callable
from time import time

from gi.repository import Adw, Gtk, GLib, Gio

from sofl import shared
from sofl.game import Game
from sofl.game_factory import GameFactory
from sofl.installer.online_fix_installer import OnlineFixInstaller
from sofl.details_dialog import DetailsDialog
from sofl.utils.flatpak import is_flatpak_path, copy_flatpak_file, log_message

# Constants
ONLINE_FIX_PASSWORD = "online-fix.me"
GAME_TITLE_REGEX = r"(^.*?)\.v"
TOAST_DEBOUNCE_DELAY = 1000  # Milliseconds

# Logging setup
logger = logging.getLogger(__name__)

@Gtk.Template(resource_path=shared.PREFIX + "/gtk/install-dialog.ui")
class InstallDialog(Adw.Dialog):
    __gtype_name__ = "InstallDialog"

    # Template children
    game_path = Gtk.Template.Child()
    game_title = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    apply_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    progress_spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    
    is_open: bool = False
    _toast_debounce_id: Optional[int] = None
    _last_toast_message: Optional[str] = None
    _current_task: Optional[threading.Thread] = None

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)
        
        # Create file dialog
        self.file_chooser = Gtk.FileDialog()
        
        # Hide status page, we'll use toast instead
        self.status_page.set_visible(False)
        
        # Connect Install button handler
        self.apply_button.connect("clicked", self.on_install_clicked)
        
        # If initialized with a game, fill in the fields
        if game:
            self.game_path.set_text(game.path if game.path else "")
            self.game_title.set_text(game.name if game.name else "")
            
        # Initialize the installer
        self.installer = OnlineFixInstaller()

    def show_progress(self, show: bool, message: Optional[str] = None) -> None:
        """Shows or hides the loading indicator
        
        Args:
            show: True to show, False to hide
            message: Message to display in the indicator
        """
        def update_ui():
            # First activate the spinner if showing progress
            if show:
                # Important: activate spinner before switching pages
                self.progress_spinner.set_spinning(True)
                # Sometimes spinner doesn't update due to GTK optimizations,
                # so make it explicitly visible
                self.progress_spinner.set_visible(True)
            
            # Switch visible stack depending on loading state
            stack_page = "loading" if show else "content"
            self.main_stack.set_visible_child_name(stack_page)
            
            # Update message text if provided
            if message:
                self.progress_label.set_label(message)
            
            # Deactivate Add button during loading
            if show:
                self.apply_button.set_sensitive(False)
            else:
                # If hiding - stop spinner
                self.progress_spinner.set_spinning(False)
            
            # Force UI update without using deprecated events_pending
            # in GTK4 this is automatically handled through GLib.MainContext
            
            return False
            
        # Execute in main thread since this is a UI operation
        GLib.idle_add(update_ui)

    def run_async(self, func: Callable, callback: Optional[Callable] = None) -> None:
        """Runs a function asynchronously in a separate thread
        
        Args:
            func: Function to execute
            callback: Callback after completion (will be executed in main thread)
        """
        def thread_func():
            try:
                # Ensure UI updates before starting long operation
                GLib.idle_add(lambda: None)
                
                result = func()
                if callback:
                    GLib.idle_add(lambda: callback(result))
            except Exception as e:
                self.log_message(f"Error in asynchronous operation: {str(e)}", logging.ERROR)
                if callback:
                    GLib.idle_add(lambda: callback(None))
            finally:
                # Hide progress indicator after completion
                GLib.idle_add(lambda: self.show_progress(False))
                self._current_task = None
        
        # Stop current task if it exists
        if self._current_task and self._current_task.is_alive():
            self.log_message("Cancelling previous task")
            # Just create a new thread (Python doesn't allow safely stopping threads)
        
        # Create and start new thread
        self._current_task = threading.Thread(target=thread_func)
        self._current_task.daemon = True
        self._current_task.start()

    @Gtk.Template.Callback()
    def on_file_chooser_clicked(self, button):
        # Create filters
        filter_rar = Gtk.FileFilter()
        filter_rar.set_name("RAR files")
        filter_rar.add_pattern("*.rar")
        
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("EXE files")
        filter_exe.add_pattern("*.exe")
        
        # Create filter list
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_rar)
        filters.append(filter_exe)
        
        # Configure file chooser to open files
        self.file_chooser.set_filters(filters)
        self.file_chooser.set_title("Select game file")
        
        # Use portal to open file
        self.file_chooser.open(None, None, self.on_file_chooser_response)

    def on_file_chooser_response(self, dialog, result):
        try:
            file = self.file_chooser.open_finish(result)
            if file:
                original_path = file.get_path()
                path = original_path
                
                # Show progress in UI
                self.show_progress(True, "Checking file...")
                
                # Check if we need to copy the file from Flatpak
                if self.is_flatpak_path(path):
                    self.log_message(f"Detected Flatpak path: {path}")
                    
                    # Asynchronously copy the file
                    self.show_progress(True, "Copying file...")
                    
                    def copy_file():
                        return self.copy_flatpak_file(path)
                    
                    def after_copy(new_path):
                        if new_path and new_path != path:
                            self.log_message(f"Using copied file: {new_path}")
                            self.game_path.set_text(new_path)
                        
                        # Check file after copying
                        self.check_file_async(new_path or path)
                    
                    self.run_async(copy_file, after_copy)
                else:
                    # Format path for display
                    self.game_path.set_text(path)
                    
                    # Asynchronously check file
                    self.check_file_async(path)
                    
        except GLib.Error as error:
            self.log_message(f"Error accessing file: {error.message}", logging.ERROR)
            self.show_toast(f"Error accessing file: {error.message}")
            return

    def check_file_async(self, path: str) -> None:
        """Asynchronous game file check
        
        Args:
            path: Path to the file
        """
        self.show_progress(True, "Checking game file...")
        
        def check_task():
            file = Gio.File.new_for_path(path)
            try:
                if not file.query_exists():
                    self.log_message(f"File does not exist: {path}", logging.ERROR)
                    self.show_toast("File does not exist")
                    return False
                
                # Check file
                try:
                    file_stream = file.read()
                    file_stream.close()
                    
                    # Optimized archive check
                    if path.lower().endswith(".rar"):
                        self.show_progress(True, "Checking archive...")
                        
                        # Quick archive check - just open it with password without extracting
                        if self.verify_rar_password(path):
                            # Extract game title from filename
                            self.extract_game_title(os.path.basename(path))
                            self.show_toast("Confirmed: This is an Online-Fix game")
                            return True
                        else:
                            self.show_toast("Not an Online-Fix game or invalid archive")
                            return False
                            
                    elif path.lower().endswith(".exe"):
                        self.log_message("EXE files are not supported yet")
                        self.show_toast("EXE files are not supported yet")
                        return False
                    else:
                        self.log_message("Unsupported file format")
                        self.show_toast("Unsupported file format")
                        return False
                except Exception as e:
                    self.log_message(f"Error checking file: {str(e)}", logging.ERROR)
                    self.show_toast(f"Error checking file: {str(e)}")
                    return False
            except GLib.Error as error:
                self.log_message(f"Error accessing file: {error.message}", logging.ERROR)
                self.show_toast(f"Error accessing file: {error.message}")
                return False
        
        def after_check(result):
            self.apply_button.set_sensitive(bool(result))
        
        self.run_async(check_task, after_check)

    def on_path_changed(self, entry, pspec):
        path = self.game_path.get_text()
        if path:
            # Check if we need to copy the file from Flatpak
            if self.is_flatpak_path(path):
                self.show_progress(True, "Detected Flatpak path...")
                
                def copy_file():
                    return self.copy_flatpak_file(path)
                
                def after_copy(new_path):
                    if new_path and new_path != path:
                        self.log_message(f"Using copied file: {new_path}")
                        self.game_path.set_text(new_path)
                    
                    self.check_file_async(new_path or path)
                
                self.run_async(copy_file, after_copy)
            else:
                self.check_file_async(path)
        else:
            self.show_toast("Specify a game file path to check")
            self.apply_button.set_sensitive(False)

    def format_path_for_display(self, path: str) -> str:
        """Format path for display, handling Flatpak paths"""
        if platform == "linux":
            # Remove the path prefix if picked via Flatpak portal
            path = re.sub(r"/run/user/\d+/doc/[^/]+/", "", path)
            # Replace the home directory with "~"
            if hasattr(shared, 'home') and shared.home:
                path = path.replace(str(shared.home), "~")
        return path

    def is_flatpak_path(self, path: str) -> bool:
        """Checks if the path is a Flatpak path"""
        return is_flatpak_path(path)

    def copy_flatpak_file(self, path: str) -> str:
        """Delegates to utility function"""
        return copy_flatpak_file(path)

    def verify_rar_password(self, path: str) -> bool:
        """Quick verification of password-protected archive without extraction
        
        Args:
            path: Path to the file
            
        Returns:
            bool: True if the archive is valid and opens with password, otherwise False
        """
        try:
            # Method 1: Use unrar directly for archive testing (fastest)
            self.log_message("Quick archive verification via unrar")
            try:
                unrar_path = rarfile.UNRAR_TOOL
                result = subprocess.run(
                    [unrar_path, "t", "-p" + ONLINE_FIX_PASSWORD, "-idp", path], 
                    capture_output=True, 
                    text=True, 
                    check=False,
                    timeout=10  # Timeout in seconds
                )
                
                if result.returncode == 0:
                    self.log_message("Archive passed verification via unrar")
                    return True
                else:
                    self.log_message(f"Archive failed verification: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                self.log_message("Archive verification took too long, cancelling")
                return False
            except Exception as e:
                self.log_message(f"Error during verification via unrar: {str(e)}")
                
                # Method 2: Use rarfile for verification (fallback)
                self.log_message("Checking archive via rarfile")
                try:
                    with rarfile.RarFile(path) as rf:
                        rf.setpassword(ONLINE_FIX_PASSWORD)
                        # Just get file list, don't extract
                        info_list = rf.infolist()
                        # If we got file list with password, the archive is correct
                        return len(info_list) > 0
                except rarfile.PasswordRequired:
                    # If password required but not the one we specified, it's not an Online-Fix archive
                    self.log_message("Archive is protected by a different password")
                    return False
                except Exception as e:
                    self.log_message(f"Error during verification via rarfile: {str(e)}")
                    return False
        except Exception as e:
            self.log_message(f"General error during archive verification: {str(e)}")
            return False

    def extract_game_title(self, filename):
        """Extracts game title from filename"""
        match = re.search(GAME_TITLE_REGEX, filename)
        if match:
            game_title = match.group(1).replace(".", " ")
            self.game_title.set_text(game_title)

    def show_toast(self, message):
        """Show a toast notification using the toast overlay with debouncing"""
        # Call unified logging method
        self.log_message(message)
        
        # If message is the same as previous, reset timer
        if self._toast_debounce_id is not None:
            GLib.source_remove(self._toast_debounce_id)
            self._toast_debounce_id = None
        
        # Remember last message
        self._last_toast_message = message
        
        # Set new timer for debouncing
        self._toast_debounce_id = GLib.timeout_add(
            TOAST_DEBOUNCE_DELAY, 
            self._do_show_toast
        )

    def log_message(self, message, level=logging.INFO):
        """Delegates to utility function"""
        log_message(message, level)

    def _do_show_toast(self):
        """Actually show toast after debouncing"""
        if self._last_toast_message:
            toast = Adw.Toast.new(self._last_toast_message)
            toast.set_timeout(3)  # 3 seconds
            toast.set_priority(Adw.ToastPriority.HIGH)
            self.toast_overlay.add_toast(toast)
        
        # Reset timer ID and message
        self._toast_debounce_id = None
        self._last_toast_message = None
        
        # Return False to stop timer repetitions
        return False

    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open

    def on_install_clicked(self, button):
        """Handler for Install button click (Game installation)"""
        # Validate input
        if not self._validate_installation_input():
            return
            
        # Show progress
        self.show_progress(True, "Preparing for installation...")
        
        # Start installation asynchronously
        self.run_async(self._install_game_task, self._handle_installation_result)
    
    def _validate_installation_input(self):
        """Validates installation input parameters
        
        Returns:
            bool: True if input is valid, False otherwise
        """
        # Get archive path and game name
        archive_path = self.game_path.get_text()
        game_name = self.game_title.get_text()
        
        if not archive_path or not game_name:
            self.show_toast("Select an archive and specify game name")
            return False
            
        # Check if file exists
        if not os.path.exists(archive_path):
            self.show_toast("File does not exist")
            return False
            
        return True
    
    def _install_game_task(self):
        """Task for game installation
        
        Returns:
            tuple: (success, result, executable)
        """
        archive_path = self.game_path.get_text()
        game_name = self.game_title.get_text()
        
        def progress_update(progress, message):
            GLib.idle_add(lambda: self.update_installation_progress(progress, message))
            
        # Call installation method from installer
        success, result, executable = self.installer.install_game(
            archive_path, 
            game_name, 
            progress_update
        )
        
        return success, result, executable
    
    def _handle_installation_result(self, result):
        """Handles installation result
        
        Args:
            result: Installation result tuple or None on error
        """
        if not result:
            self.show_toast("Error during game installation")
            return
            
        success, install_path, executable = result
        
        if success:
            self.show_toast(f"Game successfully installed in: {install_path}")
            self._add_game_to_library(install_path, executable)
        else:
            self.show_toast(f"Error during game installation: {install_path}")
    
    def _add_game_to_library(self, install_path, executable):
        """Adds installed game to library
        
        Args:
            install_path: Path where game was installed
            executable: Path to game executable
        """
        game_name = self.game_title.get_text()
        
        try:
            game_id = self._generate_game_id()
            new_game = self._create_game_object(game_id, game_name, install_path, executable)
            
            # Add game to store
            shared.store.add_game(new_game, {}, run_pipeline=False)
            new_game.save()
            
            # Hide current installation dialog
            self.hide()
            
            # Show game details dialog to complete setup
            GLib.idle_add(lambda: self.show_details_dialog(new_game))
            
        except Exception as e:
            self._handle_game_creation_error(e, install_path)
    
    def _generate_game_id(self):
        """Generates a unique game ID for online-fix games
        
        Returns:
            str: Generated game ID
        """
        source_id = "online-fix"
        numbers = [0]
        prefix = "online-fix_"
        
        for game_id in shared.store.source_games.get(source_id, set()):
            if not game_id.startswith(prefix):
                continue
            try:
                numbers.append(int(game_id.replace(prefix, "", 1)))
            except ValueError:
                pass
        
        game_number = max(numbers) + 1
        return f"{prefix}{game_number}"
    
    def _create_game_object(self, game_id, game_name, install_path, executable):
        """Creates a Game object for the installed game
        
        Args:
            game_id: Generated game ID
            game_name: Game name
            install_path: Path where game was installed
            executable: Path to game executable
            
        Returns:
            Game: Created game object
        """
        executable_path = ""
        if executable:
            executable_path = str(Path(install_path) / executable)
            
        return GameFactory.create_game({
            "game_id": game_id,
            "hidden": False,
            "source": "online-fix",
            "name": game_name,
            "path": install_path,
            "executable": executable_path,
            "added": int(time()),
        })
    
    def _handle_game_creation_error(self, error, install_path):
        """Handles error during game creation
        
        Args:
            error: Exception that occurred
            install_path: Path where game was installed
        """
        self.log_message(f"Error adding game: {str(error)}", logging.ERROR)
        self.show_toast(f"Game installed but not added to library: {str(error)}")
        
        # Close dialog after successful installation via timeout
        GLib.timeout_add(1500, lambda: self.hide() or False)
        
    def show_details_dialog(self, game):
        """Shows dialog with game details for editing
        
        Args:
            game: Game to edit
        """
        try:
            if DetailsDialog.is_open:
                return
            
            # Set flag for details dialog
            DetailsDialog.install_mode = True
            
            # Create and show dialog
            dialog = DetailsDialog(game)
            dialog.present(self.get_root())
        except Exception as e:
            self.log_message(f"Error opening details dialog: {str(e)}", logging.ERROR)
            self.show_toast(f"Could not open game configuration dialog: {str(e)}")
    
    def update_installation_progress(self, progress: float, message: str) -> bool:
        """Updates installation progress indicator
        
        Args:
            progress: Progress from 0 to 1
            message: Current status message
            
        Returns:
            bool: False for one-time call via GLib.idle_add
        """
        self.show_progress(True, message)
        return False

