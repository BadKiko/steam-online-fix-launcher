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

import os
import re
import rarfile
import subprocess
import tempfile
import logging
from pathlib import Path
from sys import platform
from typing import Any, Optional

from gi.repository import Adw, Gtk, GLib, Gio

from sofl import shared
from sofl.game import Game

# Constants
ONLINE_FIX_PASSWORD = "online-fix.me"
GAME_TITLE_REGEX = r"(^.*?)\.v"
TOAST_DEBOUNCE_DELAY = 1000  # Миллисекунды
FLATPAK_PATH_PATTERN = r"/run/user/\d+/doc/"

# Настройка логирования
logger = logging.getLogger(__name__)

@Gtk.Template(resource_path=shared.PREFIX + "/gtk/install-dialog.ui")
class InstallDialog(Adw.Dialog):
    __gtype_name__ = "InstallDialog"

    # Template children
    game_path = Gtk.Template.Child()
    game_title = Gtk.Template.Child()
    status_page = Gtk.Template.Child()
    apply_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    
    is_open: bool = False
    _toast_debounce_id: Optional[int] = None
    _last_toast_message: Optional[str] = None

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)
        
        # Create file dialog
        self.file_chooser = Gtk.FileDialog()
        
        # Connect path change handler
        self.game_path.connect("notify::text", self.on_path_changed)
        
        # Hide status page, we'll use toast instead
        self.status_page.set_visible(False)
        
        # If game already exists, fill in the fields
        if game:
            self.game_path.set_text(game.path if game.path else "")
            self.game_title.set_text(game.name if game.name else "")

    @Gtk.Template.Callback()
    def on_file_chooser_clicked(self, button):
        # Create filters
        filter_rar = Gtk.FileFilter()
        filter_rar.set_name("RAR files")
        filter_rar.add_pattern("*.rar")
        
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("EXE files")
        filter_exe.add_pattern("*.exe")
        
        # Create filter list
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_rar)
        filters.append(filter_exe)
        
        # Configure file chooser to open files
        self.file_chooser.set_filters(filters)
        self.file_chooser.set_title("Select game file")
        
        # Use portal to open file
        self.file_chooser.open(None, None, self.on_file_chooser_response)

    def on_file_chooser_response(self, dialog, result):
        try:
            file = self.file_chooser.open_finish(result)
            if file:
                original_path = file.get_path()
                path = original_path
                
                # Проверяем, нужно ли скопировать файл из Flatpak
                if self.is_flatpak_path(path):
                    self.log_message(f"Обнаружен путь Flatpak: {path}")
                    # Копируем файл и получаем новый путь
                    new_path = self.copy_flatpak_file(path)
                    # Используем новый путь для дальнейшей обработки
                    if new_path != path:
                        self.log_message(f"Используем скопированный файл: {new_path}")
                        path = new_path
                        file = Gio.File.new_for_path(path)
                
                # Format path for display
                display_path = self.format_path_for_display(path)
                self.game_path.set_text(path)
                
                try:
                    # Get file info through GIO
                    file_info = file.query_info("standard::*", Gio.FileQueryInfoFlags.NONE, None)
                    
                    if file_info and file_info.get_file_type() == Gio.FileType.REGULAR:
                        # Explicitly trigger file check after setting the path
                        self.log_message(f"Проверяем файл: {path}")
                        self.check_game_file(path, file)
                    else:
                        self.show_toast("Selected item is not a valid file")
                        self.apply_button.set_sensitive(False)
                except GLib.Error as err:
                    self.log_message(f"Ошибка доступа к скопированному файлу: {err.message}", logging.ERROR)
                    # Повторная попытка с оригинальным файлом, если скопированный недоступен
                    if path != original_path:
                        self.log_message("Пробуем использовать оригинальный файл", logging.WARNING)
                        path = original_path
                        file = Gio.File.new_for_path(path)
                        self.game_path.set_text(path)
                        self.check_game_file(path, file)
                    else:
                        self.show_toast(f"Error accessing file: {err.message}")
                        self.apply_button.set_sensitive(False)
                    
        except GLib.Error as error:
            self.log_message(f"Ошибка доступа к файлу: {error.message}", logging.ERROR)
            self.show_toast(f"Error accessing file: {error.message}")
            return

    def format_path_for_display(self, path: str) -> str:
        """Format path for display, handling Flatpak paths"""
        if platform == "linux":
            # Remove the path prefix if picked via Flatpak portal
            path = re.sub(r"/run/user/\d+/doc/[^/]+/", "", path)
            # Replace the home directory with "~"
            if hasattr(shared, 'home') and shared.home:
                path = path.replace(str(shared.home), "~")
        return path

    def is_flatpak_path(self, path: str) -> bool:
        """Проверяет, является ли путь путем Flatpak"""
        return bool(re.search(FLATPAK_PATH_PATTERN, path))

    def copy_flatpak_file(self, path: str) -> str:
        """Копирует файл из Flatpak в доступную директорию
        
        Args:
            path: Путь к файлу в Flatpak
            
        Returns:
            str: Путь к скопированному файлу или исходный путь в случае ошибки
        """
        try:
            # Создаем временную директорию, если её еще нет
            temp_dir = os.path.join(GLib.get_user_cache_dir(), "sofl-temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Получаем имя файла из пути
            filename = os.path.basename(path)
            new_path = os.path.join(temp_dir, filename)
            
            self.log_message(f"Копирую файл из Flatpak в: {new_path}")
            
            # Метод 1: Использование GIO для копирования файла (предпочтительный метод)
            try:
                self.log_message("Метод 1: Пробую копировать через GIO...")
                source_file = Gio.File.new_for_path(path)
                dest_file = Gio.File.new_for_path(new_path)
                
                # Проверяем существование исходного файла
                if not source_file.query_exists():
                    self.log_message(f"Исходный файл не существует через GIO: {path}", logging.WARNING)
                else:
                    # Копируем файл с флагами перезаписи
                    source_file.copy(
                        dest_file,
                        Gio.FileCopyFlags.OVERWRITE,
                        None, None  # Без отслеживания прогресса и отмены
                    )
                    self.log_message("GIO: Файл успешно скопирован")
                    return new_path
            except GLib.Error as e:
                self.log_message(f"GIO: Ошибка копирования: {e.message}", logging.ERROR)
            
            # Метод 2: Использование flatpak-spawn для доступа к хосту
            try:
                self.log_message("Метод 2: Пробую копировать через flatpak-spawn...")
                # Для доступа к файлам хоста через Flatpak
                result = subprocess.run(
                    ["flatpak-spawn", "--host", "cp", path, new_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    self.log_message("flatpak-spawn: Файл успешно скопирован")
                    return new_path
                else:
                    self.log_message(f"flatpak-spawn: Ошибка копирования: {result.stderr}", logging.ERROR)
            except Exception as e:
                self.log_message(f"flatpak-spawn: Ошибка: {str(e)}", logging.ERROR)
            
            # Метод 3: Используем xdg-document-portal
            try:
                self.log_message("Метод 3: Пробую получить реальный путь к файлу через портал документов...")
                # Извлекаем ID документа из пути Flatpak
                match = re.search(r'/run/user/\d+/doc/([^/]+)/', path)
                if match:
                    doc_id = match.group(1)
                    self.log_message(f"ID документа: {doc_id}")
                    
                    # Попытка получить путь через FUSE или другие методы
                    # Здесь мы предполагаем, что документ может быть доступен через системный путь
                    # Проверяем несколько возможных мест
                    potential_paths = [
                        # Общий путь к документам на хосте
                        f"/run/user/{os.getuid()}/doc/{doc_id}",
                        # Попробуем получить доступ через /tmp
                        f"/tmp/doc/{doc_id}",
                        # Используем относительный путь без префикса
                        path.replace(f"/run/user/{os.getuid()}/doc/{doc_id}/", "")
                    ]
                    
                    for alt_path in potential_paths:
                        self.log_message(f"Проверяю путь: {alt_path}")
                        if os.path.exists(alt_path):
                            self.log_message(f"Найден файл по пути: {alt_path}")
                            # Копируем файл стандартным способом
                            with open(alt_path, "rb") as src, open(new_path, "wb") as dst:
                                dst.write(src.read())
                            self.log_message("Файл успешно скопирован через Python")
                            return new_path
            except Exception as e:
                self.log_message(f"Метод 3: Ошибка: {str(e)}", logging.ERROR)
            
            # Метод 4: Прямое использование команды cp
            try:
                self.log_message("Метод 4: Пробую прямое копирование через cp...")
                result = subprocess.run(
                    ["cp", path, new_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    self.log_message("cp: Файл успешно скопирован")
                    return new_path
                else:
                    self.log_message(f"cp: Ошибка копирования: {result.stderr}", logging.ERROR)
            except Exception as e:
                self.log_message(f"cp: Ошибка: {str(e)}", logging.ERROR)
            
            # Все методы не удались, возвращаем исходный путь
            self.log_message("Все методы копирования не удались. Продолжаем с исходным файлом.", logging.WARNING)
            return path
        except Exception as e:
            self.log_message(f"Общая ошибка при копировании файла: {str(e)}", logging.ERROR)
            return path

    def on_path_changed(self, entry, pspec):
        path = self.game_path.get_text()
        if path:
            # Проверяем, нужно ли скопировать файл из Flatpak
            if self.is_flatpak_path(path):
                # Копируем файл и получаем новый путь
                new_path = self.copy_flatpak_file(path)
                # Обновляем текстовое поле, если путь изменился
                if new_path != path:
                    self.game_path.set_text(new_path)
                    path = new_path
            
            file = Gio.File.new_for_path(path)
            self.check_game_file(path, file)
        else:
            self.show_toast("Specify a game file path to check")
            self.apply_button.set_sensitive(False)

    def check_game_file(self, path, file=None):
        """Check if the file is a valid game file
        
        Args:
            path: The path to the file
            file: Optional Gio.File object for the file
        """
        # Перед проверкой убедимся, что используем правильный путь
        self.log_message(f"Проверка файла игры: {path}")
        
        if file is None:
            file = Gio.File.new_for_path(path)
        
        # Check if file exists through GIO
        try:
            if not file.query_exists():
                self.log_message(f"Файл не существует: {path}", logging.ERROR)
                self.show_toast("File does not exist")
                self.apply_button.set_sensitive(False)
                return
                
            # Open the file using GIO to handle Flatpak portal access
            file_stream = None
            try:
                file_stream = file.read()
                self.log_message("Файл успешно открыт для чтения")
            except GLib.Error as err:
                self.log_message(f"Не удалось открыть файл: {err.message}", logging.ERROR)
                self.show_toast(f"Cannot access file: {err.message}")
                self.apply_button.set_sensitive(False)
                return
            finally:
                if file_stream:
                    file_stream.close()
                
            # File exists and is accessible, continue with checking
            if path.lower().endswith(".rar"):
                try:
                    # Проверяем архив с паролем напрямую
                    self.log_message("Проверка RAR архива с паролем")
                    if self.validate_with_password(path):
                        self.show_toast("Confirmed: This is an Online-Fix game")
                        self.extract_game_title(os.path.basename(path))
                        self.apply_button.set_sensitive(True)
                    else:
                        # Если с паролем не получилось, попробуем проверить архив более подробно
                        self.log_message("Проверка RAR архива более подробно")
                        self.check_rar_detailed(path)
                except Exception as e:
                    self.log_message(f"Ошибка проверки архива: {str(e)}", logging.ERROR)
                    self.show_toast(f"Error checking archive: {str(e)}")
                    self.apply_button.set_sensitive(False)
            elif path.lower().endswith(".exe"):
                # Placeholder for exe files
                self.log_message("EXE файлы пока не поддерживаются")
                self.show_toast("EXE files are not supported yet")
                self.apply_button.set_sensitive(False)
            else:
                self.log_message(f"Неподдерживаемый формат файла: {path}")
                self.show_toast("Unsupported file format")
                self.apply_button.set_sensitive(False)
                
        except GLib.Error as error:
            self.log_message(f"Ошибка доступа к файлу: {error.message}", logging.ERROR)
            self.show_toast(f"Error accessing file: {error.message}")
            self.apply_button.set_sensitive(False)

    def check_rar_detailed(self, path):
        """Более подробная проверка RAR-архива"""
        try:
            # Проверим наличие исполняемого файла unrar в системе
            unrar_path = rarfile.UNRAR_TOOL
            if not os.path.exists(unrar_path):
                # Проверяем альтернативные пути в зависимости от среды выполнения
                alt_paths = [
                    "/app/bin/unrar",  # В Flatpak
                    "/usr/bin/unrar",   # В большинстве систем Linux
                    "/bin/unrar",       # Альтернативный путь
                ]
                
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        self.show_toast(f"Использую unrar из {alt_path}")
                        rarfile.UNRAR_TOOL = alt_path
                        unrar_path = alt_path
                        break
                
                if not os.path.exists(rarfile.UNRAR_TOOL):
                    self.show_toast(f"unrar не найден! Проверьте, установлен ли он в системе.")
                    self.apply_button.set_sensitive(False)
                    return
            
            self.show_toast(f"Путь к unrar: {unrar_path}")
            
            # Попробуем сначала напрямую использовать subprocess для проверки архива
            try:
                # Пробуем прямой вызов unrar для получения списка файлов с паролем
                self.show_toast("Проверяю архив напрямую через unrar...")
                result = subprocess.run(
                    [unrar_path, "lb", "-p" + ONLINE_FIX_PASSWORD, path], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Если получили список файлов, значит архив рабочий
                    file_count = len(result.stdout.strip().split('\n'))
                    self.show_toast(f"Напрямую через unrar найдено {file_count} файлов")
                    
                    # Извлечем название игры из имени файла
                    self.extract_game_title(os.path.basename(path))
                    self.apply_button.set_sensitive(True)
                    return True
                else:
                    self.show_toast(f"Ошибка unrar: {result.stderr}")
            except Exception as e:
                self.show_toast(f"Ошибка при прямом вызове unrar: {str(e)}")
            
            # Если прямой метод не сработал, попробуем через rarfile
            self.show_toast("Проверяю архив через библиотеку rarfile...")
            
            # Попытка открыть архив без пароля для проверки структуры
            with rarfile.RarFile(path) as rar_file:
                try:
                    # Получаем список файлов
                    info_list = rar_file.infolist()
                    
                    # Выводим информацию о количестве файлов для диагностики
                    if not info_list:
                        self.show_toast("RAR архив пуст (0 файлов найдено)")
                        self.apply_button.set_sensitive(False)
                        return
                    
                    # Проверяем, защищен ли первый файл паролем
                    first_file = info_list[0]
                    is_encrypted = first_file.needs_password()
                    self.show_toast(f"Архив содержит {len(info_list)} файлов, защищен паролем: {is_encrypted}")
                    
                    if is_encrypted:
                        # Если файл требует пароль, ещё раз проверим с паролем
                        self.show_toast("Пробую открыть архив с паролем...")
                        if self.validate_with_password(path):
                            self.show_toast("Подтверждено: Это игра Online-Fix")
                            self.extract_game_title(os.path.basename(path))
                            self.apply_button.set_sensitive(True)
                        else:
                            self.show_toast("Неверный пароль или проблема с архивом")
                            self.apply_button.set_sensitive(False)
                    else:
                        self.show_toast(f"Архив содержит {len(info_list)} файлов, но не защищен паролем")
                        self.apply_button.set_sensitive(False)
                        
                except rarfile.BadRarFile as e:
                    self.show_toast(f"Ошибка RAR архива: {str(e)}")
                    self.apply_button.set_sensitive(False)
                except IndexError:
                    self.show_toast("Некорректная структура RAR архива")
                    self.apply_button.set_sensitive(False)
        except rarfile.RarExecError as e:
            self.show_toast(f"Ошибка запуска unrar: {str(e)}. Убедитесь, что unrar установлен.")
            self.apply_button.set_sensitive(False)
        except Exception as e:
            self.show_toast(f"Ошибка анализа архива: {str(e)}")
            self.apply_button.set_sensitive(False)

    def validate_with_password(self, path):
        try:
            self.show_toast(f"Открываю архив с паролем: {ONLINE_FIX_PASSWORD}")
            
            # Сначала попробуем прямой вызов unrar
            try:
                unrar_path = rarfile.UNRAR_TOOL
                result = subprocess.run(
                    [unrar_path, "t", "-p" + ONLINE_FIX_PASSWORD, path], 
                    capture_output=True, 
                    text=True, 
                    check=False
                )
                
                if result.returncode == 0:
                    self.show_toast("Архив успешно проверен через прямой вызов unrar")
                    return True
            except Exception as e:
                self.show_toast(f"Ошибка прямой проверки: {str(e)}")
            
            # Если прямой метод не сработал, используем rarfile
            with rarfile.RarFile(path, 'r') as rar_file:
                # Set the password
                rar_file.setpassword(ONLINE_FIX_PASSWORD)
                # Try to get file list
                files = rar_file.infolist()
                # Выведем детальную информацию о файлах в архиве
                file_count = len(files)
                self.show_toast(f"Найдено {file_count} файлов в архиве")
                
                if file_count > 0 and file_count < 5:  # Если файлов мало, покажем их имена
                    file_names = [f.filename for f in files[:5]]
                    self.show_toast(f"Файлы в архиве: {', '.join(file_names)}")
                
                # Если архив имеет хотя бы один файл и с паролем открылся без ошибок
                return file_count > 0
        except rarfile.BadRarFile as e:
            self.show_toast(f"Ошибка формата RAR: {str(e)}")
            return False
        except rarfile.PasswordRequired as e:
            self.show_toast(f"Требуется пароль: {str(e)}")
            return False
        except rarfile.RarExecError as e:
            self.show_toast(f"Ошибка выполнения unrar: {str(e)}")
            return False
        except Exception as e:
            self.show_toast(f"Ошибка проверки пароля: {str(e)}")
            return False

    def extract_game_title(self, filename):
        match = re.search(GAME_TITLE_REGEX, filename)
        if match:
            game_title = match.group(1).replace(".", " ")
            self.game_title.set_text(game_title)

    def show_toast(self, message):
        """Show a toast notification using the toast overlay with debouncing"""
        # Вызываем унифицированный метод логирования
        self.log_message(message)
        
        # Если сообщение такое же как предыдущее, сбросим таймер
        if self._toast_debounce_id is not None:
            GLib.source_remove(self._toast_debounce_id)
            self._toast_debounce_id = None
        
        # Запомним последнее сообщение
        self._last_toast_message = message
        
        # Устанавливаем новый таймер для дебаунсинга
        self._toast_debounce_id = GLib.timeout_add(
            TOAST_DEBOUNCE_DELAY, 
            self._do_show_toast
        )

    def log_message(self, message, level=logging.INFO):
        """Унифицированный метод для логирования и отображения сообщений
        
        Args:
            message: Сообщение для отображения и логирования
            level: Уровень логирования (по умолчанию INFO)
        """
        # Логирование в консоль
        logger.log(level, message)
        # Также печатаем в stdout для отладки
        print(f"[SOFL] {message}")

    def _do_show_toast(self):
        """Фактически показать тост после дебаунсинга"""
        if self._last_toast_message:
            toast = Adw.Toast.new(self._last_toast_message)
            toast.set_timeout(3)  # 3 секунды
            toast.set_priority(Adw.ToastPriority.HIGH)
            self.toast_overlay.add_toast(toast)
        
        # Сбрасываем ID таймера и сообщение
        self._toast_debounce_id = None
        self._last_toast_message = None
        
        # Возвращаем False, чтобы остановить повторения таймера
        return False

    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open

