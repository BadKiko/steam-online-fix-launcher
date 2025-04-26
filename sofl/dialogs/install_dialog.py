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
import threading
from pathlib import Path
from sys import platform
from typing import Any, Optional, Callable
from time import time

from gi.repository import Adw, Gtk, GLib, Gio

from sofl import shared
from sofl.game import Game
from sofl.installer.online_fix_installer import OnlineFixInstaller
from sofl.details_dialog import DetailsDialog

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
    progress_spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    
    is_open: bool = False
    _toast_debounce_id: Optional[int] = None
    _last_toast_message: Optional[str] = None
    _current_task: Optional[threading.Thread] = None

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)
        
        # Create file dialog
        self.file_chooser = Gtk.FileDialog()
        
        # Hide status page, we'll use toast instead
        self.status_page.set_visible(False)
        
        # Подключаем обработчик кнопки Install
        self.apply_button.connect("clicked", self.on_install_clicked)
        
        # Если заполнен игрой, заполняем поля
        if game:
            self.game_path.set_text(game.path if game.path else "")
            self.game_title.set_text(game.name if game.name else "")
            
        # Инициализируем установщик
        self.installer = OnlineFixInstaller()

    def show_progress(self, show: bool, message: Optional[str] = None) -> None:
        """Показывает или скрывает индикатор загрузки
        
        Args:
            show: True для показа, False для скрытия
            message: Сообщение для отображения в индикаторе
        """
        def update_ui():
            # Сначала активируем спиннер, если показываем прогресс
            if show:
                # Важно: активируем спиннер до переключения страницы
                self.progress_spinner.set_spinning(True)
                # Иногда спиннер не обновляется из-за GTK оптимизаций,
                # поэтому делаем его явно видимым
                self.progress_spinner.set_visible(True)
            
            # Переключаем видимый стек в зависимости от состояния загрузки
            stack_page = "loading" if show else "content"
            self.main_stack.set_visible_child_name(stack_page)
            
            # Обновляем текст сообщения, если он предоставлен
            if message:
                self.progress_label.set_label(message)
            
            # Деактивируем кнопку Add во время загрузки
            if show:
                self.apply_button.set_sensitive(False)
            else:
                # Если скрываем - останавливаем спиннер
                self.progress_spinner.set_spinning(False)
            
            # Форсируем обновление UI без использования устаревшего events_pending
            # в GTK4 это автоматически обрабатывается через GLib.MainContext
            
            return False
            
        # Выполняем в основном потоке, так как это UI операция
        GLib.idle_add(update_ui)

    def run_async(self, func: Callable, callback: Optional[Callable] = None) -> None:
        """Запускает функцию асинхронно в отдельном потоке
        
        Args:
            func: Функция для выполнения
            callback: Обратный вызов после завершения (будет выполнен в основном потоке)
        """
        def thread_func():
            try:
                # Гарантируем, что UI обновится перед запуском долгой операции
                GLib.idle_add(lambda: None)
                
                result = func()
                if callback:
                    GLib.idle_add(lambda: callback(result))
            except Exception as e:
                self.log_message(f"Ошибка в асинхронной операции: {str(e)}", logging.ERROR)
                if callback:
                    GLib.idle_add(lambda: callback(None))
            finally:
                # Скрываем индикатор прогресса после завершения
                GLib.idle_add(lambda: self.show_progress(False))
                self._current_task = None
        
        # Остановить текущую задачу, если она есть
        if self._current_task and self._current_task.is_alive():
            self.log_message("Отмена предыдущей задачи")
            # Просто создадим новый поток (Python не позволяет безопасно остановить потоки)
        
        # Создаем и запускаем новый поток
        self._current_task = threading.Thread(target=thread_func)
        self._current_task.daemon = True
        self._current_task.start()

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
                
                # Показываем прогресс в UI
                self.show_progress(True, "Проверка файла...")
                
                # Проверяем, нужно ли скопировать файл из Flatpak
                if self.is_flatpak_path(path):
                    self.log_message(f"Обнаружен путь Flatpak: {path}")
                    
                    # Асинхронно копируем файл
                    self.show_progress(True, "Копирование файла...")
                    
                    def copy_file():
                        return self.copy_flatpak_file(path)
                    
                    def after_copy(new_path):
                        if new_path and new_path != path:
                            self.log_message(f"Используем скопированный файл: {new_path}")
                            self.game_path.set_text(new_path)
                        
                        # Проверяем файл после копирования
                        self.check_file_async(new_path or path)
                    
                    self.run_async(copy_file, after_copy)
                else:
                    # Форматируем путь для отображения
                    display_path = self.format_path_for_display(path)
                    self.game_path.set_text(path)
                    
                    # Асинхронно проверяем файл
                    self.check_file_async(path)
                    
        except GLib.Error as error:
            self.log_message(f"Ошибка доступа к файлу: {error.message}", logging.ERROR)
            self.show_toast(f"Error accessing file: {error.message}")
            return

    def check_file_async(self, path: str) -> None:
        """Асинхронная проверка файла игры
        
        Args:
            path: Путь к файлу
        """
        self.show_progress(True, "Проверка файла игры...")
        
        def check_task():
            file = Gio.File.new_for_path(path)
            try:
                if not file.query_exists():
                    self.log_message(f"Файл не существует: {path}", logging.ERROR)
                    self.show_toast("File does not exist")
                    return False
                
                # Проверяем файл
                try:
                    file_stream = file.read()
                    file_stream.close()
                    
                    # Оптимизированная проверка архива
                    if path.lower().endswith(".rar"):
                        self.show_progress(True, "Проверка архива...")
                        
                        # Быстрая проверка архива - только открываем его с паролем, не распаковывая
                        if self.verify_rar_password(path):
                            # Извлекаем название игры из имени файла
                            self.extract_game_title(os.path.basename(path))
                            self.show_toast("Confirmed: This is an Online-Fix game")
                            return True
                        else:
                            self.show_toast("Not an Online-Fix game or invalid archive")
                            return False
                            
                    elif path.lower().endswith(".exe"):
                        self.log_message("EXE файлы пока не поддерживаются")
                        self.show_toast("EXE files are not supported yet")
                        return False
                    else:
                        self.log_message("Неподдерживаемый формат файла")
                        self.show_toast("Unsupported file format")
                        return False
                except Exception as e:
                    self.log_message(f"Ошибка при проверке файла: {str(e)}", logging.ERROR)
                    self.show_toast(f"Error checking file: {str(e)}")
                    return False
            except GLib.Error as error:
                self.log_message(f"Ошибка доступа к файлу: {error.message}", logging.ERROR)
                self.show_toast(f"Error accessing file: {error.message}")
                return False
        
        def after_check(result):
            self.apply_button.set_sensitive(bool(result))
        
        self.run_async(check_task, after_check)

    def on_path_changed(self, entry, pspec):
        path = self.game_path.get_text()
        if path:
            # Проверяем, нужно ли скопировать файл из Flatpak
            if self.is_flatpak_path(path):
                self.show_progress(True, "Обнаружен путь Flatpak...")
                
                def copy_file():
                    return self.copy_flatpak_file(path)
                
                def after_copy(new_path):
                    if new_path and new_path != path:
                        self.log_message(f"Используем скопированный файл: {new_path}")
                        self.game_path.set_text(new_path)
                    
                    self.check_file_async(new_path or path)
                
                self.run_async(copy_file, after_copy)
            else:
                self.check_file_async(path)
        else:
            self.show_toast("Specify a game file path to check")
            self.apply_button.set_sensitive(False)

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

    def verify_rar_password(self, path: str) -> bool:
        """Быстрая проверка архива с паролем без распаковки
        
        Args:
            path: Путь к файлу
            
        Returns:
            bool: True если архив валидный и открывается с паролем, иначе False
        """
        try:
            # Способ 1: Используем unrar напрямую для тестирования архива (самый быстрый)
            self.log_message("Быстрая проверка архива через unrar")
            try:
                unrar_path = rarfile.UNRAR_TOOL
                result = subprocess.run(
                    [unrar_path, "t", "-p" + ONLINE_FIX_PASSWORD, "-idp", path], 
                    capture_output=True, 
                    text=True, 
                    check=False,
                    timeout=10  # Таймаут в секундах
                )
                
                if result.returncode == 0:
                    self.log_message("Архив прошел проверку через unrar")
                    return True
                else:
                    self.log_message(f"Архив не прошел проверку: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                self.log_message("Проверка архива заняла слишком много времени, отмена")
                return False
            except Exception as e:
                self.log_message(f"Ошибка при проверке через unrar: {str(e)}")
                
                # Способ 2: Используем rarfile для проверки (резервный вариант)
                self.log_message("Проверка архива через rarfile")
                try:
                    with rarfile.RarFile(path) as rf:
                        rf.setpassword(ONLINE_FIX_PASSWORD)
                        # Получаем только список файлов, не распаковываем
                        info_list = rf.infolist()
                        # Если получили список файлов с паролем, значит архив правильный
                        return len(info_list) > 0
                except rarfile.PasswordRequired:
                    # Если требуется пароль, но не тот что мы указали, это не Online-Fix архив
                    self.log_message("Архив защищен другим паролем")
                    return False
                except Exception as e:
                    self.log_message(f"Ошибка при проверке через rarfile: {str(e)}")
                    return False
        except Exception as e:
            self.log_message(f"Общая ошибка при проверке архива: {str(e)}")
            return False

    def extract_game_title(self, filename):
        """Извлекает название игры из имени файла"""
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

    def on_install_clicked(self, button):
        """Обработчик нажатия на кнопку Install (Установка игры)"""
        # Получаем путь к архиву и название игры
        archive_path = self.game_path.get_text()
        game_name = self.game_title.get_text()
        
        if not archive_path or not game_name:
            self.show_toast("Выберите архив и укажите название игры")
            return
            
        # Проверяем, существует ли файл
        if not os.path.exists(archive_path):
            self.show_toast("Файл не существует")
            return
            
        # Показываем прогресс
        self.show_progress(True, "Подготовка к установке...")
        
        # Запускаем установку асинхронно
        def install_task():
            def progress_update(progress, message):
                GLib.idle_add(lambda: self.update_installation_progress(progress, message))
                
            # Вызываем метод установки из установщика
            success, result, executable = self.installer.install_game(
                archive_path, 
                game_name, 
                progress_update
            )
            
            return success, result, executable
            
        def after_install(result):
            if not result:
                self.show_toast("Ошибка при установке игры")
                return
                
            success, install_path, executable = result
            
            if success:
                self.show_toast(f"Игра успешно установлена в: {install_path}")
                
                # Создаем новую игру
                try:
                    # Инкрементально создаем ID для новой игры
                    source_id = "online-fix"
                    numbers = [0]
                    for game_id in shared.store.source_games.get(source_id, set()):
                        prefix = "online-fix_"
                        if not game_id.startswith(prefix):
                            continue
                        try:
                            numbers.append(int(game_id.replace(prefix, "", 1)))
                        except ValueError:
                            pass
                    
                    game_number = max(numbers) + 1
                    
                    # Создаем новую игру
                    new_game = Game({
                        "game_id": f"online-fix_{game_number}",
                        "hidden": False,
                        "source": source_id,
                        "name": game_name,
                        "path": install_path,
                        "executable":  str(Path(shared.home) / "Games" / "Online-Fix" / executable) if executable else "",
                        "added": int(time()),
                    })
                    
                    # Добавляем игру в хранилище
                    shared.store.add_game(new_game, {}, run_pipeline=False)
                    new_game.save()
                    
                    # Скрываем текущий диалог установки
                    self.hide()
                    
                    # Показываем диалог деталей игры для завершения настройки
                    GLib.idle_add(lambda: self.show_details_dialog(new_game))
                    
                except Exception as e:
                    self.log_message(f"Ошибка при добавлении игры: {str(e)}", logging.ERROR)
                    self.show_toast(f"Игра установлена, но не добавлена в библиотеку: {str(e)}")
                    
                    # Закрываем диалог после успешной установки через таймаут
                    GLib.timeout_add(1500, lambda: self.hide() or False)
            else:
                self.show_toast(f"Ошибка при установке игры: {install_path}")
        
        self.run_async(install_task, after_install)
    
    def show_details_dialog(self, game):
        """Показывает диалог с деталями игры для редактирования
        
        Args:
            game: Игра для редактирования
        """
        try:
            if DetailsDialog.is_open:
                return
            
            # Устанавливаем флаг для диалога деталей
            DetailsDialog.install_mode = True
            
            # Создаем и показываем диалог
            dialog = DetailsDialog(game)
            dialog.present(self.get_root())
        except Exception as e:
            self.log_message(f"Ошибка при открытии диалога деталей: {str(e)}", logging.ERROR)
            self.show_toast(f"Не удалось открыть диалог настройки игры: {str(e)}")
    
    def update_installation_progress(self, progress: float, message: str) -> bool:
        """Обновляет индикатор прогресса установки
        
        Args:
            progress: Прогресс от 0 до 1
            message: Сообщение о текущем статусе
            
        Returns:
            bool: False для однократного вызова через GLib.idle_add
        """
        self.show_progress(True, message)
        return False

