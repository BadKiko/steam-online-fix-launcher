# SOFL - Сборка пакетов

Этот документ описывает процесс сборки SOFL для различных Linux дистрибутивов.

## 🚀 Быстрый старт

### Сборка всех пакетов сразу

```bash
# Сборка всех типов пакетов с версией из meson.build
./scripts/build_all.sh

# Сборка с указанной версией
./scripts/build_all.sh 1.0.0

# Сборка только определенных пакетов
./scripts/build_all.sh 1.0.0 "flatpak deb"
```

### Релиз нового версии

```bash
# 1. Обновить версию во всех файлах
./scripts/update_version.sh 1.0.0

# 2. Собрать все пакеты
./scripts/build_all.sh

# 3. Создать git тег (запустит автоматическую сборку на GitHub)
git add .
git commit -m "Release v1.0.0"
git tag v1.0.0
git push origin main --tags
```

## 📦 Поддерживаемые форматы

### Flatpak
Универсальный формат для всех Linux дистрибутивов.

```bash
cd packaging/flatpak
./build.sh [version]
```

**Требования:**
- flatpak-builder
- org.gnome.Platform 47
- org.gnome.Sdk 47

### Debian (.deb)
Для Debian, Ubuntu и производных.

```bash
cd packaging/debian
./build.sh [version]
```

**Требования:**
- dpkg-dev
- meson, ninja-build
- python3-gi, python3-gi-cairo
- gir1.2-gtk-4.0, gir1.2-adw-1

### Arch Linux
PKGBUILD для сборки в Arch Linux.

```bash
cd packaging/arch
./build.sh [version]
```

**Требования:**
- makepkg (Arch Linux)
- Или создается source tarball для ручной сборки

## 🛠️ Доступные скрипты

### `scripts/get_version.sh`
Получить текущую версию из meson.build.

```bash
./scripts/get_version.sh
# Вывод: 0.0.3
```

### `scripts/update_version.sh`
Обновить версию во всех файлах упаковки.

```bash
./scripts/update_version.sh 1.0.0
```

### `scripts/build_all.sh`
Собрать пакеты для всех платформ.

```bash
./scripts/build_all.sh [version] [package_types]
```

## ⚡ GitHub Actions

Проект включает автоматическую сборку через GitHub Actions:

### Автоматические релизы
При создании git тега (например, `v1.0.0`) автоматически:
1. Собираются пакеты для всех платформ
2. Создается GitHub релиз с прикрепленными пакетами
3. Обновляется версия во всех файлах

### Тестирование
На pull requests автоматически тестируется сборка всех пакетов.

### Ручной запуск
Через интерфейс GitHub Actions можно запустить сборку вручную, указав версию.

## 📋 Установка созданных пакетов

### Flatpak
```bash
flatpak install --user org.badkiko.sofl.flatpak
```

### Debian/Ubuntu
```bash
sudo dpkg -i sofl_1.0.0_all.deb
sudo apt install -f
```

### Arch Linux
```bash
# Скачать PKGBUILD и tarball, затем:
makepkg -si
```

## 📁 Структура проекта

```
├── scripts/                    # Общие скрипты сборки
│   ├── get_version.sh         # Получить версию
│   ├── update_version.sh      # Обновить версию
│   ├── build_all.sh           # Собрать все пакеты
│   └── README.md              # Документация скриптов
├── packaging/                 # Файлы для упаковки
│   ├── flatpak/               # Flatpak пакет
│   ├── debian/                # Debian пакет
│   ├── arch/                  # Arch Linux пакет
│   └── README.md              # Документация упаковки
├── .github/workflows/         # GitHub Actions
│   ├── build-packages.yml     # Сборка релизов
│   └── test-build.yml         # Тестирование
└── .gitignore                 # Исключения git
```

## 🔧 Устранение проблем

### Flatpak
```bash
# Очистить предыдущие сборки
rm -rf packaging/flatpak/flatpak-build packaging/flatpak/sofl-repo

# Проверить зависимости
flatpak install org.gnome.Platform//47 org.gnome.Sdk//47
```

### Debian
```bash
# Проверить зависимости пакета
dpkg-checkbuilddeps

# Установить недостающие зависимости
sudo apt install meson ninja-build python3-gi python3-gi-cairo
```

### Arch Linux
```bash
# Проверить PKGBUILD
namcap PKGBUILD

# Тестовая сборка
makepkg -c
```

## 📄 Документация

- [packaging/README.md](packaging/README.md) - Подробная документация по упаковке
- [scripts/README.md](scripts/README.md) - Документация скриптов сборки
- [GitHub Actions](.github/workflows/) - Файлы автоматизации

## 🎯 Следующие шаги

1. **Тестирование** - Протестируйте сборку на вашей системе
2. **GitHub Actions** - Настройте secrets если нужно
3. **Flathub** - Рассмотрите публикацию Flatpak на Flathub
4. **PPA** - Рассмотрите создание PPA для Debian пакетов
5. **AUR** - Опубликуйте PKGBUILD в AUR

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи GitHub Actions
2. Создайте issue в репозитории
3. Проверьте требования к зависимостям

---

**Примечание:** Все скрипты автоматически определяют версию из `meson.build` и обновляют все файлы упаковки согласованно.
