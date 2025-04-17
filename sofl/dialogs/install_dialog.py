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

from typing import Any, Optional

from gi.repository import Adw, Gtk

from sofl import shared
from sofl.game import Game

@Gtk.Template(resource_path=shared.PREFIX + "/gtk/install-dialog.ui")
class InstallDialog(Adw.Dialog):
    __gtype_name__ = "InstallDialog"

    is_open: bool = False

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)


    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open
