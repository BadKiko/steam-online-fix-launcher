# steam-online-fix-launcher
This script allows you to launch 'steam is not running' online-fix games in linux

Go to releases - download zip - unpack zip to game folder - add launcher.exe to steam and write name in arguments 

For example path: "/home/kiko/HddDrive/BGames/drive_c/Games/Kebab Chefs Pioneer/launcher.exe"  "Kebab Chefs! - Restaurant Simulator.exe", working path: /home/kiko/HddDrive/BGames/drive_c/Games/Kebab Chefs Pioneer/, start args: WINEDLLOVERRIDES="OnlineFix64=n;SteamOverlay64=n;winmm=n,b;dnet=n;steam_api64=n" %command%. and set force proton
