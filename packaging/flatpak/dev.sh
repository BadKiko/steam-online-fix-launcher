./build.sh 0.0.3.2a ../../dist fast
flatpak remove org.badkiko.sofl -y
flatpak install ../../dist/org.badkiko.sofl.flatpak --user -y
flatpak run org.badkiko.sofl 