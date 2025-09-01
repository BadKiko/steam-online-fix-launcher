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

# Обычная сборка стабильной версии
./build.sh [version]

# Быстрая сборка стабильной версии (без проверок)
./build.sh [version] . fast

# Сборка и установка стабильной версии
./build.sh [version] . install

# Быстрая сборка и установка стабильной версии
./build.sh [version] . fast install

# Сборка и установка dev версии
./build.sh [version] . dev install

# Быстрая сборка и установка dev версии
./build.sh [version] . dev fast install

# Быстрая сборка и запуск dev версии
./build-dev.sh [version]

# Максимально быстрая сборка и запуск dev версии
./build-dev.sh [version] . fast
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

- `org.badkiko.sofl.yml` - Manifest файл для стабильной версии
- `org.badkiko.sofl.Devel.yml` - Manifest файл для dev версии
- `build.sh` - Скрипт сборки (поддерживает dev и fast режимы)
- `build-dev.sh` - Скрипт быстрой сборки dev версии (с поддержкой fast режима)

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
# Локальная установка стабильной версии
flatpak install --user org.badkiko.sofl.flatpak

# Локальная установка dev версии
flatpak install --user org.badkiko.sofl.Devel.flatpak

# Системная установка
sudo flatpak install org.badkiko.sofl.flatpak

# Запуск стабильной версии
flatpak run org.badkiko.sofl

# Запуск dev версии
flatpak run org.badkiko.sofl.Devel
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

## Разработка

### Режимы сборки Flatpak

Проект поддерживает два режима сборки Flatpak:

#### Стабильная версия (`org.badkiko.sofl`)

- Используется для релизов и production
- Branch: `stable` (по умолчанию)

#### Dev версия (`org.badkiko.sofl.Devel`)

- Используется для разработки и тестирования
- Branch: `devel`
- Автоматически запускается после сборки

### Быстрая разработка

Для быстрой разработки используйте `build-dev.sh`:

```bash
cd packaging/flatpak

# Быстрая сборка и запуск dev версии
./build-dev.sh

# Сборка с указанной версией
./build-dev.sh 1.0.0-dev
```

### Ручная сборка dev версии

```bash
cd packaging/flatpak

# Сборка dev версии через основной скрипт
./build.sh dev . dev install
```

### Особенности dev режима

- **Автоматический запуск**: После сборки приложение запускается автоматически
- **Отдельный профиль**: Dev версия не конфликтует со стабильной
- **Разные настройки**: Можно тестировать новые функции без влияния на стабильную версию

### Fast режим для быстрой разработки

Для максимальной скорости сборки используйте fast режим, который пропускает:

- Установку flatpak и flatpak-builder
- Настройку Flathub remote
- Обновление remotes (сетевые операции)
- Проверку и установку runtime/SDK

```bash
# Быстрая сборка dev версии
./build-dev.sh dev . fast

# Быстрая сборка стабильной версии
./build.sh 1.0.0 . fast install
```

## Поддержка

При возникновении проблем с упаковкой создавайте issue в репозитории проекта.
