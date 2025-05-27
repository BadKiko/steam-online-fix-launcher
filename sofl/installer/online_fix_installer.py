# online_fix_installer.py
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
import re
import logging
import subprocess
import rarfile
import shutil
from pathlib import Path
from typing import Callable, Optional, Tuple, Dict, Any, List

from gi.repository import GLib

from sofl import shared

# Constants
ONLINE_FIX_PASSWORD = "online-fix.me"
logger = logging.getLogger(__name__)

# List of ignored executable files - not considered as main game files
IGNORED_EXECUTABLES = [
    "UnityHandler64.exe",  # Unity handler
    "UnityHandler.exe",    # Unity handler
    "UnityCrashHandler.exe", # Unity crash handler
    "UnityCrashHandler64.exe", # Unity crash handler 64-bit
    "launcher.exe",        # Generic launcher name
    "LauncherHelper.exe",  # Helper launcher
    "redist.exe",          # Dependency installer
    "vcredist.exe",        # Visual C++ runtime installer
    "directx_setup.exe",   # DirectX installer
    "dxsetup.exe",         # DirectX installer
    "dotNetFx40_Full_setup.exe", # .NET Framework installer
    "unins000.exe",        # Uninstaller
    "steam_api.exe",       # Steam API
    "steam_api64.exe",     # Steam API 64-bit
    "steamclient.exe",     # Steam client
    "steamclient64.exe",   # Steam client 64-bit
    "SteamSetup.exe",      # Steam setup
    "SteamInstall.exe",    # Steam installer
    "setup.exe",           # Generic setup
    "install.exe",         # Generic installer
    "CrashReporter.exe",   # Generic crash reporter
    "binkw32.exe",         # Bink video player
    "binkw64.exe",         # Bink video player 64-bit
    "REDprelauncher.exe",  # CD Projekt RED launcher
    "ScummVM.exe",         # ScummVM emulator
    "WinRAR.exe",          # WinRAR archiver
    "7zG.exe",             # 7zip GUI
    "Editor.exe",          # Generic editor
    "Configurator.exe",    # Generic configurator
    "Updater.exe",         # Generic updater
    "DXSETUP.exe",         # DirectX setup
    "InstallerTool.exe",   # Generic installer
    "PhysXUpdateLauncher.exe", # PhysX updater
    "PhysXExtensions.exe", # PhysX extensions
    "vc_redist.exe",       # Visual C++ Redistributable
]

