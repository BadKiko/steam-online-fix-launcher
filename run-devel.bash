#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Конфигурация
BUILD_DIR="build-dir"
MANIFEST="build-aux/flatpak/org.badkiko.sofl.Devel.json"
APP_COMMAND="sofl"
LAST_BUILD_TIMESTAMP_FILE=".last_build_timestamp"
BLUEPRINT_REPO="https://gitlab.gnome.org/jwestman/blueprint-compiler.git"
BLUEPRINT_TAG="v0.16.0"
BLUEPRINT_DIR="subprojects/blueprint-compiler"
FLATPAK_BUILDER_APP="org.flatpak.Builder"
USE_NATIVE_BUILDER=true # По умолчанию используем нативный flatpak-builder

# Проверка, запущен ли скрипт в WSL
is_wsl() {
    if grep -qi microsoft /proc/version; then
        return 0  # Это WSL
    else
        return 1  # Это не WSL
    fi
}

# Проверяем, находимся ли мы в WSL
WSL_ENV=false
if is_wsl; then
    WSL_ENV=true
fi

# Функция для установки flatpak и flatpak-builder
install_flatpak_builder() {
    log_message "info" "Проверка наличия flatpak и flatpak-builder..."
    
    # Проверяем, установлен ли sudo
    HAS_SUDO=false
    if command -v sudo &> /dev/null; then
        HAS_SUDO=true
    fi
    
    # Определяем дистрибутив
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    else
        DISTRO="unknown"
    fi
    
    log_message "info" "Обнаружен дистрибутив: $DISTRO"
    
    # Проверка установлен ли flatpak
    if ! command -v flatpak &> /dev/null; then
        log_message "warn" "flatpak не установлен, устанавливаю..."
        
        case $DISTRO in
            "debian"|"ubuntu"|"linuxmint"|"pop"|"elementary"|"zorin")
                if [ "$HAS_SUDO" = true ]; then
                    sudo apt update
                    sudo apt install -y flatpak
                    
                    # Устанавливаем плагины для Software Center
                    if command -v gnome-shell &> /dev/null; then
                        log_message "info" "Обнаружена среда GNOME, устанавливаю соответствующий плагин..."
                        sudo apt install -y gnome-software-plugin-flatpak
                    elif command -v plasmashell &> /dev/null; then
                        log_message "info" "Обнаружена среда KDE, устанавливаю соответствующий плагин..."
                        sudo apt install -y plasma-discover-backend-flatpak
                    fi
                else
                    apt update
                    apt install -y flatpak
                    
                    # Устанавливаем плагины для Software Center
                    if command -v gnome-shell &> /dev/null; then
                        log_message "info" "Обнаружена среда GNOME, устанавливаю соответствующий плагин..."
                        apt install -y gnome-software-plugin-flatpak
                    elif command -v plasmashell &> /dev/null; then
                        log_message "info" "Обнаружена среда KDE, устанавливаю соответствующий плагин..."
                        apt install -y plasma-discover-backend-flatpak
                    fi
                fi
                ;;
            "fedora"|"rhel"|"centos"|"almalinux"|"rocky")
                if [ "$HAS_SUDO" = true ]; then
                    sudo dnf install -y flatpak
                else
                    dnf install -y flatpak
                fi
                ;;
            "arch"|"manjaro"|"endeavouros")
                if [ "$HAS_SUDO" = true ]; then
                    sudo pacman -Sy --noconfirm flatpak
                else
                    pacman -Sy --noconfirm flatpak
                fi
                ;;
            "opensuse"|"opensuse-leap"|"opensuse-tumbleweed"|"suse")
                if [ "$HAS_SUDO" = true ]; then
                    sudo zypper install -y flatpak
                else
                    zypper install -y flatpak
                fi
                ;;
            "alpine")
                if [ "$HAS_SUDO" = true ]; then
                    sudo apk add flatpak
                else
                    apk add flatpak
                fi
                ;;
            *)
                log_message "error" "Неизвестный дистрибутив. Пожалуйста, установите flatpak вручную согласно инструкции: https://flatpak.org/setup/"
                return 1
                ;;
        esac
    fi
    
    # Проверяем, установлен ли flatpak
    if ! command -v flatpak &> /dev/null; then
        log_message "error" "Не удалось установить flatpak. Пожалуйста, установите его вручную."
        return 1
    fi
    
    # Добавляем репозиторий Flathub (сначала для пользователя, затем если не получилось - глобально)
    log_message "info" "Добавление репозитория Flathub..."
    if ! flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo; then
        if [ "$HAS_SUDO" = true ]; then
            sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
        else
            flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
        fi
    fi
    
    # Пытаемся установить нативный flatpak-builder
    log_message "info" "Попытка установить нативный flatpak-builder..."
    case $DISTRO in
        "debian"|"ubuntu"|"linuxmint"|"pop"|"elementary"|"zorin")
            if [ "$HAS_SUDO" = true ]; then
                if sudo apt install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            else
                if apt install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            fi
            ;;
        "fedora"|"rhel"|"centos"|"almalinux"|"rocky")
            if [ "$HAS_SUDO" = true ]; then
                if sudo dnf install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            else
                if dnf install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            fi
            ;;
        "arch"|"manjaro"|"endeavouros")
            if [ "$HAS_SUDO" = true ]; then
                if sudo pacman -Sy --noconfirm flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            else
                if pacman -Sy --noconfirm flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            fi
            ;;
        "opensuse"|"opensuse-leap"|"opensuse-tumbleweed"|"suse")
            if [ "$HAS_SUDO" = true ]; then
                if sudo zypper install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            else
                if zypper install -y flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            fi
            ;;
        "alpine")
            if [ "$HAS_SUDO" = true ]; then
                if sudo apk add flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            else
                if apk add flatpak-builder; then
                    log_message "info" "Нативный flatpak-builder успешно установлен"
                    USE_NATIVE_BUILDER=true
                    return 0
                else
                    log_message "warn" "Не удалось установить нативный flatpak-builder, попробую использовать версию через Flatpak"
                fi
            fi
            ;;
        *)
            log_message "warn" "Неизвестный дистрибутив, попробую установить Flatpak Builder через Flatpak"
            ;;
    esac
    
    # Если не удалось установить нативный flatpak-builder, пробуем версию через Flatpak
    log_message "info" "Установка Flatpak Builder через Flatpak..."
    if ! flatpak list --app | grep -q "$FLATPAK_BUILDER_APP"; then
        if flatpak install --user -y flathub "$FLATPAK_BUILDER_APP"; then
            log_message "info" "Flatpak Builder успешно установлен через Flatpak"
            USE_NATIVE_BUILDER=false
            return 0
        else
            log_message "error" "Не удалось установить Flatpak Builder через Flatpak. Пожалуйста, установите его вручную."
            return 1
        fi
    else
        log_message "info" "Flatpak Builder уже установлен через Flatpak"
        USE_NATIVE_BUILDER=false
        return 0
    fi
}

