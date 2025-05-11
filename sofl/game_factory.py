# game_factory.py
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

from typing import Any

from sofl.game import Game
from sofl.game_data import GameData
from sofl.onlinefix_game import OnlineFixGameData

class GameFactory:
    """Factory for creating the appropriate game type based on source"""
    
    @staticmethod
    def create_game(data: dict[str, Any], **kwargs: Any) -> Game:
        """
        Create a game instance of the appropriate type.
        
        Args:
            data: Dictionary with game data
            kwargs: Additional keyword arguments
            
        Returns:
            An instance of Game with appropriate GameData
        """
        source = data.get("source", "")
        
        # Create the appropriate GameData instance based on source
        if source == "online-fix" or source.startswith("online-fix_"):
            game_data = OnlineFixGameData(data)
        else:
            game_data = GameData(data)
        
        # Create Game instance with appropriate GameData
        return Game(game_data, **kwargs) 