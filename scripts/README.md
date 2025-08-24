# SOFL - Build Scripts

Набор скриптов для автоматизации сборки SOFL пакетов.

## Доступные скрипты

### `get_version.sh`
Получает текущую версию из файла `meson.build`.

```bash
./scripts/get_version.sh
# Вывод: 0.0.3
```

### `update_version.sh`
Обновляет версию во всех файлах упаковки.

```bash
# Обновить до указанной версии
./scripts/update_version.sh 1.0.0

# Обновить до версии из meson.build
./scripts/update_version.sh
```

Обновляет файлы:
- `meson.build`
- `packaging/flatpak/org.badkiko.sofl.yml`
- `packaging/debian/DEBIAN/control`
- `packaging/arch/PKGBUILD`
- `data/org.badkiko.sofl.metainfo.xml.in`

### `build_all.sh`
Собирает пакеты для всех платформ.

```bash
# Сборка всех пакетов с версией из meson.build
./scripts/build_all.sh

# Сборка с указанной версией
./scripts/build_all.sh 1.0.0

# Сборка только определенных пакетов
./scripts/build_all.sh 1.0.0 "flatpak deb"
```

Поддерживаемые типы пакетов:
- `flatpak` - Flatpak пакет
- `deb` - Debian пакет
- `arch` - Arch Linux пакет

## Примеры использования

### Полная сборка нового релиза

```bash
# 1. Обновить версию
./scripts/update_version.sh 1.0.0

# 2. Собрать все пакеты
./scripts/build_all.sh

# 3. Создать git тег
git add .
git commit -m "Release v1.0.0"
git tag v1.0.0

# 4. Отправить изменения (запустит GitHub Actions)
git push origin main --tags
```

### Быстрая сборка для тестирования

```bash
# Собрать только Flatpak для тестирования
./scripts/build_all.sh $(./scripts/get_version.sh) "flatpak"
```

## Автоматизация

Скрипты автоматически:
- Определяют версию из `meson.build`
- Обновляют все файлы упаковки
- Собирают пакеты с правильными зависимостями
- Проверяют наличие необходимых инструментов

## Интеграция с GitHub Actions

Скрипты используются в GitHub Actions workflows:

- `.github/workflows/build-packages.yml` - Релизы
- `.github/workflows/test-build.yml` - Тестирование

При создании git тега автоматически запускается сборка всех пакетов и создание релиза.