# Функция вызова flatpak-builder
run_flatpak_builder() {
    local command=$1
    shift
    
    if [ "$USE_NATIVE_BUILDER" = true ]; then
        log_message "info" "Использую нативный flatpak-builder..."
        flatpak-builder $command "$@"
        return $?
    else
        log_message "info" "Использую Flatpak Builder через Flatpak..."
        # Используем расширенные привилегии для доступа к SDK
        flatpak run --filesystem=host --share=network --socket=session-bus --socket=system-bus --env=FLATPAK_SYSTEM_DIR=/var/lib/flatpak --env=FLATPAK_USER_DIR=$HOME/.local/share/flatpak $FLATPAK_BUILDER_APP $command "$@"
        return $?
    fi
}

# Функция для вывода сообщений
log_message() {
    local type=$1
    local message=$2
    
    case $type in
        "info")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "warn")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# Проверка доступности интернета
check_internet() {
    log_message "info" "Проверка интернет-соединения..."
    if ping -c 1 google.com &> /dev/null || ping -c 1 8.8.8.8 &> /dev/null; then
        log_message "info" "Интернет-соединение доступно"
        return 0
    else
        log_message "warn" "Интернет-соединение недоступно, проверка альтернативных серверов..."
        if ping -c 1 1.1.1.1 &> /dev/null; then
            log_message "info" "Интернет-соединение доступно (альтернативный сервер)"
            return 0
        else
            log_message "error" "Интернет-соединение недоступно"
            return 1
        fi
    fi
}

