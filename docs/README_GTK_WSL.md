# Настройка подсветки GTK и Adwaita (ADW) в VS Code для Python через WSL

Данное руководство поможет настроить VS Code для работы с Python-проектами, использующими GTK4 и Adwaita (libadwaita) в среде WSL (Windows Subsystem for Linux).

## Предварительные требования

1. Windows 10/11 с установленной и настроенной WSL 2
2. Дистрибутив Linux в WSL (рекомендуется Ubuntu)
3. Visual Studio Code с расширением Remote - WSL
4. Проект на Python с использованием GTK4/Adwaita

## Автоматическая настройка

Для автоматической настройки запустите скрипт `setup_workspace.sh`:

```bash
chmod +x setup_workspace.sh
./setup_workspace.sh
```

Скрипт выполнит следующие действия:
- Установит необходимые пакеты GTK4 и Adwaita в системе WSL
- Создаст виртуальное окружение Python
- Установит pygobject и pygobject-stubs для поддержки типов
- Настроит файлы конфигурации VS Code для подсветки синтаксиса и автодополнения

## Ручная настройка

Если вы предпочитаете настраивать среду вручную:

### 1. Установка системных зависимостей в WSL

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-gi \
    gir1.2-gtk-4.0 gir1.2-adw-1 libgirepository1.0-dev \
    gcc libcairo2-dev pkg-config python3-dev
```

### 2. Настройка виртуального окружения Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pygobject
```

### 3. Установка стабов для GTK/Adwaita

```bash
PYGOBJECT_STUB_CONFIG=Gtk4,Gdk4,Adw1 pip install --no-cache-dir pygobject-stubs
```

### 4. Настройка VS Code

1. Установите расширения:
   - Remote - WSL
   - Python
   - Pylance

2. Создайте файл `.vscode/settings.json` с содержимым:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.extraPaths": [
        ".venv/lib/python3*/site-packages/gi-stubs",
        ".venv/lib/python3*/site-packages"
    ],
    "python.languageServer": "Pylance",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.stubPath": ".venv/lib/python3*/site-packages/pygobject-stubs"
}
```

## Как это работает

После настройки VS Code будет подсвечивать и предлагать автодополнение для объектов GTK и Adwaita. Типы и методы будут доступны для:

```python
from gi.repository import Gtk, Adw
```

Автодополнение будет работать для классов, методов и свойств GTK4 и Adwaita.

## Проверка работоспособности

Создайте тестовый файл с кодом:

```python
from gi.repository import Gtk, Adw

window = Adw.ApplicationWindow()
window.set_default_size(800, 600)
window.set_title("Тестовое окно")

header = Adw.HeaderBar()
window.set_content(header)
```

VS Code должен подсвечивать все классы и методы и предлагать автодополнение при вводе.

## Устранение неполадок

1. **Нет подсветки синтаксиса**: перезапустите VS Code или языковой сервер (F1 → "Developer: Reload Window")

2. **Ошибки импорта gi.repository**: убедитесь, что в системе установлены пакеты python3-gi и соответствующие GIR файлы

3. **Не работает автодополнение**: проверьте, что выбран правильный интерпретатор Python (из виртуального окружения) и Pylance активирован

## Дополнительные ресурсы

- [Документация PyGObject](https://pygobject.readthedocs.io/en/latest/)
- [Документация GTK4](https://docs.gtk.org/gtk4/)
- [Документация Adwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/) 