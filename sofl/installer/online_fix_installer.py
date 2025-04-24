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

# Константы
ONLINE_FIX_PASSWORD = "online-fix.me"
logger = logging.getLogger(__name__)

# Список игнорируемых исполняемых файлов - не рассматриваются как основные игровые файлы
IGNORED_EXECUTABLES = [
    "UnityHandler64.exe",  # Unity обработчик
    "UnityHandler.exe",    # Unity обработчик
    "UnityCrashHandler.exe", # Обработчик крэшей Unity
    "UnityCrashHandler64.exe", # Обработчик крэшей Unity
    "launcher.exe",        # Общее название для лаунчеров
    "LauncherHelper.exe",  # Вспомогательный лаунчер
    "redist.exe",          # Установщик зависимостей
    "vcredist.exe",        # Установщик Visual C++ runtime
    "directx_setup.exe",   # Установщик DirectX
    "dxsetup.exe",         # Установщик DirectX
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
    """Класс для установки игр Online-Fix из RAR-архивов"""
    
    def __init__(self):
        """Инициализация установщика"""
        # Проверяем наличие пути для установки
        try:
            # Пробуем получить значение, если ключ существует
            shared.schema.get_string("online-fix-install-path")
        except:
            # Если ключа нет, устанавливаем значение по умолчанию
            default_path = str(Path(shared.home) / "Games" / "Online-Fix")
            shared.schema.set_string("online-fix-install-path", default_path)
    
    def get_install_path(self) -> str:
        """Получает путь для установки из настроек
        
        Returns:
            str: Путь установки
        """
        path = shared.schema.get_string("online-fix-install-path")
        
        # Заменяем символ ~ на домашнюю директорию пользователя
        if path.startswith("~"):
            path = str(Path(shared.home) / path[2:])
            
        return path
    
    def install_game(self, 
                     archive_path: str, 
                     game_name: str, 
                     progress_callback: Optional[Callable[[float, str], None]] = None) -> Tuple[bool, str, Optional[str]]:
        """Распаковывает игру Online-Fix из архива в указанную директорию
        
        Args:
            archive_path: Путь к RAR-архиву
            game_name: Название игры (для информационных целей)
            progress_callback: Опционально функция обратного вызова для отображения прогресса
                               принимает прогресс (0-100) и сообщение
        
        Returns:
            Tuple[bool, str, Optional[str]]: (успешность, путь установки, исполняемый файл или сообщение об ошибке)
        """
        try:
            # Получаем базовый путь для установки из настроек
            base_install_path = self.get_install_path()
            
            # Не создаем дополнительную папку, так как архивы онлайн-фикса
            # обычно уже содержат папку игры
            dest_dir = base_install_path
            
            # Создаем директорию назначения, если она еще не существует
            os.makedirs(dest_dir, exist_ok=True)
            
            # Сначала пробуем использовать unrar напрямую (быстрее и с прогрессом)
            if self._extract_with_unrar(archive_path, dest_dir, progress_callback):
                # Пытаемся обнаружить реальную папку игры внутри распакованных файлов
                game_folder = self._detect_game_folder(dest_dir, game_name)
                
                # Ищем исполняемый файл игры
                if progress_callback:
                    progress_callback(0.95, "Поиск исполняемого файла игры...")
                
                executable_path = self._find_game_executable(game_folder)
                
                # Возвращаем относительный путь к исполняемому файлу, если он найден
                relative_executable = None
                if executable_path:
                    relative_executable = os.path.relpath(executable_path, game_folder)
                
                return True, game_folder, relative_executable
            
            # Если unrar не сработал, используем библиотеку rarfile
            if progress_callback:
                progress_callback(0, "Извлечение архива (запасной метод)...")
                
            self._extract_with_rarfile(archive_path, dest_dir, progress_callback)
            
            # Обнаруживаем реальную папку игры
            game_folder = self._detect_game_folder(dest_dir, game_name)
            
            # Ищем исполняемый файл игры
            if progress_callback:
                progress_callback(0.95, "Поиск исполняемого файла игры...")
            
            executable_path = self._find_game_executable(game_folder)
            
            # Возвращаем относительный путь к исполняемому файлу, если он найден
            relative_executable = None
            if executable_path:
                relative_executable = os.path.relpath(executable_path, game_folder)
            
            return True, game_folder, relative_executable
            
        except Exception as e:
            error_msg = f"Ошибка при установке игры: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _sanitize_name(self, name: str) -> str:
        """Очищает имя игры для безопасного использования в качестве имени папки
        
        Args:
            name: Имя игры
            
        Returns:
            str: Безопасное имя папки
        """
        # Заменяем специальные символы и пробелы на подчеркивания
        sanitized = re.sub(r'[^\w\-\.]', '_', name)
        return sanitized
    
    def _extract_with_unrar(self, 
                           archive_path: str, 
                           dest_dir: str, 
                           progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Распаковывает архив с помощью утилиты unrar, отслеживая прогресс
        
        Args:
            archive_path: Путь к архиву
            dest_dir: Путь назначения для распаковки
            progress_callback: Функция для уведомления о прогрессе
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            # Проверяем наличие unrar
            unrar_path = rarfile.UNRAR_TOOL
            if not os.path.exists(unrar_path):
                # Проверяем альтернативные пути
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
                    logger.warning("unrar не найден, невозможно отслеживать прогресс")
                    return False
            
            # Запускаем процесс unrar с выводом
            process = subprocess.Popen(
                [unrar_path, "x", "-idp", "-y", f"-p{ONLINE_FIX_PASSWORD}", archive_path, dest_dir], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            if not process.stdout:
                return False
                
            # Паттерн для определения прогресса (процент и имя файла)
            progress_pattern = re.compile(r"([0-9]+)%")
            last_progress = 0
            
            for line in process.stdout:
                # Ищем процент в текущей строке
                match = progress_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    if percent != last_progress and progress_callback:
                        file_info = line.strip()
                        # Оповещаем о прогрессе
                        progress_callback(percent / 100.0, f"Распаковка: {percent}%")
                        last_progress = percent
            
            # Ждем окончания процесса
            return_code = process.wait()
            if return_code != 0:
                logger.error(f"unrar завершился с ошибкой: {return_code}")
                return False
                
            # Если все дошло до сюда, распаковка успешна
            if progress_callback:
                progress_callback(1.0, "Распаковка завершена")
            return True
                
        except Exception as e:
            logger.error(f"Ошибка при распаковке через unrar: {str(e)}")
            return False
    
    def _extract_with_rarfile(self, 
                             archive_path: str, 
                             dest_dir: str, 
                             progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """Распаковывает архив с помощью библиотеки rarfile
        
        Args:
            archive_path: Путь к архиву
            dest_dir: Путь назначения для распаковки
            progress_callback: Функция для уведомления о прогрессе
            
        Returns:
            bool: True если успешно, иначе False
        """
        try:
            with rarfile.RarFile(archive_path) as rf:
                rf.setpassword(ONLINE_FIX_PASSWORD)
                
                # Получаем список файлов
                file_list = rf.infolist()
                total_files = len(file_list)
                
                # Распаковываем каждый файл
                for i, file_info in enumerate(file_list):
                    rf.extract(file_info, path=dest_dir)
                    
                    # Обновляем прогресс
                    if progress_callback:
                        progress = (i + 1) / total_files
                        progress_callback(progress, f"Распаковка: {int(progress * 100)}%")
                        
                        # Обрабатываем события GTK для обновления UI
                        # В GTK4 это происходит автоматически через MainContext
                        # Поэтому просто даем время событийному циклу
                        GLib.main_context_default().iteration(False)
            
            if progress_callback:
                progress_callback(1.0, "Распаковка завершена")
            return True
                
        except Exception as e:
            logger.error(f"Ошибка при распаковке через rarfile: {str(e)}")
            raise 
    
    def _detect_game_folder(self, base_dir: str, game_name: str) -> str:
        """Обнаруживает папку игры внутри базовой директории установки
        
        Args:
            base_dir: Базовая директория, в которую распакован архив
            game_name: Название игры для поиска похожих папок
            
        Returns:
            str: Путь к обнаруженной папке игры
        """
        try:
            # Сначала проверяем содержимое базовой директории
            items = os.listdir(base_dir)
            
            # Ищем папки, которые могут содержать игру
            game_dirs = [d for d in items if os.path.isdir(os.path.join(base_dir, d))]
            
            if not game_dirs:
                # Если нет подпапок, возвращаем базовую директорию
                return base_dir
                
            # Если есть только одна подпапка, скорее всего это и есть наша игра
            if len(game_dirs) == 1:
                return os.path.join(base_dir, game_dirs[0])
                
            # Если есть несколько папок, попробуем найти ту, которая похожа на название игры
            clean_game_name = self._sanitize_name(game_name).lower()
            
            for dir_name in game_dirs:
                if clean_game_name in dir_name.lower() or dir_name.lower() in clean_game_name:
                    return os.path.join(base_dir, dir_name)
            
            # Если не нашли похожую, ищем папку, которая содержит исполняемые файлы
            for dir_name in game_dirs:
                dir_path = os.path.join(base_dir, dir_name)
                exe_files = [f for f in os.listdir(dir_path) if f.lower().endswith('.exe')]
                if exe_files:
                    return dir_path
            
            # Если не нашли подходящую директорию, возвращаем базовую
            return base_dir
            
        except Exception as e:
            logger.warning(f"Ошибка при определении папки игры: {str(e)}")
            return base_dir
    
    def _find_game_executable(self, game_dir: str) -> Optional[str]:
        """Находит основной исполняемый файл игры, игнорируя служебные файлы
        
        Args:
            game_dir: Директория игры для поиска
            
        Returns:
            Optional[str]: Полный путь к исполняемому файлу или None, если не найден
        """
        try:
            # Сначала создадим список всех исполняемых файлов
            all_executables = []
            
            # Рекурсивно ищем все .exe файлы
            for root, _, files in os.walk(game_dir):
                for file in files:
                    if file.lower().endswith('.exe'):
                        all_executables.append(os.path.join(root, file))
            
            if not all_executables:
                logger.warning(f"Исполняемые файлы не найдены в {game_dir}")
                return None
            
            # Фильтруем исполняемые файлы, исключая игнорируемые
            valid_executables = []
            for exe_path in all_executables:
                exe_name = os.path.basename(exe_path)
                if exe_name not in IGNORED_EXECUTABLES:
                    # Проверяем размер файла (маленькие файлы обычно не основные)
                    file_size = os.path.getsize(exe_path)
                    if file_size > 1024 * 100:  # Больше 100 КБ
                        valid_executables.append((exe_path, file_size))
            
            if not valid_executables:
                # Если все файлы в игнорируемом списке, возьмем любой исполняемый файл
                logger.warning("Все исполняемые файлы находятся в игнорируемом списке")
                return all_executables[0]
            
            # Сортируем по размеру (больший файл вероятнее основной)
            valid_executables.sort(key=lambda x: x[1], reverse=True)
            
            # Приоритет файлам в корневой директории
            root_executables = [exe for exe, _ in valid_executables if os.path.dirname(exe) == game_dir]
            if root_executables:
                return root_executables[0]
            
            # Возвращаем самый большой исполняемый файл
            return valid_executables[0][0]
            
        except Exception as e:
            logger.error(f"Ошибка при поиске исполняемого файла: {str(e)}")
            return None 