# Проверка и установка Flatpak Builder
if ! command -v flatpak-builder &> /dev/null && ! flatpak list --app | grep -q "$FLATPAK_BUILDER_APP"; then
    if ! install_flatpak_builder; then
        log_message "error" "Flatpak Builder не установлен и не может быть установлен автоматически. Пожалуйста, установите его вручную и попробуйте снова."
        exit 1
    fi
elif command -v flatpak-builder &> /dev/null; then
    log_message "info" "Обнаружен нативный flatpak-builder"
    USE_NATIVE_BUILDER=true
elif flatpak list --app | grep -q "$FLATPAK_BUILDER_APP"; then
    log_message "info" "Обнаружен Flatpak Builder через Flatpak"
    USE_NATIVE_BUILDER=false
fi

# Функция для проверки и установки необходимых SDK Flatpak
check_install_sdk() {
    # Извлечение информации о runtime и SDK из манифеста
    if [ ! -f "$MANIFEST" ]; then
        log_message "error" "Манифест $MANIFEST не найден"
        exit 1
    fi
    
    # Извлекаем информацию о runtime, версии и SDK из JSON файла
    RUNTIME=$(grep -o '"runtime": "[^"]*"' "$MANIFEST" | cut -d'"' -f4)
    RUNTIME_VERSION=$(grep -o '"runtime-version": "[^"]*"' "$MANIFEST" | cut -d'"' -f4)
    SDK=$(grep -o '"sdk": "[^"]*"' "$MANIFEST" | cut -d'"' -f4)
    
    if [ -z "$RUNTIME" ] || [ -z "$RUNTIME_VERSION" ] || [ -z "$SDK" ]; then
        log_message "error" "Не удалось извлечь информацию о runtime/sdk из манифеста"
        exit 1
    fi
    
    log_message "info" "Проверка наличия $SDK/$RUNTIME_VERSION..."
    
    # Проверяем, установлен ли SDK
    if ! flatpak list | grep -q "$SDK//$RUNTIME_VERSION"; then
        log_message "warn" "$SDK версии $RUNTIME_VERSION не установлен. Устанавливаю..."
        
        # Устанавливаем SDK только для пользователя (--user), чтобы избежать ошибки с правами доступа
        if flatpak install --user -y flathub "$SDK//$RUNTIME_VERSION"; then
            log_message "info" "$SDK версии $RUNTIME_VERSION успешно установлен для пользователя"
        else
            # Пробуем установить из другого репозитория
            log_message "warn" "Не удалось установить из Flathub, пробую GNOME репозиторий..."
            if flatpak install --user -y gnome-nightly "$SDK//$RUNTIME_VERSION"; then
                log_message "info" "$SDK версии $RUNTIME_VERSION успешно установлен из GNOME репозитория"
            else
                # Пробуем более старую версию, если указанная не найдена
                log_message "warn" "Версия $RUNTIME_VERSION не найдена, пробую найти другие доступные версии..."
                
                # Получаем список доступных версий
                AVAILABLE_SDK_VERSIONS=$(flatpak remote-ls --columns=ref flathub | grep "$SDK" | sort -r)
                if [ -n "$AVAILABLE_SDK_VERSIONS" ]; then
                    log_message "info" "Найдены доступные версии SDK: $AVAILABLE_SDK_VERSIONS"
                    # Берем первую (самую новую) версию
                    ALTERNATIVE_VERSION=$(echo "$AVAILABLE_SDK_VERSIONS" | head -n1 | sed -E 's/.*\/([0-9.]+)\/.*/\1/')
                    
                    if [ -n "$ALTERNATIVE_VERSION" ]; then
                        log_message "info" "Попытка установить альтернативную версию: $ALTERNATIVE_VERSION"
                        if flatpak install --user -y flathub "$SDK//$ALTERNATIVE_VERSION"; then
                            log_message "info" "$SDK версии $ALTERNATIVE_VERSION успешно установлен для пользователя"
                            # Обновляем манифест с новой версией
                            log_message "warn" "Обновляю манифест для использования версии $ALTERNATIVE_VERSION"
                            sed -i "s/\"runtime-version\": \"$RUNTIME_VERSION\"/\"runtime-version\": \"$ALTERNATIVE_VERSION\"/" "$MANIFEST"
                            RUNTIME_VERSION="$ALTERNATIVE_VERSION"
                        else
                            log_message "error" "Не удалось установить $SDK"
                            exit 1
                        fi
                    else
                        log_message "error" "Не удалось найти альтернативную версию для $SDK"
                        exit 1
                    fi
                else
                    log_message "error" "Не удалось установить $SDK версии $RUNTIME_VERSION"
                    exit 1
                fi
            fi
        fi
    else
        log_message "info" "$SDK версии $RUNTIME_VERSION уже установлен"
    fi
    
    # Также проверяем наличие runtime
    if ! flatpak list | grep -q "$RUNTIME//$RUNTIME_VERSION"; then
        log_message "warn" "$RUNTIME версии $RUNTIME_VERSION не установлен. Устанавливаю..."
        if flatpak install --user -y flathub "$RUNTIME//$RUNTIME_VERSION"; then
            log_message "info" "$RUNTIME версии $RUNTIME_VERSION успешно установлен для пользователя"
        else
            # Пробуем установить из другого репозитория
            log_message "warn" "Не удалось установить из Flathub, пробую GNOME репозиторий..."
            if flatpak install --user -y gnome-nightly "$RUNTIME//$RUNTIME_VERSION"; then
                log_message "info" "$RUNTIME версии $RUNTIME_VERSION успешно установлен из GNOME репозитория"
            else
                log_message "error" "Не удалось установить $RUNTIME версии $RUNTIME_VERSION"
                exit 1
            fi
        fi
    else
        log_message "info" "$RUNTIME версии $RUNTIME_VERSION уже установлен"
    fi
    
    # Обновляем переменную XDG_DATA_DIRS если она не содержит пути flatpak
    if [[ ! "$XDG_DATA_DIRS" == *"flatpak/exports/share"* ]]; then
        export XDG_DATA_DIRS="$HOME/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
        log_message "info" "Обновлена переменная XDG_DATA_DIRS для поиска Flatpak приложений"
    fi
}