class OnlineFixInstaller:
    """Class for installing Online-Fix games from RAR archives"""
    
    def __init__(self):
        """Installer initialization"""
        # Check if installation path exists
        try:
            # Try to get the value if the key exists
            shared.schema.get_string("online-fix-install-path")
        except GLib.Error as e:
            # If the key doesn't exist, set the default value
            default_path = str(Path(shared.home) / "Games" / "Online-Fix")
            shared.schema.set_string("online-fix-install-path", default_path)
            logger.warning(f"Online-Fix install path not found, using default: {default_path}")
    
    def get_install_path(self) -> str:
        """Gets the installation path from settings
        
        Returns:
            str: Installation path
        """
        path = shared.schema.get_string("online-fix-install-path")
        
        # Replace ~ symbol with user's home directory
        if path.startswith("~"):
            path = str(Path(shared.home) / path[2:])
            
        return path
    
    def install_game(self, 
                     archive_path: str, 
                     game_name: str, 
                     progress_callback: Optional[Callable[[float, str], None]] = None) -> Tuple[bool, str, Optional[str]]:
        """Extracts an Online-Fix game from an archive to the specified directory
        
        Args:
            archive_path: Path to the RAR archive
            game_name: Game name (for informational purposes)
            progress_callback: Optional callback function to display progress
                               takes progress (0-100) and message
        
        Returns:
            Tuple[bool, str, Optional[str]]: (success, installation path, executable file or error message)
        """
        try:
            # Get base installation path from settings
            base_install_path = self.get_install_path()
            
            # Don't create additional folder as online-fix archives
            # usually already contain game folder
            dest_dir = base_install_path
            
            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)
            
            # First try to use unrar directly (faster and with progress)
            if self._extract_with_unrar(archive_path, dest_dir, progress_callback):
                # Try to detect actual game folder inside extracted files
                game_folder = self._detect_game_folder(dest_dir, game_name)
                
                # Search for game executable
                if progress_callback:
                    progress_callback(0.95, "Searching for game executable...")
                
                executable_path = self._find_game_executable(game_folder)
                
                # Return relative path to executable if found
                relative_executable = None
                if executable_path:
                    relative_executable = os.path.relpath(executable_path, game_folder)
                
                return True, game_folder, relative_executable
            
            # If unrar didn't work, use rarfile library
            if progress_callback:
                progress_callback(0, "Extracting archive (backup method)...")
                
            self._extract_with_rarfile(archive_path, dest_dir, progress_callback)
            
            # Detect actual game folder
            game_folder = self._detect_game_folder(dest_dir, game_name)
            
            # Search for game executable
            if progress_callback:
                progress_callback(0.95, "Searching for game executable...")
            
            executable_path = self._find_game_executable(game_folder)
            
            # Return relative path to executable if found
            relative_executable = None
            if executable_path:
                relative_executable = os.path.relpath(executable_path, game_folder)
            
            return True, game_folder, relative_executable
            
        except Exception as e:
            error_msg = f"Error during game installation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _sanitize_name(self, name: str) -> str:
        """Cleans up game name for safe use as folder name
        
        Args:
            name: Game name
            
        Returns:
            str: Safe folder name
        """
        # Replace special characters and spaces with underscores
        sanitized = re.sub(r'[^\w\-\.]', '_', name)
        return sanitized
    
    def _extract_with_unrar(self, 
                           archive_path: str, 
                           dest_dir: str, 
                           progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Extracts an archive using the unrar utility, tracking progress
        
        Args:
            archive_path: Path to the archive
            dest_dir: Destination path for extraction
            progress_callback: Function for progress notification
            
        Returns:
            bool: True if successful, otherwise False
        """
        try:
            # Check for unrar
            unrar_path = rarfile.UNRAR_TOOL
            if not os.path.exists(unrar_path):
                # Check for alternative paths
                alt_paths = [
                    "/app/bin/unrar",  # Flatpak
                    "/usr/bin/unrar",
                    "/bin/unrar",
                ]
                
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        unrar_path = alt_path
                        break
                        
                if not os.path.exists(unrar_path):
                    logger.warning("unrar not found, unable to track progress")
                    return False
            
            # Start unrar process with output
            process = subprocess.Popen(
                [unrar_path, "x", "-idp", "-y", f"-p{ONLINE_FIX_PASSWORD}", archive_path, dest_dir], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            if not process.stdout:
                return False
                
            # Pattern for determining progress (percentage and file name)
            progress_pattern = re.compile(r"([0-9]{1,3})%")
            last_progress = 0
            
            for line in process.stdout:
                # Search for percentage in current line
                match = progress_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    if percent != last_progress and progress_callback:
                        file_info = line.strip()
                        # Notify about progress
                        progress_callback(percent / 100.0, f"Extracting: {percent}%")
                        last_progress = percent
            
            # Wait for process to finish
            return_code = process.wait()
            if return_code != 0:
                logger.error(f"unrar finished with error: {return_code}")
                return False
                
            # If everything reached here, extraction was successful
            if progress_callback:
                progress_callback(1.0, "Extraction complete")
            return True
                
        except Exception as e:
            logger.error(f"Error during extraction with unrar: {str(e)}")
            return False
    
    def _extract_with_rarfile(self, 
                             archive_path: str, 
                             dest_dir: str, 
                             progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Extracts an archive using the rarfile library
        
        Args:
            archive_path: Path to the archive
            dest_dir: Destination path for extraction
            progress_callback: Function for progress notification
            
        Returns:
            bool: True if successful, otherwise False
        """
        try:
            with rarfile.RarFile(archive_path) as rf:
                rf.setpassword(ONLINE_FIX_PASSWORD)
                
                # Get file list
                file_list = rf.infolist()
                total_files = len(file_list)
                
                # Extract each file
                for i, file_info in enumerate(file_list):
                    rf.extract(file_info, path=dest_dir)
                    
                    # Update progress
                    if progress_callback:
                        progress = (i + 1) / total_files
                        progress_callback(progress, f"Extracting: {int(progress * 100)}%")
                        
                        # Process GTK events to update UI
                        # In GTK4 this happens automatically through MainContext
                        # So we just give time to the event loop
                        GLib.main_context_default().iteration(False)
            
            if progress_callback:
                progress_callback(1.0, "Extraction complete")
            return True
                
        except Exception as e:
            logger.error(f"Error during extraction with rarfile: {str(e)}")
            raise 
    
    def _detect_game_folder(self, base_dir: str, game_name: str) -> str:
        """Detects the game folder inside the base installation directory
        
        Args:
            base_dir: Base directory where the archive was extracted
            game_name: Game name for matching purposes
            
        Returns:
            str: Path to the detected game folder
        """
        try:
            # First check the contents of base directory
            items = os.listdir(base_dir)
            
            # Search for folders that might contain the game
            game_dirs = [d for d in items if os.path.isdir(os.path.join(base_dir, d))]
            
            if not game_dirs:
                # If no subfolders, return base directory
                return base_dir
                
            # If there's only one subfolder, it's probably our game
            if len(game_dirs) == 1:
                return os.path.join(base_dir, game_dirs[0])
                
            # If there are multiple folders, try to find the one that matches the game name
            clean_game_name = self._sanitize_name(game_name).lower()
            
            for dir_name in game_dirs:
                if clean_game_name in dir_name.lower() or dir_name.lower() in clean_game_name:
                    return os.path.join(base_dir, dir_name)
            
            # If we haven't found a similar one, look for a folder that contains executable files
            for dir_name in game_dirs:
                dir_path = os.path.join(base_dir, dir_name)
                exe_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.exe')]
                if exe_files:
                    return dir_path
            
            # If we haven't found a suitable directory, return the base one
            return base_dir
            
        except Exception as e:
            logger.warning(f"Error when detecting game folder: {str(e)}")
            return base_dir
    
    def _find_game_executable(self, game_dir: str) -> Optional[str]:
        """Finds the main game executable, ignoring service files
        
        Args:
            game_dir: Game directory to search
            
        Returns:
            Optional[str]: Full path to the executable file or None if not found
        """
        try:
            # First create a list of all executable files
            all_executables = []
            
            # Recursively search for all .exe files
            for root, _, files in os.walk(game_dir):
                for file in files:
                    if file.lower().endswith('.exe'):
                        all_executables.append(os.path.join(root, file))
            
            if not all_executables:
                logger.warning(f"Executable files not found in {game_dir}")
                return None
            
            # Filter executable files, excluding ignored
            valid_executables = []
            for exe_path in all_executables:
                exe_name = os.path.basename(exe_path)
                if exe_name not in IGNORED_EXECUTABLES:
                    # Check file size (small files usually not main)
                    file_size = os.path.getsize(exe_path)
                    if file_size > 1024 * 100:  # More than 100 KB
                        valid_executables.append((exe_path, file_size))
            
            if not valid_executables:
                # If all files are in the ignored list, take any executable file
                logger.warning("All executable files are in the ignored list")
                return all_executables[0]
            
            # Sort by size (larger file more likely main)
            valid_executables.sort(key=lambda x: x[1], reverse=True)
            
            # Priority to files in the root directory
            root_executables = [exe for exe, _ in valid_executables if os.path.dirname(exe) == game_dir]
            if root_executables:
                return root_executables[0]
            
            # Return the largest executable file
            return valid_executables[0][0]
            
        except Exception as e:
            logger.error(f"Error when searching for executable file: {str(e)}")
            return None 