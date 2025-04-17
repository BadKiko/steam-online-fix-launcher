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

# Проверка наличия flatpak-builder
if ! command -v flatpak-builder &> /dev/null; then
    log_message "error" "flatpak-builder не установлен. Пожалуйста, установите его и попробуйте снова."
    exit 1
fi

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
    
    # Выполняем сборку
    log_message "info" "Начало сборки..."
    if flatpak-builder "$BUILD_DIR" "$MANIFEST"; then
        log_message "info" "Сборка успешно завершена"
        # Сохраняем отметку времени сборки
        date > "$LAST_BUILD_TIMESTAMP_FILE"
    else
        log_message "error" "Сборка завершилась с ошибками"
        # Пробуем проверить и исправить metainfo.xml еще раз
        check_metainfo_xml
        log_message "warn" "Пробуем сборку еще раз..."
        if flatpak-builder "$BUILD_DIR" "$MANIFEST"; then
            log_message "info" "Вторая попытка сборки успешна"
            date > "$LAST_BUILD_TIMESTAMP_FILE"
        else
            log_message "error" "Вторая попытка сборки также завершилась с ошибками"
            exit 1
        fi
    fi
else
    log_message "info" "Сборка не требуется, используем существующую"
fi

# Запуск приложения
log_message "info" "Запуск приложения..."
if ! flatpak-builder --run "$BUILD_DIR" "$MANIFEST" "$APP_COMMAND"; then
    log_message "error" "Не удалось запустить приложение"
    exit 1
fi

exit 0