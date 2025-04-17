#!/bin/bash
# Полная очистка и пересборка
rm -rf build-dir/ .flatpak-builder/

# Копируем файл metainfo.xml с измененными цветами в директорию 
mkdir -p .flatpak-builder/build/cartridges-1/data/
cp data/org.badkiko.sofl.metainfo.xml.in .flatpak-builder/build/cartridges-1/data/org.badkiko.sofl.Devel.metainfo.xml

# Запускаем сборку
flatpak-builder --run build-dir/ build-aux/flatpak/org.badkiko.sofl.Devel.json cartridges