# Предварительная загрузка blueprint-compiler
prepare_blueprint_compiler() {
    log_message "info" "Проверка наличия blueprint-compiler..."
    
    # Создаем директорию subprojects, если её нет
    mkdir -p "subprojects"
    
    # Проверяем, существует ли уже blueprint-compiler
    if [ -d "$BLUEPRINT_DIR" ] && [ -f "$BLUEPRINT_DIR/meson.build" ]; then
        log_message "info" "blueprint-compiler уже загружен"
        
        # Обновляем до нужной версии
        cd "$BLUEPRINT_DIR" || return 1
        if git fetch origin && git checkout "$BLUEPRINT_TAG"; then
            log_message "info" "blueprint-compiler обновлен до версии $BLUEPRINT_TAG"
            cd - || return 1
            return 0
        else
            log_message "warn" "Не удалось обновить blueprint-compiler, пробую заново клонировать..."
            cd - || return 1
        fi
    fi
    
    # Удаляем существующую директорию, если она повреждена или не удалось обновить
    if [ -d "$BLUEPRINT_DIR" ]; then
        log_message "warn" "Удаление существующей директории blueprint-compiler..."
        rm -rf "$BLUEPRINT_DIR"
    fi
    
    # Клонируем репозиторий
    log_message "info" "Клонирование blueprint-compiler версии $BLUEPRINT_TAG..."
    if git clone --depth 1 --branch "$BLUEPRINT_TAG" "$BLUEPRINT_REPO" "$BLUEPRINT_DIR"; then
        log_message "info" "blueprint-compiler успешно клонирован"
        return 0
    else
        # Пробуем альтернативный репозиторий через GitHub зеркало
        log_message "warn" "Не удалось клонировать из GNOME GitLab, пробую через GitHub зеркало..."
        GITHUB_MIRROR="https://github.com/jwestman/blueprint-compiler.git"
        if git clone --depth 1 --branch "$BLUEPRINT_TAG" "$GITHUB_MIRROR" "$BLUEPRINT_DIR"; then
            log_message "info" "blueprint-compiler успешно клонирован через GitHub зеркало"
            return 0
        else
            log_message "error" "Не удалось клонировать blueprint-compiler"
            return 1
        fi
    fi
}

