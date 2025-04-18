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
from pathlib import Path
from sys import platform
from typing import Any, Optional

from gi.repository import Adw, Gtk, GLib, Gio

from sofl import shared
from sofl.game import Game

# Constants
ONLINE_FIX_PASSWORD = "online-fix.me"
GAME_TITLE_REGEX = r"(^.*?)\.v"

@Gtk.Template(resource_path=shared.PREFIX + "/gtk/install-dialog.ui")
class InstallDialog(Adw.Dialog):
    __gtype_name__ = "InstallDialog"

    # Template children
    game_path = Gtk.Template.Child()
    game_title = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    apply_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    
    is_open: bool = False

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)
        
        # Create file dialog
        self.file_chooser = Gtk.FileDialog()
        
        # Connect path change handler
        self.game_path.connect("notify::text", self.on_path_changed)
        
        # Hide status page, we'll use toast instead
        self.status_page.set_visible(False)
        
        # If game already exists, fill in the fields
        if game:
            self.game_path.set_text(game.path if game.path else "")
            self.game_title.set_text(game.name if game.name else "")

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
                path = file.get_path()
                # Format path for display
                display_path = self.format_path_for_display(path)
                self.game_path.set_text(path)
                
                # Get file info through GIO
                file_info = file.query_info("standard::*", Gio.FileQueryInfoFlags.NONE, None)
                
                if file_info and file_info.get_file_type() == Gio.FileType.REGULAR:
                    # Explicitly trigger file check after setting the path
                    self.check_game_file(path, file)
                else:
                    self.show_toast("Selected item is not a valid file")
                    self.apply_button.set_sensitive(False)
                    
        except GLib.Error as error:
            self.show_toast(f"Error accessing file: {error.message}")
            return

    def format_path_for_display(self, path: str) -> str:
        """Format path for display, handling Flatpak paths"""
        if platform == "linux":
            # Remove the path prefix if picked via Flatpak portal
            path = re.sub(r"/run/user/\d+/doc/[^/]+/", "", path)
            # Replace the home directory with "~"
            if hasattr(shared, 'home') and shared.home:
                path = path.replace(str(shared.home), "~")
        return path

    def on_path_changed(self, entry, pspec):
        path = self.game_path.get_text()
        if path:
            file = Gio.File.new_for_path(path)
            self.check_game_file(path, file)
        else:
            self.show_toast("Specify a game file path to check")
            self.apply_button.set_sensitive(False)

    def check_game_file(self, path, file=None):
        """Check if the file is a valid game file
        
        Args:
            path: The path to the file
            file: Optional Gio.File object for the file
        """
        if file is None:
            file = Gio.File.new_for_path(path)
        
        # Check if file exists through GIO
        try:
            if not file.query_exists():
                self.show_toast("File does not exist")
                self.apply_button.set_sensitive(False)
                return
                
            # Open the file using GIO to handle Flatpak portal access
            file_stream = None
            try:
                file_stream = file.read()
            except GLib.Error as err:
                self.show_toast(f"Cannot access file: {err.message}")
                self.apply_button.set_sensitive(False)
                return
            finally:
                if file_stream:
                    file_stream.close()
                
            # File exists and is accessible, continue with checking
            if path.lower().endswith(".rar"):
                try:
                    # Check if the archive is password protected
                    with rarfile.RarFile(path) as rar_file:
                        try:
                            # Try to view information about the first file without a password
                            first_file = rar_file.infolist()[0]
                            if first_file.needs_password():
                                # Try with online-fix.me password
                                try:
                                    if self.validate_with_password(path):
                                        self.show_toast("Confirmed: This is an Online-Fix game")
                                        self.extract_game_title(os.path.basename(path))
                                        self.apply_button.set_sensitive(True)
                                    else:
                                        self.show_toast("Wrong password, this is not an Online-Fix game")
                                        self.apply_button.set_sensitive(False)
                                except Exception as e:
                                    self.show_toast(f"Error checking archive: {str(e)}")
                                    self.apply_button.set_sensitive(False)
                            else:
                                self.show_toast("Archive is not password protected, this is not an Online-Fix game")
                                self.apply_button.set_sensitive(False)
                        except rarfile.BadRarFile as e:
                            self.show_toast(f"RAR archive error: {str(e)}")
                            self.apply_button.set_sensitive(False)
                except (rarfile.BadRarFile, Exception) as e:
                    self.show_toast(f"Error opening archive: {str(e)}")
                    self.apply_button.set_sensitive(False)
            elif path.lower().endswith(".exe"):
                # Placeholder for exe files
                self.show_toast("EXE files are not supported yet")
                self.apply_button.set_sensitive(False)
            else:
                self.show_toast("Unsupported file format")
                self.apply_button.set_sensitive(False)
                
        except GLib.Error as error:
            self.show_toast(f"Error accessing file: {error.message}")
            self.apply_button.set_sensitive(False)

    def validate_with_password(self, path):
        try:
            with rarfile.RarFile(path, 'r') as rar_file:
                # Set the password
                rar_file.setpassword(ONLINE_FIX_PASSWORD)
                # Try to get file list
                rar_file.infolist()
                # If no exception was thrown, the password works
                return True
        except (rarfile.BadRarFile, rarfile.PasswordRequired, Exception):
            return False

    def extract_game_title(self, filename):
        match = re.search(GAME_TITLE_REGEX, filename)
        if match:
            game_title = match.group(1).replace(".", " ")
            self.game_title.set_text(game_title)

    def show_toast(self, message):
        """Show a toast notification using the toast overlay"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)  # 3 seconds
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.toast_overlay.add_toast(toast)

    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open

