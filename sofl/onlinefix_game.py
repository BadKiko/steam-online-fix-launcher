# onlinefix_game.py
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

import logging
import shutil
import os
import subprocess
import tempfile
import struct
from typing import Any, Optional
from pathlib import Path
from time import time

from gi.repository import Adw

from sofl import shared
from sofl.game_data import GameData
from sofl.utils.run_executable import run_executable
from sofl.utils.create_dialog import create_dialog

from gettext import gettext as _

class OnlineFixGameData(GameData):
    """Класс данных для игр Online-Fix с расширенной функциональностью"""
    
    def __init__(self, data: dict[str, Any]):
        super().__init__(data)
    
    def get_play_button_label(self) -> str:
        """Return the label text for the play button"""
        return _("Play with Online-Fix")
    
    def launch(self) -> None:
        """Launch the Online-Fix game with its specific launcher logic"""
        # First record last played time and save/update the game
        self.last_played = int(time())
        self.save()
        self.update()
        
        # Check if we should use Steam/Proton for launching
        launcher_type = shared.schema.get_int("online-fix-launcher-type")
        print(f"launcher_type: {launcher_type}")
        
        # Сначала пробуем запустить через Steam/Proton
        success = self.launch_with_steam_proton()
        
        # Если метод не сработал, используем альтернативный метод запуска
        if not success and launcher_type == 0:  # Если выбран Steam API, но основной метод не сработал
            success = self.launch_with_direct_proton()
        
        # Если оба метода не сработали, используем стандартный запуск
        if not success:
            run_executable(self.executable)
        
        if shared.schema.get_boolean("exit-after-launch"):
            shared.win.get_application().quit()
        
        # Create toast notification
        self.create_toast(_("{} launched with Online-Fix").format(self.name))
    
    def launch_with_direct_proton(self) -> bool:
        """
        Запускает игру напрямую с Proton через скрипт
        
        Returns:
            bool: True если запуск успешен, False в противном случае
        """
        try:
            # Get the path to the executable
            exec_path = Path(self.executable.split()[0])
            
            # Prepare environment variables
            env_vars = {}
            
            # Add WINEDLLOVERRIDES if auto-patch is disabled
            if not shared.schema.get_boolean("online-fix-auto-patch"):
                dll_overrides = shared.schema.get_string("online-fix-dll-overrides")
                if dll_overrides:
                    env_vars["WINEDLLOVERRIDES"] = dll_overrides
            
            # Add SteamAppID environment variable if enabled
            if shared.schema.get_boolean("online-fix-steam-appid-patch"):
                env_vars["SteamAppId"] = "480"  # Use generic AppID 480 (Spacewar)
                
            # Add Steam-Fix-64 patch if enabled
            if shared.schema.get_boolean("online-fix-steamfix64-patch"):
                # Set path to Steam installation - adjust path if needed
                steam_path = os.path.expanduser("~/.steam/steam")
                env_vars["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = steam_path
            
            # Найдем Steam Runtime и Proton
            steam_path = os.path.expanduser("~/.steam/steam")
            proton_path = None
            
            # Поиск последней версии Proton
            proton_dirs = list(Path(f"{steam_path}/steamapps/common").glob("Proton*"))
            if proton_dirs:
                # Сортируем по номерам версий
                proton_dirs.sort(reverse=True)
                proton_path = str(proton_dirs[0] / "proton")
            
            if not proton_path:
                self.log_and_toast(_("Proton not found. Install Proton in Steam first."))
                return False
            
            # Создадим временный скрипт для запуска
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                script_path = script_file.name
                
                script_content = "#!/bin/bash\n\n"
                
                # Добавляем переменные окружения
                for var, value in env_vars.items():
                    script_content += f'export {var}="{value}"\n'
                
                # Путь к Steam Runtime
                script_content += f'export STEAM_RUNTIME="{steam_path}/ubuntu12_32/steam-runtime"\n'
                
                # Команда запуска с Proton
                script_content += f'"{proton_path}" run "{exec_path}" "$@"\n'
                
                script_file.write(script_content)
            
            # Делаем скрипт исполняемым
            os.chmod(script_path, 0o755)
            
            # Запускаем скрипт
            subprocess.Popen(
                [script_path],
                cwd=exec_path.parent,
                start_new_session=True,
                shell=False
            )
            
            self.log_and_toast(_("Launching game directly with Proton"))
            return True
            
        except Exception as e:
            self.log_and_toast(_("Error launching with direct Proton: {}").format(str(e)))
            return False

    def launch_with_steam_proton(self) -> bool:
        """
        Launch the game through Steam with Proton
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the path to the executable
            exec_path = Path(self.executable.split()[0])
            
            # Generate a unique AppID for this game based on its path
            # This will help ensure we get a consistent Steam shortcut ID
            import hashlib
            game_hash = hashlib.md5(str(exec_path).encode()).hexdigest()
            shortcut_id = int(game_hash[:8], 16) % 1000000  # Create a shorter number for AppID
            app_id = shortcut_id + 989400000  # AppID для non-Steam игр
            
            # Prepare launch options with DLL overrides
            launch_options = ""
            
            # Add WINEDLLOVERRIDES if auto-patch is disabled
            if not shared.schema.get_boolean("online-fix-auto-patch"):
                dll_overrides = shared.schema.get_string("online-fix-dll-overrides")
                if dll_overrides:
                    launch_options += f"WINEDLLOVERRIDES=\"{dll_overrides}\" "
            
            # Add SteamAppID environment variable if enabled
            if shared.schema.get_boolean("online-fix-steam-appid-patch"):
                launch_options += "SteamAppId=480 "  # Use generic AppID 480 (Spacewar)
                
            # Add Steam-Fix-64 patch if enabled
            if shared.schema.get_boolean("online-fix-steamfix64-patch"):
                # Set path to Steam installation - adjust path if needed
                steam_path = "~/.steam/steam"
                launch_options += f"STEAM_COMPAT_CLIENT_INSTALL_PATH=\"{steam_path}\" "
            
            # Пути к конфигурационным файлам Steam
            steam_config_dir = Path(os.path.expanduser("~/.steam/steam/userdata"))
            if not steam_config_dir.exists():
                # Try alternative path for Flatpak
                steam_config_dir = Path(os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/userdata"))
            
            # Find the first user directory
            user_dirs = [d for d in steam_config_dir.glob("*") if d.is_dir() and d.name.isdigit()]
            if not user_dirs:
                self.log_and_toast(_("Could not find Steam user directory"))
                return False
                
            user_config_dir = user_dirs[0] / "config"
            
            # Ensure the directory exists
            user_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a temporary VDF file to add the game to Steam
            vdf_path = user_config_dir / "shortcuts.vdf"
            
            # Back up the original shortcuts.vdf if it exists
            backup_path = None
            if vdf_path.exists():
                backup_path = vdf_path.with_suffix('.vdf.bak')
                shutil.copy2(vdf_path, backup_path)
            else:
                # Если файла нет, создадим пустой бинарный файл с базовой структурой
                with open(vdf_path, 'wb') as f:
                    f.write(b'\0shortcuts\0\x08')
            
            # Create a binary VDF file for Steam shortcuts
            try:
                self._create_binary_vdf(vdf_path, shortcut_id, launch_options, exec_path)
            except Exception as e:
                self.log_and_toast(_("Error creating shortcuts.vdf: {}").format(str(e)))
                # Restore backup if creation failed
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, vdf_path)
                return False
                
            # Set Proton compatibility in config.vdf
            config_vdf_path = user_config_dir / "config.vdf"
            
            # Simple content for config.vdf to set Proton compatibility
            proton_id = "Proton 8"  # Use latest Proton by default
            config_content = f"""
            "InstallConfigStore"
            {{
                "Software"
                {{
                    "Valve"
                    {{
                        "Steam"
                        {{
                            "CompatToolMapping"
                            {{
                                "{app_id}"
                                {{
                                    "name"		"{proton_id}"
                                    "config"		""
                                    "priority"		"250"
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """
            
            # Backup config.vdf if it exists
            config_backup_path = None
            if config_vdf_path.exists():
                config_backup_path = config_vdf_path.with_suffix('.vdf.bak')
                shutil.copy2(config_vdf_path, config_backup_path)
                
            # Write the new config.vdf
            with open(config_vdf_path, 'w') as f:
                f.write(config_content)
                
            # Проверяем, что файл был создан с правильными правами доступа
            os.chmod(vdf_path, 0o644)
            os.chmod(config_vdf_path, 0o644)
            
            # Find Steam executable
            steam_exe = "steam"
                
            # Log the launch attempt
            logging.info(f"Added {self.name} to Steam with shortcut ID: {shortcut_id}, AppID: {app_id}")
            logging.info(f"Launch options: {launch_options}")
            
            # Полностью закрываем Steam если он запущен
            try:
                self.log_and_toast(_("Closing Steam to apply changes..."))
                subprocess.run(["killall", "-9", "steam", "steamwebhelper"], check=False)
                import time
                time.sleep(3)  # Даем Steam время полностью закрыться
            except Exception as e:
                logging.warning(f"Error stopping Steam: {str(e)}")
            
            # Запускаем Steam с непосредственным запуском игры
            cmd = [steam_exe, f"-applaunch", str(app_id)]
            
            # Use Flatpak spawn if running in Flatpak
            if os.getenv("FLATPAK_ID") == shared.APP_ID:
                cmd = ["flatpak-spawn", "--host"] + cmd
            
            # Launch Steam
            subprocess.Popen(
                cmd,
                start_new_session=True,
                shell=False
            )
            
            # Show toast notification
            self.log_and_toast(_("Game added to Steam and launch requested"))
            
            # Schedule restoration of the original files after some time
            if backup_path or config_backup_path:
                restore_script = "#!/bin/sh\n"
                restore_script += "sleep 300\n"  # Wait 5 minutes
                
                if backup_path:
                    restore_script += f"mv '{backup_path}' '{vdf_path}'\n"
                
                if config_backup_path:
                    restore_script += f"mv '{config_backup_path}' '{config_vdf_path}'\n"
                
                # Create a temporary script file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                    script_path = script_file.name
                    script_file.write(restore_script)
                
                # Make it executable
                os.chmod(script_path, 0o755)
                
                # Run the script in background
                subprocess.Popen(
                    [script_path],
                    start_new_session=True,
                    shell=False
                )
            
            return True
            
        except Exception as e:
            self.log_and_toast(_("Error launching with Steam: {}").format(str(e)))
            return False
    
    def _create_binary_vdf(self, vdf_path: Path, shortcut_id: int, launch_options: str, exec_path: Path) -> None:
        """
        Creates a binary VDF file for Steam shortcuts
        
        Args:
            vdf_path: Path to write the VDF file
            shortcut_id: Unique ID for the shortcut
            launch_options: Launch options string
            exec_path: Path to the game executable
        """
        with open(vdf_path, 'wb') as f:
            # Работаем с Valve's binary VDF (KeyValues) format
            # Начало файла
            f.write(b'\0shortcuts\0')
            
            # Идентификатор для начала записи
            f.write(struct.pack('<L', shortcut_id))
            
            # Запись App Name
            self._write_vdf_key_string(f, "AppName", self.name)
            
            # Запись пути к exe файлу
            self._write_vdf_key_string(f, "Exe", str(exec_path))
            
            # Стартовая директория
            self._write_vdf_key_string(f, "StartDir", str(exec_path.parent))
            
            # Иконка (пустая)
            self._write_vdf_key_string(f, "icon", "")
            
            # Путь к ярлыку (пустой)
            self._write_vdf_key_string(f, "ShortcutPath", "")
            
            # Параметры запуска
            self._write_vdf_key_string(f, "LaunchOptions", f"{launch_options} %command%")
            
            # IsHidden = 0 (не скрыто)
            self._write_vdf_key_int(f, "IsHidden", 0)
            
            # AllowDesktopConfig = 1 (разрешить конфигурацию)
            self._write_vdf_key_int(f, "AllowDesktopConfig", 1)
            
            # AllowOverlay = 1 (разрешить оверлей)
            self._write_vdf_key_int(f, "AllowOverlay", 1)
            
            # Открывать без VR
            self._write_vdf_key_int(f, "OpenVR", 0)
            
            # Последнее время запуска
            self._write_vdf_key_int(f, "LastPlayTime", self.last_played)
            
            # Разработка отключена
            self._write_vdf_key_int(f, "Devkit", 0)
            
            # ID для разработки (пустое)
            self._write_vdf_key_string(f, "DevkitGameID", "")
            
            # Уникальный ID ярлыка (для Steam)
            app_id = shortcut_id + 989400000
            self._write_vdf_key_int(f, "appid", app_id)
            
            # Теги
            f.write(b'\0tags\0')
            self._write_vdf_key_string(f, "0", "Online-Fix")
            f.write(b'\x08\x08')  # Конец тегов
            
            # Конец записи
            f.write(b'\x08')
            
            # Конец файла
            f.write(b'\x08')
    
    def _write_vdf_key_string(self, file, key: str, value: str) -> None:
        """
        Writes a string key-value pair to the binary VDF file
        
        Args:
            file: Open binary file object
            key: Key name
            value: String value
        """
        file.write(key.encode('utf-8') + b'\0' + value.encode('utf-8') + b'\0')
    
    def _write_vdf_key_int(self, file, key: str, value: int) -> None:
        """
        Writes an integer key-value pair to the binary VDF file
        
        Args:
            file: Open binary file object
            key: Key name
            value: Integer value
        """
        file.write(key.encode('utf-8') + b'\0')
        file.write(struct.pack('<I', value))
        file.write(b'\0\0\0\0')
    
    def uninstall_game(self) -> None:
        """Uninstall the game by removing its root directory after confirmation"""
        # Check if the game is from online-fix
        if "online-fix" not in self.source:
            self.log_and_toast(_("Cannot uninstall non-online-fix games"))
            return
        
        # Get the path to online-fix installations
        onlinefix_path = shared.schema.get_string("online-fix-install-path")
        # Expand tilde to full home directory path
        onlinefix_root = Path(os.path.expanduser(onlinefix_path))
        
        try:
            # Check if the game is inside the online-fix folder
            if not str(self.executable).startswith(str(onlinefix_root)):
                self.log_and_toast(_("Game is not installed in Online-Fix directory"))
                return
            
            # Get a more reliable game root folder
            game_root = self._detect_game_root_folder(onlinefix_root)
            
            # Create a confirmation dialog
            dialog = create_dialog(
                shared.win,
                _("Uninstall Game"),
                _("This will remove folder {}, and can't be undone.").format(game_root),
                "uninstall",
                _("Uninstall")
            )
 
            dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
            
            def on_response(dialog, response):
                if response == "uninstall":
                    self.log_and_toast(_("{} started uninstalling").format(self.name))
                    try:
                        # Remove the game's root folder
                        shutil.rmtree(game_root)
                        self.log_and_toast(_("{} uninstalled").format(self.name))
                    
                    except Exception as e:
                        self.log_and_toast(_("Error uninstalling {}: {}").format(self.name, str(e)))

                    finally:
                        # Mark the game as removed
                        self.removed = True
                        self.save()
                        self.update()
            
            dialog.connect("response", on_response)
            
        except Exception as e:
            self.log_and_toast(_("Error: {}").format(str(e)))

    def _detect_game_root_folder(self, onlinefix_root: Path) -> Path:
        """
        Detects the game's root folder more reliably
        
        Args:
            onlinefix_root: Path to the online-fix installation directory
            
        Returns:
            Path: Path to the detected game folder
        """
        try:
            # Get the path to the executable
            exec_path = Path(self.executable.split()[0])
            
            # Make sure it's relative to the online-fix root
            if not str(exec_path).startswith(str(onlinefix_root)):
                # Fallback to parent directory of executable
                return exec_path.parent
                
            # Get relative path from online-fix root
            rel_path = exec_path.relative_to(onlinefix_root)
            
            # First try to use first directory component
            if len(rel_path.parts) > 0:
                candidate = rel_path.parts[0]
                game_dir = onlinefix_root / candidate
                
                # Verify that this is actually a directory
                if game_dir.is_dir():
                    return game_dir
            
            # If first component isn't suitable, fall back to executable's parent
            return exec_path.parent
            
        except Exception as e:
            logging.error(f"Error detecting game root folder: {str(e)}")
            # Always fall back to parent directory of executable if something goes wrong
            return Path(self.executable.split()[0]).parent
    
    def log_and_toast(self, message: str) -> None:
        """Log a message and show a toast notification"""
        logging.info(f"[SOFL] {message}")
        self.create_toast(message) 