# Патч для отключения тестов blueprint-compiler при проблемах с WSLg
patch_blueprint_tests() {
    local meson_file="$BLUEPRINT_DIR/meson.build"
    
    if [ "$WSL_ENV" = true ] && [ -f "$meson_file" ]; then
        log_message "info" "Запущено в WSL, применяю патч для отключения тестов blueprint-compiler..."
        
        # Создаем резервную копию
        cp "$meson_file" "${meson_file}.bak"
        
        # Отключаем тесты в файле meson.build
        sed -i 's/subdir(.tests.)/# Тесты отключены для WSL/' "$meson_file"
        
        log_message "info" "Патч применен, тесты blueprint-compiler отключены"
    fi
}

# Проверка и исправление файла metainfo.xml
check_metainfo_xml() {
    local expected_file="data/org.badkiko.sofl.Devel.metainfo.xml"
    local configured_file="${BUILD_DIR}/files/share/metainfo/org.badkiko.sofl.Devel.metainfo.xml"
    
    if [ ! -f "$expected_file" ] && [ -f "$configured_file" ]; then
        log_message "warn" "Отсутствует $expected_file, создаю копию из сборки..."
        mkdir -p "$(dirname "$expected_file")"
        cp "$configured_file" "$expected_file"
        return 0
    elif [ ! -f "$expected_file" ] && [ ! -f "$configured_file" ]; then
        log_message "warn" "Файл metainfo.xml отсутствует, создаю пустой заглушку..."
        mkdir -p "$(dirname "$expected_file")"
        echo '<?xml version="1.0" encoding="UTF-8"?><component type="desktop-application"></component>' > "$expected_file"
        return 0
    fi
    return 0
}

# Функция для настройки D-Bus в WSL
setup_dbus_for_wsl() {
    if [ "$WSL_ENV" = true ]; then
        log_message "info" "Запущено в WSL, настраиваю D-Bus..."
        
        # Проверяем запущен ли dbus-daemon
        if ! pgrep -x dbus-daemon > /dev/null; then
            log_message "warn" "D-Bus не запущен, запускаю..."
            
            # Проверяем установлен ли dbus
            if ! command -v dbus-daemon > /dev/null; then
                log_message "warn" "Пакет D-Bus не найден, устанавливаю..."
                if [ "$HAS_SUDO" = true ]; then
                    sudo apt-get update && sudo apt-get install -y dbus-x11
                else
                    apt-get update && apt-get install -y dbus-x11
                fi
            fi
            
            # Запускаем dbus-daemon
            dbus-daemon --session --address=unix:path=/tmp/dbus-session-socket --nofork --print-address &
            DBUS_PID=$!
            log_message "info" "D-Bus запущен с PID $DBUS_PID"
            
            # Небольшая пауза для запуска
            sleep 1
            
            # Устанавливаем переменные окружения
            export DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus-session-socket"
        else
            log_message "info" "D-Bus уже запущен"
            
            # Если dbus уже запущен, но переменные не установлены
            if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
                export DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus-session-socket"
                log_message "info" "Установлена переменная DBUS_SESSION_BUS_ADDRESS"
            fi
        fi
    fi
}

# Проверяем интернет-соединение
check_internet

# Проверяем наличие SDK перед началом сборки
check_install_sdk

# Подготавливаем blueprint-compiler
prepare_blueprint_compiler

# Патчим тесты blueprint-compiler для WSL, если необходимо
patch_blueprint_tests

# Проверка наличия директории build-dir и ее состояния
build_required=false
rebuild_reason=""

if [ ! -d "$BUILD_DIR" ] || [ -z "$(ls -A $BUILD_DIR 2>/dev/null)" ]; then
    build_required=true
    rebuild_reason="Директория сборки отсутствует или пуста"
