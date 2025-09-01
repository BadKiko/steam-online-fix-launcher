# SOFL Flatpak Packaging

Скрипты и файлы для сборки SOFL как Flatpak пакета.

## Файлы

- `build.sh` - Основной скрипт сборки (стабильная и dev версии)
- `build-dev.sh` - Быстрая сборка и запуск dev версии
- `org.badkiko.sofl.yml` - Manifest для стабильной версии (profile=release)
- `org.badkiko.sofl.Devel.yml` - Manifest для dev версии (profile=development)

## Быстрое использование

### Для разработки

```bash
# Быстрая сборка и запуск dev версии
./build-dev.sh

# С указанной версией
./build-dev.sh 1.0.0-dev
```

### Для стабильной сборки

```bash
# Сборка стабильной версии
./build.sh

# Сборка и установка
./build.sh 1.0.0 . install

# Сборка dev версии
./build.sh dev . dev install
```

## Параметры скриптов

### build.sh

```bash
./build.sh [version] [output_dir] [mode] [dev_flag]

# version    - версия приложения (по умолчанию: unknown)
# output_dir - директория для сохранения bundle (по умолчанию: .)
# mode       - install для установки после сборки
# dev_flag   - dev для сборки dev версии
```

### build-dev.sh

```bash
./build-dev.sh [version] [output_dir] [fast]

# version    - версия приложения (по умолчанию: dev)
# output_dir - директория для сохранения bundle (по умолчанию: .)
# fast       - опциональный параметр для быстрой сборки (пропускает медленные операции)
```

## Примеры

```bash
# Сборка и установка стабильной версии
./build.sh 1.0.0 . install

# Быстрая сборка стабильной версии (без проверок)
./build.sh 1.0.0 . fast install

# Сборка dev версии с установкой
./build.sh dev . dev install

# Быстрая сборка dev версии
./build.sh dev . dev fast install

# Быстрая сборка dev версии через build-dev.sh
./build-dev.sh dev . fast

# Обычная быстрая сборка dev версии
./build-dev.sh

# Сборка dev версии в определенную папку
./build-dev.sh dev ./builds
```

## Автоматический выбор manifest файла

Скрипт `build.sh` автоматически выбирает правильный manifest файл:

- **Стабильная версия**: использует `org.badkiko.sofl.yml`
- **Dev версия**: использует `org.badkiko.sofl.Devel.yml`

## Управление приложением

```bash
# Запуск стабильной версии
flatpak run org.badkiko.sofl

# Запуск dev версии
flatpak run org.badkiko.sofl.Devel

# Просмотр установленных версий
flatpak list | grep sofl

# Удаление версий
flatpak uninstall org.badkiko.sofl
flatpak uninstall org.badkiko.sofl.Devel
```

## Устранение проблем

```bash
# Очистка предыдущих сборок
rm -rf build-dir flatpak-build sofl-repo

# Проверка manifest
flatpak-builder --show-manifest org.badkiko.sofl.yml

# Проверка установленных runtime
flatpak list --runtime

# Логи сборки
flatpak-builder --verbose --force-clean flatpak-build org.badkiko.sofl.yml
```

### Проблема "Command 'sofl' not found"

Если сборка завершается ошибкой "Command 'sofl' not found", это означает, что исполняемый файл не был правильно установлен. Решение:

```bash
# Очистите предыдущую сборку
rm -rf build-dir flatpak-build sofl-repo

# Проверьте, что meson правильно настроен
meson configure build-dir

# Сборка без кэширования
flatpak-builder --force-clean --user --repo=sofl-repo --default-branch=stable --install-deps-from=flathub --disable-rofiles-fuse --ccache flatpak-build org.badkiko.sofl.yml
```

## Режимы сборки

### Стабильная версия

- ID: `org.badkiko.sofl`
- Branch: `stable`
- Для релизов и production использования

### Dev версия

- ID: `org.badkiko.sofl.Devel`
- Branch: `devel`
- Для разработки и тестирования
- Автоматически запускается после сборки

### Fast режим

- Пропускает медленные операции:
  - Установку flatpak и flatpak-builder
  - Настройку Flathub remote
  - Обновление remotes
  - Проверку и установку runtime/SDK
- Идеально для повторных сборок
- Используйте `fast` параметр в любом скрипте

## Требования

- flatpak
- flatpak-builder
- org.gnome.Platform//48
- org.gnome.Sdk//48

Скрипт автоматически установит необходимые компоненты при первом запуске.
