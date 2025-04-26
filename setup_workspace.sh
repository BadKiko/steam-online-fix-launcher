#!/bin/bash

# Скрипт для настройки рабочего пространства VS Code под проект GTK/Adwaita
# Для Steam Online Fix Launcher

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Определение дистрибутива Linux
DISTRO=""
if grep -q microsoft /proc/version; then
    ENV_TYPE="WSL"
    echo -e "${BLUE}Обнаружена среда WSL...${NC}"
    if grep -q "Ubuntu\|Debian" /etc/os-release; then
        DISTRO="debian"
    fi
else
    ENV_TYPE="Native Linux"
    echo -e "${BLUE}Обнаружена нативная среда Linux...${NC}"
    
    if [ -f /etc/arch-release ]; then
        DISTRO="arch"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/fedora-release ]; then
        DISTRO="fedora"
    fi
fi

if [ -z "$DISTRO" ]; then
    echo -e "${YELLOW}Не удалось определить дистрибутив Linux. Будет использована ручная установка.${NC}"
    echo -e "${YELLOW}Вам может потребоваться установить следующие пакеты вручную:${NC}"
    echo -e "${YELLOW}Python3, pip, venv, GTK4, libadwaita, gobject-introspection, cairo, pkg-config${NC}"
    
    read -p "Продолжить установку? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${BLUE}Дистрибутив: $DISTRO${NC}"
fi

# Установка необходимых пакетов для разработки GTK/Adwaita
echo -e "${BLUE}Установка пакетов для разработки GTK/Adwaita...${NC}"

if [ "$DISTRO" = "debian" ]; then
    sudo apt update
    sudo apt install -y python3-pip python3-venv python3-gi \
        gir1.2-gtk-4.0 gir1.2-adw-1 libgirepository1.0-dev \
        gcc libcairo2-dev pkg-config python3-dev
elif [ "$DISTRO" = "arch" ]; then
    sudo pacman -Syu --noconfirm
    sudo pacman -S --noconfirm python python-pip python-virtualenv \
        gtk4 libadwaita gobject-introspection cairo \
        gcc pkgconf python-gobject
elif [ "$DISTRO" = "fedora" ]; then
    sudo dnf update -y
    sudo dnf install -y python3-pip python3-devel python3-virtualenv \
        gtk4-devel libadwaita-devel gobject-introspection-devel \
        cairo-devel gcc-c++ pkgconfig python3-gobject
fi

# Создание виртуального окружения, если его еще нет
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Создание виртуального окружения Python...${NC}"
    python3 -m venv .venv
fi

# Активация виртуального окружения
echo -e "${BLUE}Активация виртуального окружения...${NC}"
source .venv/bin/activate

# Установка необходимых пакетов Python
echo -e "${BLUE}Установка необходимых пакетов Python...${NC}"
pip install --upgrade pip
pip install pygobject
pip install mypy pylint black

# Установка стабов для PyGObject с поддержкой GTK4 и Adwaita
echo -e "${BLUE}Установка стабов для PyGObject...${NC}"
PYGOBJECT_STUB_CONFIG=Gtk4,Gdk4 pip install --no-cache-dir pygobject-stubs

# Создание директории .vscode, если ее еще нет
mkdir -p .vscode

# Создание файла settings.json для VS Code
echo -e "${BLUE}Настройка VS Code для работы с GTK/Adwaita...${NC}"
cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.extraPaths": [
        ".venv/lib/python3*/site-packages/gi-stubs",
        ".venv/lib/python3*/site-packages"
    ],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.languageServer": "Pylance",
    "editor.formatOnSave": true,
    "python.formatting.provider": "none",
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.diagnosticMode": "workspace",
    "python.analysis.stubPath": ".venv/lib/python3*/site-packages/pygobject-stubs",
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter"
    }
}
EOF

# Создание файла pyrightconfig.json для лучшей поддержки типов
cat > pyrightconfig.json << EOF
{
    "include": [
        "sofl"
    ],
    "exclude": [
        ".venv"
    ],
    "typeCheckingMode": "basic",
    "reportMissingImports": true,
    "reportMissingTypeStubs": false,
    "pythonVersion": "3.10",
    "extraPaths": [
        ".venv/lib/python3*/site-packages"
    ]
}
EOF

# Создание файла .gitignore, если его еще нет
if [ ! -f ".gitignore" ]; then
    echo -e "${BLUE}Создание файла .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
ENV/

# VS Code
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json

# OS specific
.DS_Store
Thumbs.db
EOF
fi

echo -e "${GREEN}Настройка рабочего пространства завершена!${NC}"
echo -e "${BLUE}Для использования:${NC}"

if [ "$ENV_TYPE" = "WSL" ]; then
    echo -e "1. Установите расширение 'Remote - WSL' в VS Code на Windows"
    echo -e "2. Откройте проект в VS Code через WSL: нажмите F1, введите 'WSL: Open Folder in WSL'"
    echo -e "3. При открытии Python файлов VS Code предложит установить рекомендуемые расширения"
else
    echo -e "1. Откройте эту папку в VS Code"
    echo -e "2. При открытии Python файлов VS Code предложит установить рекомендуемые расширения"
fi

echo -e "4. Установите расширения: Python, Pylance, Black Formatter"
echo -e "5. Чтобы активировать подсветку GTK/Adwaita, возможно потребуется перезагрузить VS Code"

# Вывод подсказки о необходимых расширениях
echo -e "${BLUE}Рекомендуемые расширения VS Code:${NC}"
echo -e "- ms-python.python"
echo -e "- ms-python.vscode-pylance"
echo -e "- ms-python.black-formatter"
if [ "$ENV_TYPE" = "WSL" ]; then
    echo -e "- ms-vscode-remote.remote-wsl"
fi 