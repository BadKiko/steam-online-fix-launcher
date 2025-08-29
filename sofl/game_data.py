# game_data.py
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

import shlex
from pathlib import Path
from time import time
from typing import Any, Optional, Callable

from gi.repository import GObject

from sofl import shared
from sofl.utils.run_executable import run_executable

from sofl.utils.path_utils import normalize_executable_path

from gettext import gettext as _


class GameData(GObject.Object):
    """
    Base class for storing game data and logic.
    This class does not contain user interface elements.
    """

    added: int
    executable: str
    game_id: str
    source: str
    base_source: str
    hidden: bool = False
    last_played: int = 0
    name: str
    developer: Optional[str] = None
    removed: bool = False
    blacklisted: bool = False
    version: int = 0

    # Signals for communication with widget
    __gsignals__ = {
        "update-ready": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "save-ready": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "toast": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, data: dict[str, Any]):
        super().__init__()
        self.version = shared.SPEC_VERSION

        # Initialize default values for required attributes
        self.name = data.get("name", _("Unknown Game"))
        self.executable = data.get("executable", "")
        self.game_id = data.get("game_id", "")
        self.source = data.get("source", "")
        self.added = data.get("added", int(time()))
        self.hidden = data.get("hidden", False)
        self.last_played = data.get("last_played", 0)
        self.developer = data.get("developer", None)
        self.removed = data.get("removed", False)
        self.blacklisted = data.get("blacklisted", False)

        self.update_values(data)
        self.base_source = self.source.split("_")[0]

    def update_values(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            # Convert executables to strings
            if key == "executable" and isinstance(value, list):
                value = shlex.join(value)
            setattr(self, key, value)

    def update(self) -> None:
        """Signals the need for interface update"""
        self.emit("update-ready", {})

    def save(self) -> None:
        """Signals the need for data saving"""
        self.emit("save-ready", {})

    def create_toast(self, message: str) -> None:
        """Signals the need to show notification"""
        self.emit("toast", message)

    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play")

    def get_play_button_icon(self) -> str:
        """Return the icon name for the play button"""
        return (
            "help-about-symbolic"
            if shared.schema.get_boolean("cover-launches-game")
            else "media-playback-start-symbolic"
        )

    def launch(self) -> None:
        """Launch the game"""
        self.last_played = int(time())
        self.save()
        self.update()

        run_executable(normalize_executable_path(self.executable))

        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()

        # The variable is the title of the game
        self.create_toast(_("{} launched").format(self.name))

    def toggle_hidden(self, toast: bool = True) -> None:
        """Toggle game hidden state"""
        self.hidden = not self.hidden
        self.save()
        self.update()

        if toast:
            # The variable is the title of the game
            self.create_toast(
                (_("{} hidden") if self.hidden else _("{} unhidden")).format(self.name)
            )

    def remove_game(self) -> None:
        """Mark game as removed"""
        self.removed = True
        self.save()
        self.update()

        # The variable is the title of the game
        self.create_toast(_("{} removed").format(self.name))

    def get_cover_path(self) -> Optional[Path]:
        """Get the path to the game's cover image"""
        cover_path = shared.covers_dir / f"{self.game_id}.gif"
        if cover_path.is_file():
            return cover_path  # type: ignore

        cover_path = shared.covers_dir / f"{self.game_id}.tiff"
        if cover_path.is_file():
            return cover_path  # type: ignore

        return None
