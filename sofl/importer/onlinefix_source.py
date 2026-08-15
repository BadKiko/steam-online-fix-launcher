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

import os
import difflib
import logging
from pathlib import Path
from time import time

from sofl import shared
from sofl.game import Game
from sofl.onlinefix_game import OnlineFixGameData
from sofl.importer.source import Source, SourceIterable

class OnlineFixSourceIterable(SourceIterable):
    """Iterator for Online-Fix games with Fuzzy Matching Logic"""

    source: "OnlineFixSource"

    def __iter__(self):
        """Generator method producing games"""
        install_path = shared.schema.get_string("online-fix-install-path")
        if not install_path:
            return
            
        root_path = Path(os.path.expanduser(install_path))
        if not root_path.exists():
            return

        logging.info(f"Scanning Online-Fix folder: {root_path}")

        for game_dir in root_path.iterdir():
            if not game_dir.is_dir():
                continue
            
            # Find the best candidate
            exe_path = self._find_executable(game_dir)
            if not exe_path:
                continue
                
            game_name = game_dir.name
            # Unique ID based on folder name
            game_id = f"online-fix:{game_name}"
            
            raw_data = {
                "game_id": game_id,
                "name": game_name,
                "source": "online-fix",
                "executable": str(exe_path),
                "added": int(time()),
                "last_played": 0,
                "hidden": False,
                "removed": False
            }
            
            data = OnlineFixGameData(raw_data)
            
            game = Game(data)
            yield game

    def _find_executable(self, folder: Path) -> Path | None:
        """
        Uses Fuzzy Logic and Scoring to find the true Game Executable.
        """

        # 1. THE IGNORE LIST (Case insensitive)
        # Common junk found in pirate releases and game engines
        BLACKLIST = {
            # Unity / Unreal Engine Trash
            "unitycrashhandler64.exe", "unitycrashhandler.exe",
            "crashreportclient.exe", "crashreporter.exe",
            "ue4prereqsetup_x64.exe", "ue4prereqsetup.exe",
            "uplay_crash_reporter.exe",

            # Installers / Redistributables
            "unins000.exe", "unins001.exe", "uninstall.exe", "setup.exe",
            "dxsetup.exe", "vcredist_x64.exe", "vcredist_x86.exe",
            "dotnetfx.exe", "physx_systemsoftware.exe",

            # Anti-Cheats / Launchers
            "easyanticheat_setup.exe", "battleye_installer.exe",
            "launcher.exe", # Often just a menu, prefer the game exe if possible
            "dowser.exe"    # Paradox Launcher trash
        }

        # Gather all EXEs
        exes = list(folder.glob("*.exe"))

        # Strict Filtering
        candidates = [exe for exe in exes if exe.name.lower() not in BLACKLIST]

        if not candidates:
            return None

        # Prepare for comparison
        folder_name_clean = folder.name.lower().replace(" ", "").replace("_", "").replace("-", "")

        def score_candidate(exe: Path) -> float:
            score = 0.0
            name = exe.stem.lower()
            name_clean = name.replace(" ", "").replace("_", "").replace("-", "")

            # --- CRITERIA 1: FUZZY NAME MATCH (0 to 100 points) ---
            # Uses difflib to find similarity ratio (0.0 to 1.0)
            similarity = difflib.SequenceMatcher(None, folder_name_clean, name_clean).ratio()
            score += similarity * 100

            # Bonus: Exact containment (e.g. 'Factorio' in 'Factorio.exe')
            if folder_name_clean in name_clean:
                score += 20

            # --- CRITERIA 2: SIZE HEURISTIC (Adjusted) ---
            # We don't penalize small files blindly, only MICRO files (<50KB)
            # A 650KB exe is plausible (wrapper), a 10KB exe is usually a stub.
            size_mb = exe.stat().st_size / (1024 * 1024)

            if size_mb > 50: # Heavy file = likely assets included = Game
                score += 30
            elif size_mb < 0.1: # < 100KB = Suspicious
                score -= 50

            # --- CRITERIA 3: KEYWORDS PENALTY ---
            # Penalize utility names unless they are the ONLY option
            if "config" in name or "settings" in name or "server" in name:
                score -= 40

            # Penalize "Shipping" builds slightly less (UE4 games often use 'Game-Win64-Shipping.exe')
            if "shipping" in name:
                score += 10

            return score

        # Sort by score descending
        candidates.sort(key=score_candidate, reverse=True)

        # Debug Log (Visible if you run flatpak run with -v)
        winner = candidates[0]
        logging.debug(f"[Scanner] Folder: {folder.name} -> Picked: {winner.name} (Score: {score_candidate(winner):.2f})")

        return winner


class OnlineFixSource(Source):
    source_id = "online-fix"
    name = "Online-Fix"
    iterable_class = OnlineFixSourceIterable
    available_on = {"linux", "win32", "darwin"}

    def __init__(self) -> None:
        super().__init__()
        self.locations = []

    def make_executable(self, *args, **kwargs) -> str:
        return kwargs.get("executable", "")