else
    # Проверяем изменения в исходных файлах
    if [ -f "$LAST_BUILD_TIMESTAMP_FILE" ]; then
        LAST_BUILD=$(cat "$LAST_BUILD_TIMESTAMP_FILE")
        
        # Проверяем, были ли изменения в каталогах с исходным кодом
        # и вычитаем 1 чтобы избежать ложного обнаружения изменений
        CHANGED_FILES=$(find . -type f -not -path "./$BUILD_DIR/*" -not -path "./.git/*" -newer "$LAST_BUILD_TIMESTAMP_FILE" | wc -l)
        CHANGED_FILES=$((CHANGED_FILES - 1))
        
        if [ "$CHANGED_FILES" -gt 0 ]; then
            build_required=true
            rebuild_reason="Обнаружены изменения в исходных файлах ($CHANGED_FILES файлов)"
        else
            log_message "info" "Изменений в файлах не обнаружено"
        fi
    else
        build_required=true
        rebuild_reason="Не найден файл с отметкой времени последней сборки"
    fi
fi

# Проверяем metainfo.xml перед сборкой
check_metainfo_xml

# Очищаем директорию сборки, если требуется сборка
if [ "$build_required" = true ]; then
    if [ -d "$BUILD_DIR" ] && [ ! -z "$(ls -A $BUILD_DIR 2>/dev/null)" ]; then
        log_message "info" "Очистка директории сборки..."
        rm -rf "$BUILD_DIR"
    fi
    mkdir -p "$BUILD_DIR"
fi

# Выполняем сборку, если необходимо
if [ "$build_required" = true ]; then
    log_message "info" "Требуется сборка: $rebuild_reason"
    
    # Настройки для WSL
    BUILD_OPTS=""
    if [ "$WSL_ENV" = true ]; then
        log_message "info" "Сборка в WSL, добавляю специальные опции..."
    fi
    
    # Выполняем сборку
    log_message "info" "Начало сборки..."
    if run_flatpak_builder "$BUILD_OPTS" "$BUILD_DIR" "$MANIFEST"; then
        log_message "info" "Сборка успешно завершена"
        # Сохраняем отметку времени сборки
        date > "$LAST_BUILD_TIMESTAMP_FILE"
    else
        log_message "error" "Сборка завершилась с ошибками"
        # Пробуем проверить и исправить metainfo.xml еще раз
        check_metainfo_xml
        
        # Проверяем blueprint-compiler снова перед второй попыткой
        prepare_blueprint_compiler
        
        # Патчим тесты blueprint-compiler еще раз
        patch_blueprint_tests
        
        log_message "warn" "Пробуем сборку еще раз с принудительной очисткой..."
        if run_flatpak_builder "--force-clean $BUILD_OPTS" "$BUILD_DIR" "$MANIFEST"; then
            log_message "info" "Вторая попытка сборки успешна"
            date > "$LAST_BUILD_TIMESTAMP_FILE"
        else
            # Явно добавляем пропуск всех проверок, если другие методы не сработали
            log_message "warn" "Вторая попытка тоже не удалась, пробую с другими опциями..."
            if run_flatpak_builder "--force-clean" "$BUILD_DIR" "$MANIFEST"; then
                log_message "info" "Третья попытка сборки успешна"
                date > "$LAST_BUILD_TIMESTAMP_FILE"
            else
                log_message "error" "Все попытки сборки завершились с ошибками"
                exit 1
            fi
        fi
    fi
else
    log_message "info" "Сборка не требуется, используем существующую"
fi

# Запуск приложения
log_message "info" "Запуск приложения..."

# Настраиваем D-Bus для WSL перед запуском
setup_dbus_for_wsl

if [ "$USE_NATIVE_BUILDER" = true ]; then
    if ! flatpak-builder --run "$BUILD_DIR" "$MANIFEST" "$APP_COMMAND"; then
        log_message "error" "Не удалось запустить приложение"
        exit 1
    fi
else
    if ! flatpak run --filesystem=host $FLATPAK_BUILDER_APP --run "$BUILD_DIR" "$MANIFEST" "$APP_COMMAND"; then
        log_message "error" "Не удалось запустить приложение"
        exit 1
    fi
fi

exit 0