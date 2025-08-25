# SOFL - Packaging

Этот каталог содержит скрипты и файлы для сборки пакетов SOFL для различных Linux дистрибутивов.

## Поддерживаемые форматы пакетов

- **Flatpak** - Универсальный формат для всех Linux дистрибутивов
- **Debian (.deb)** - Для Debian, Ubuntu и производных
- **Arch Linux** - PKGBUILD для сборки в Arch Linux

## Быстрый старт

### Сборка всех пакетов

```bash
# Сборка всех типов пакетов с версией из meson.build
./scripts/build_all.sh

# Сборка всех пакетов с указанной версией
./scripts/build_all.sh 1.0.0

# Сборка только определенных пакетов
./scripts/build_all.sh 1.0.0 "flatpak deb"
```

### Сборка отдельных пакетов

#### Flatpak

```bash
cd packaging/flatpak
./build.sh [version]
```

#### Debian

```bash
cd packaging/debian
./build.sh [version]
```

#### Arch Linux

```bash
cd packaging/arch
./build.sh [version]
```

## Скрипты сборки

### Общие скрипты (`scripts/`)

- `get_version.sh` - Получить версию из meson.build
- `update_version.sh` - Обновить версию во всех файлах упаковки
- `build_all.sh` - Собрать все типы пакетов

### Использование скриптов

```bash
# Получить текущую версию
./scripts/get_version.sh

# Обновить версию во всех файлах
./scripts/update_version.sh 1.0.0

# Собрать все пакеты
./scripts/build_all.sh

# Собрать определенные пакеты
./scripts/build_all.sh 1.0.0 "flatpak deb"
```

## CI/CD

### GitHub Actions

Проект включает автоматическую сборку пакетов через GitHub Actions:

- **build-packages.yml** - Основной workflow для сборки релизов
- **test-build.yml** - Тестирование сборки на pull requests

### Автоматические релизы

При создании git тега (например, `v1.0.0`) автоматически:
1. Собираются пакеты для всех платформ
2. Создается GitHub релиз с прикрепленными пакетами
3. Обновляется версия во всех файлах

### Ручной запуск

Можно запустить сборку вручную через GitHub Actions интерфейс, указав версию или оставив поле пустым для автоопределения.

## Структура пакетов

### Flatpak
- `org.badkiko.sofl.yml` - Manifest файл
- `build.sh` - Скрипт сборки

### Debian
- `DEBIAN/control` - Метаданные пакета
- `DEBIAN/postinst` - Скрипт пост-установки
- `DEBIAN/prerm` - Скрипт пред-удаления
- `build.sh` - Скрипт сборки

### Arch Linux
- `PKGBUILD` - Скрипт сборки для Arch
- `build.sh` - Скрипт сборки

## Установка пакетов

### Flatpak

```bash
# Локальная установка
flatpak install --user org.badkiko.sofl.flatpak

# Системная установка
sudo flatpak install org.badkiko.sofl.flatpak
```

### Debian/Ubuntu

```bash
sudo dpkg -i sofl_VERSION_all.deb
sudo apt install -f  # Установить зависимости если нужно
```

### Arch Linux

```bash
# Скачать PKGBUILD и исходный код
# Затем выполнить:
makepkg -si
```

## Требования для сборки

### Flatpak
- flatpak-builder
- org.gnome.Platform 47
- org.gnome.Sdk 47

### Debian
- dpkg-dev
- meson
- ninja-build
- python3-gi и другие зависимости

### Arch Linux
- makepkg (доступно на Arch Linux)
- Для других систем создается source tarball

## Устранение проблем

### Flatpak
```bash
# Очистить предыдущие сборки
rm -rf flatpak-build sofl-repo

# Проверить manifest
flatpak-builder --show-manifest org.badkiko.sofl.yml
```

### Debian
```bash
# Проверить зависимости
dpkg-checkbuilddeps

# Проверить пакет после сборки
lintian sofl_VERSION.deb
```

### Arch Linux
```bash
# Проверить PKGBUILD
namcap PKGBUILD

# Тестовая сборка
makepkg -c
```

## Распространение

После сборки пакеты можно распространять:

1. **Flatpak** - загрузить на Flathub
2. **Debian** - загрузить в PPA или репозиторий
3. **Arch Linux** - загрузить в AUR

## Поддержка

При возникновении проблем с упаковкой создавайте issue в репозитории проекта.
