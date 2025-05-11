# game.py
#
# Copyright 2022-2023 badkiko
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

import shlex
from pathlib import Path
from time import time
from typing import Any, Optional
import shutil
import os
import logging

from gi.repository import Adw, GObject, Gtk

from sofl import shared
from sofl.game_cover import GameCover
from sofl.game_data import GameData
from sofl.utils.run_executable import run_executable
from sofl.utils.create_dialog import create_dialog

from gettext import gettext as _

# pylint: disable=too-many-instance-attributes
@Gtk.Template(resource_path=shared.PREFIX + "/gtk/game.ui")
class Game(Gtk.Box):
    __gtype_name__ = "Game"

    title = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    menu_revealer = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()
    online_fix_options = Gtk.Template.Child()

    loading: int = 0
    filtered: bool = False
    game_cover: GameCover = None
    
    # Это виджет, который использует данные игры из data
    data: GameData = None

    def __init__(self, data: GameData, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.app = shared.win.get_application()
        self.data = data
        
        # Подключаем сигналы от data
        self.data.connect("update-ready", self.on_update_ready)
        self.data.connect("save-ready", self.on_save_ready)
        self.data.connect("toast", self.on_toast)

        self.set_play_icon()

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.event_contoller_motion.connect("enter", self.toggle_play, False)
        self.event_contoller_motion.connect("leave", self.toggle_play, None, None)
        self.cover_button.connect("clicked", self.main_button_clicked, False)
        self.play_button.connect("clicked", self.main_button_clicked, True)

        shared.schema.connect("changed", self.schema_changed)
        
        # Инициализируем UI на основе данных
        self.title.set_label(self.data.name)

    def on_update_ready(self, data: GameData, _args: Any) -> None:
        """Обрабатывает сигнал о необходимости обновления"""
        # Обновляем UI на основе данных
        self.title.set_label(self.data.name)
        self.emit("update-ready", {})
        
    def on_save_ready(self, data: GameData, _args: Any) -> None:
        """Обрабатывает сигнал о необходимости сохранения"""
        self.emit("save-ready", {})
        
    def on_toast(self, data: GameData, message: str) -> None:
        """Обрабатывает сигнал о необходимости показать уведомление"""
        toast = Adw.Toast.new(message)
        toast.set_priority(Adw.ToastPriority.HIGH)
        toast.set_use_markup(False)
        shared.win.toast_overlay.add_toast(toast)

    def set_loading(self, state: int) -> None:
        self.loading += state
        loading = self.loading > 0

        self.cover.set_opacity(int(not loading))
        self.spinner.set_visible(loading)

    def toggle_play(
        self, _widget: Any, _prop1: Any, _prop2: Any, state: bool = True
    ) -> None:
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(not state)
            self.menu_revealer.set_reveal_child(not state)

    def main_button_clicked(self, _widget: Any, button: bool) -> None:
        if shared.schema.get_boolean("cover-launches-game") ^ button:
            self.data.launch()
        else:
            shared.win.show_details_page(self)

    def set_play_icon(self) -> None:
        self.play_button.set_icon_name(self.data.get_play_button_icon())
        # Set button tooltip
        self.play_button.set_tooltip_text(self.data.get_play_button_label())

    def schema_changed(self, _settings: Any, key: str) -> None:
        if key == "cover-launches-game":
            self.set_play_icon()

    @GObject.Signal(name="update-ready", arg_types=[object])
    def update_ready(self, _additional_data):  # type: ignore
        """Signal emitted when the game needs updating"""

    @GObject.Signal(name="save-ready", arg_types=[object])
    def save_ready(self, _additional_data):  # type: ignore
        """Signal emitted when the game needs saving"""
        
    # Методы делегирования к data
    @property
    def game_id(self) -> str:
        return self.data.game_id
        
    @property
    def name(self) -> str:
        return self.data.name
    
    @name.setter
    def name(self, value: str) -> None:
        self.data.name = value
    
    @property
    def source(self) -> str:
        return self.data.source
    
    @property
    def base_source(self) -> str:
        return self.data.base_source
    
    @property
    def executable(self) -> str:
        return self.data.executable
    
    @executable.setter
    def executable(self, value: str) -> None:
        self.data.executable = value
    
    @property
    def hidden(self) -> bool:
        return self.data.hidden
    
    @property
    def removed(self) -> bool:
        return self.data.removed
    
    @property
    def developer(self) -> Optional[str]:
        return self.data.developer
    
    @developer.setter
    def developer(self, value: Optional[str]) -> None:
        self.data.developer = value
    
    @property
    def last_played(self) -> int:
        return self.data.last_played
    
    @property
    def added(self) -> int:
        return self.data.added
    
    @property
    def version(self) -> int:
        return self.data.version
    
    @property
    def blacklisted(self) -> bool:
        return self.data.blacklisted
    
    # Делегируем методы к data
    def launch(self) -> None:
        self.data.launch()
    
    def toggle_hidden(self, toast: bool = True) -> None:
        self.data.toggle_hidden(toast)
    
    def remove_game(self) -> None:
        self.data.remove_game()
    
    def uninstall_game(self) -> None:
        self.data.uninstall_game()
    
    def get_play_button_label(self) -> str:
        return self.data.get_play_button_label()
    
    def get_play_button_icon(self) -> str:
        return self.data.get_play_button_icon()
    
    def get_cover_path(self) -> Optional[Path]:
        return self.data.get_cover_path()
    
    def create_toast(self, message: str) -> None:
        self.data.create_toast(message)
    
    def update(self) -> None:
        self.data.update()
    
    def save(self) -> None:
        self.data.save()