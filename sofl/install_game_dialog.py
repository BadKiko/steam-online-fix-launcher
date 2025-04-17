# install_dialog.py
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

import os
from typing import Any, Optional

from gi.repository import Adw, Gtk, Gio, GLib

from sofl import shared
from sofl.details_dialog import DetailsDialog
from sofl.game import Game

class InstallDialog(Adw.Window):
    """Диалоговое окно для установки игры"""
    
    is_open = False
    selected_file: Optional[str] = None
    
    def __init__(self) -> None:
        super().__init__(
            title=_("Install Game"),
            modal=True,
            destroy_with_parent=True,
            width_request=450,
            height_request=300,
            resizable=False,
        )
        
        InstallDialog.is_open = True
        self.connect("close-request", self.on_close_request)
        
        # Основное содержимое
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24, 
                           margin_bottom=24, margin_start=24, margin_end=24)
        
        # Заголовок
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title = Gtk.Label(label=_("Install Game"), 
                         halign=Gtk.Align.START)
        title.add_css_class("title-2")
        description = Gtk.Label(
            label=_("Select installation file to continue"),
            halign=Gtk.Align.START
        )
        description.add_css_class("dim-label")
        
        header_box.append(title)
        header_box.append(description)
        self.vbox.append(header_box)
        
        # Выбор файла
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.file_entry = Gtk.Entry(hexpand=True, placeholder_text=_("Installation file path"))
        self.file_entry.set_editable(False)
        
        browse_button = Gtk.Button(label=_("Browse"))
        browse_button.connect("clicked", self.on_browse_clicked)
        
        file_box.append(self.file_entry)
        file_box.append(browse_button)
        self.vbox.append(file_box)
        
        # Кнопки действий
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, 
                            halign=Gtk.Align.END, margin_top=12)
        
        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.connect("clicked", lambda _: self.close())
        
        self.next_button = Gtk.Button(label=_("Next"))
        self.next_button.add_css_class("suggested-action")
        self.next_button.set_sensitive(False)
        self.next_button.connect("clicked", self.on_next_clicked)
        
        button_box.append(cancel_button)
        button_box.append(self.next_button)
        self.vbox.append(button_box)
        
        # Настройка содержимого окна
        self.set_content(self.vbox)
        
    def on_browse_clicked(self, _button: Gtk.Button) -> None:
        """Открывает диалог выбора файла"""
        dialog = Gtk.FileChooserDialog(
            title=_("Select Installation File"),
            action=Gtk.FileChooserAction.OPEN,
            transient_for=self,
            modal=True
        )
        
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("Open"), Gtk.ResponseType.ACCEPT)
        
        # Фильтры для исполняемых файлов
        exe_filter = Gtk.FileFilter()
        exe_filter.set_name(_("Executable Files"))
        exe_filter.add_pattern("*.exe")
        exe_filter.add_mime_type("application/x-executable")
        dialog.add_filter(exe_filter)
        
        # Фильтр для всех файлов
        all_filter = Gtk.FileFilter()
        all_filter.set_name(_("All Files"))
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        
        dialog.connect("response", self.on_file_dialog_response)
        dialog.present()
    
    def on_file_dialog_response(self, dialog: Gtk.FileChooserDialog, response_id: int) -> None:
        """Обрабатывает ответ от диалога выбора файла"""
        if response_id == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            self.selected_file = file.get_path()
            self.file_entry.set_text(self.selected_file)
            self.next_button.set_sensitive(True)
        
        dialog.destroy()
    
    def on_next_clicked(self, _button: Gtk.Button) -> None:
        """Переходит к следующему шагу установки игры"""
        if self.selected_file:
            # Закрываем текущее окно
            self.close()
            
            # Открываем обычное диалоговое окно создания игры
            dialog = DetailsDialog()
            # Предустановим путь к исполняемому файлу
            dialog.set_executable(self.selected_file)
            # Можем также попытаться предложить имя игры из имени файла
            filename = os.path.basename(self.selected_file)
            game_name = os.path.splitext(filename)[0]
            dialog.set_name(game_name)
            
            dialog.present(shared.win)
    
    def on_close_request(self, *_args: Any) -> bool:
        """Вызывается при закрытии окна"""
        InstallDialog.is_open = False
        return False