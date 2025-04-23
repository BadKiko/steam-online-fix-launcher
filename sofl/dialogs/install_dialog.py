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
from pathlib import Path
from sys import platform
from typing import Any, Optional

from gi.repository import Adw, Gtk, GLib, Gio

from sofl import shared
from sofl.game import Game

# Constants
ONLINE_FIX_PASSWORD = "online-fix.me"
GAME_TITLE_REGEX = r"(^.*?)\.v"
TOAST_DEBOUNCE_DELAY = 1000  # Миллисекунды

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
    _toast_debounce_id: Optional[int] = None
    _last_toast_message: Optional[str] = None

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
                    # Проверяем архив с паролем напрямую
                    if self.validate_with_password(path):
                        self.show_toast("Confirmed: This is an Online-Fix game")
                        self.extract_game_title(os.path.basename(path))
                        self.apply_button.set_sensitive(True)
                    else:
                        # Если с паролем не получилось, попробуем проверить архив более подробно
                        self.check_rar_detailed(path)
                except Exception as e:
                    self.show_toast(f"Error checking archive: {str(e)}")
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
            
    def check_rar_detailed(self, path):
        """Более подробная проверка RAR-архива"""
        try:
            # Попытка открыть архив без пароля для проверки структуры
            with rarfile.RarFile(path) as rar_file:
                try:
                    # Получаем список файлов
                    info_list = rar_file.infolist()
                    
                    # Выводим информацию о количестве файлов для диагностики
                    if not info_list:
                        self.show_toast("RAR archive appears empty (0 files found)")
                        self.apply_button.set_sensitive(False)
                        return
                    
                    # Проверяем, защищен ли первый файл паролем
                    first_file = info_list[0]
                    if first_file.needs_password():
                        self.show_toast(f"Archive is password protected. Testing with password...")
                        # Если файл требует пароль, ещё раз проверим с паролем
                        if self.validate_with_password(path):
                            self.show_toast("Confirmed: This is an Online-Fix game")
                            self.extract_game_title(os.path.basename(path))
                            self.apply_button.set_sensitive(True)
                        else:
                            self.show_toast("Wrong password, this is not an Online-Fix game")
                            self.apply_button.set_sensitive(False)
                    else:
                        self.show_toast(f"Archive contains {len(info_list)} files but is not password protected")
                        self.apply_button.set_sensitive(False)
                        
                except rarfile.BadRarFile as e:
                    self.show_toast(f"RAR archive error: {str(e)}")
                    self.apply_button.set_sensitive(False)
                except IndexError:
                    self.show_toast("Invalid RAR archive structure")
                    self.apply_button.set_sensitive(False)
        except Exception as e:
            self.show_toast(f"Error analyzing archive: {str(e)}")
            self.apply_button.set_sensitive(False)

    def validate_with_password(self, path):
        try:
            with rarfile.RarFile(path, 'r') as rar_file:
                # Set the password
                rar_file.setpassword(ONLINE_FIX_PASSWORD)
                # Try to get file list
                files = rar_file.infolist()
                # Если архив имеет хотя бы один файл и с паролем открылся без ошибок
                return len(files) > 0
        except (rarfile.BadRarFile, rarfile.PasswordRequired, Exception) as e:
            self.show_toast(f"Password verification failed: {str(e)}")
            return False

    def extract_game_title(self, filename):
        match = re.search(GAME_TITLE_REGEX, filename)
        if match:
            game_title = match.group(1).replace(".", " ")
            self.game_title.set_text(game_title)

    def show_toast(self, message):
        """Show a toast notification using the toast overlay with debouncing"""
        # Если сообщение такое же как предыдущее, сбросим таймер
        if self._toast_debounce_id is not None:
            GLib.source_remove(self._toast_debounce_id)
            self._toast_debounce_id = None
        
        # Запомним последнее сообщение
        self._last_toast_message = message
        
        # Устанавливаем новый таймер для дебаунсинга
        self._toast_debounce_id = GLib.timeout_add(
            TOAST_DEBOUNCE_DELAY, 
            self._do_show_toast
        )

    def _do_show_toast(self):
        """Фактически показать тост после дебаунсинга"""
        if self._last_toast_message:
            toast = Adw.Toast.new(self._last_toast_message)
            toast.set_timeout(3)  # 3 секунды
            toast.set_priority(Adw.ToastPriority.HIGH)
            self.toast_overlay.add_toast(toast)
        
        # Сбрасываем ID таймера и сообщение
        self._toast_debounce_id = None
        self._last_toast_message = None
        
        # Возвращаем False, чтобы остановить повторения таймера
        return False

    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open

