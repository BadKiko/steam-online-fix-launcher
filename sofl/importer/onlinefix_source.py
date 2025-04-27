# onlinefix_source.py
#
# Copyright 2025 badkiko
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

from sofl.importer.source import Source, SourceIterable

class OnlineFixSourceIterable(SourceIterable):
    """Iterator for Online-Fix games"""
    
    source: "OnlineFixSource"
    
    def __iter__(self):
        """Generator method producing games"""
        # Logic for iterating over Online-Fix games will go here
        # Currently, no specific implementation is needed
        yield None


class OnlineFixSource(Source):
    """Source for Online-Fix games"""
    
    source_id = "online-fix"
    name = "Online-Fix"
    iterable_class = OnlineFixSourceIterable
    available_on = {"linux", "win32", "darwin"}  # Available on all platforms
    
    def __init__(self) -> None:
        super().__init__()
        self.locations = []  # We have no special locations to check
    
    def make_executable(self, *args, **kwargs) -> str:
        """Creates a command to launch the game"""
        return kwargs.get("executable", "") 