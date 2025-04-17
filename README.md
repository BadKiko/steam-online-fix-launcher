<p align="center">
    <img src="https://raw.githubusercontent.com/BadKiko/steam-online-fix-launcher/refs/heads/main/banner.svg" alt="banner" height="150" />
</p>
<h3 align="center">SOFL </h3>

🎮 Big News! 🎮

I'm excited to announce that I'm merging my two projects - SOFL and Dark Cartridges! This is a huge step forward, and I couldn't be more thrilled about what this means for all users.

🔄 What's Happening? 🔄

I'm combining my SOFL and Dark Cartridges projects into a single, powerful solution for launching online-fix games on Linux. This unified project under the SOFL name will create a seamless experience for everyone.

⚙️ Legacy Instructions ⚙️

Until the merger is complete, you can still use SOFL as follows:
- Download from releases
- Extract to game folder
- Add launcher.exe to Steam with game name in arguments

Example setup:
Path: "/home/kiko/HddDrive/BGames/drive_c/Games/Kebab Chefs Pioneer/launcher.exe" "Kebab Chefs! - Restaurant Simulator.exe"
Working dir: /home/kiko/HddDrive/BGames/drive_c/Games/Kebab Chefs Pioneer/
Launch options: WINEDLLOVERRIDES="OnlineFix64=n;SteamOverlay64=n;winmm=n,b;dnet=n;steam_api64=n" %command%
Don't forget to enable Force Proton!

## Reddit Post

**Updated 25.05.2024**

I know there are already many guides on launching online-fix games with classic SpaceWar, but there are many other fixes that do not follow the standard scenario. In this post, I would like to collect all the known ways of launching online-fix games as well as their organization in the library. You could say this is a gaming mix and my notes, which might be useful for beginners just starting their journey in Linux gaming. I will break the post into several "fix options.".

# Standard Online-Fix  

1.1 **Method with Steam Library:** For standard online-fix games working on SpaceWar, just add the game to Steam and in the launch options, specify `WINEDLLOVERRIDES="OnlineFix64=n;SteamOverlay64=n;winmm=n,b;dnet=n;steam_api64=n;winhttp=n,b" %command%`. This method is suitable for you if you don't mind having non-licensed games in Steam. I also can't fail to mention projects like [steamgrid](https://github.com/boppreh/steamgrid) and [SGDBoop](https://github.com/SteamGridDB/SGDBoop) which find covers for games to make your Steam library look colorful.

1.2 **Method without Steam Library:** What is meant here? In point 1, the Steam library was necessary. In this point, I would like to retell the post [here](https://www.reddit.com/r/LinuxCrackSupport/comments/19f4kse/onlinefix_launching_onlinefixme_games_outside/) but with some updates. This method uses `umu-launcher` (formerly `ulwgl`). I will briefly retell the post with examples for working with `umu-launcher`

1. Download SpaceWar (simply type in the console \`steam steam://install/480\`. If it doesn't work, go to the [https://steamdb.info/app/480/info/](https://steamdb.info/app/480/info/) and click the green "owned" button at the top right).
2. Then SpaceWar - properties - compatibility - select the Proton version.
3. Launch SpaceWar.
4. Copy the SpaceWar prefix folder somewhere. For native Steam, it's \`\~/.local/share/Steam/steamapps/compatdata/480\`, and for flatpak, it's \`\~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/480\`. For example, for me, it will be \`\~/SteamPrefixes/480\`.
5. Next, you need to download \`umu-launcher\`. I use the AUR package https://aur.archlinux.org/packages/umu-launcher. For other distributions different from Arch, they have a flatpak version, nix, and a build from source [https://github.com/Open-Wine-Components/umu-launcher](https://github.com/Open-Wine-Components/umu-launcher)
6. After downloading everything, just launch Steam and execute the command (command paths for me, yours will likely differ, \`protonpath\` is the path to your Proton):`WINEPREFIX='\~/SteamPrefixes/480' WINEDLLOVERRIDES="OnlineFix64=n;SteamOverlay64=n;winmm=n,b;dnet=n;steam\_api64=n" GAMEID=480 PROTONPATH=\~/.local/share/Steam/compatibilitytools.d/GE-Proton9-5 umu-run '\~/pathtogame/game.exe'`
7. Thanks to this bundle, you can create a library for pirated games, for example, with the help of [cartridges](https://github.com/kra-mo/cartridges), a very handy tool. If you're looking to gather all your games in one place, in the program, just create a new game, and in the executable file, insert the command from point 7

# steam_appid.txt fix

Next, I would like to consider exceptions, such as online-fix using Cube Racer with a similar fix like The Binding of Isaac - Repentance by Pioneer. In this fix, Cube Racer is used. Using method 1, I couldn't get it to work; it launched the official version of the game. If you don't own the game, which is logical, it will throw you into the store.

![img](eq7yxe7yki1d1 "Without changing steam_appid.txt")

Such fixes can be recognized by `steam_appid.txt`

Which will contain the ID of the real game. Change it to the one that needs to be emulated, usually specified by repackers, but if not, you can check in `cream_api.ini` if you have a similar repack, and the necessary ID will be indicated there.

All you need is to insert the ID of the emulated game in `steam_appid.txt`, and the game will launch under the necessary ID.

![img](4c8eogpali1d1 "With steam_appid.txt changes")

# Steam is not running fix

My least favorite type of fixes, only completely non-working ones are worse. Here's an example of how this fix looks.

This type of fix checks for the presence of the fix launch in `wineprefix` (as I understand it, it can't be turned off), meaning the game needs to see Steam directly in the prefix. I conducted a whole investigation and eventually made a script allowing such files to be launched. By default, files named `steam.exe` cannot be launched from `umu-launcher` or Steam to make the game see a fake Steam, but with the script, it is possible. So all you need is to download online-fix-launcher from the releases [here](https://github.com/BadKiko/steam-online-fix-launcher/releases/tag/0.0.1) and unpack it into the game folder, then use the launch methods from point 1, but also add the game name in the arguments after `launcher.exe` file, for example:"/home/kiko/HddDrive/BGames/drive\_c/Games/Kebab Chefs Pioneer/launcher.exe" "Kebab Chefs! - Restaurant Simulator.exe"

# Failed read Steam Enviroment

To fix this error, you just need to take another SteamFix64.dll from another game (for your convenience, I uploaded the dll file here https://github.com/BadKiko/steam-online-fix-launcher/releases) and replace it. I don't know exactly why this error occurs, I encountered such an error in The Jump Guys, and to fix it, I just took SteamFix64.dll from Lethal Company and inserted it into The Jump Guys/TheJumpGuys\_Data/Plugins/x86\_64 and that's it.

# Failed to load steam overlay dll

To fix this error, you must run the game through Steam. When using umu-launcher, I encountered this error in My Summer Car, but it was the only game that didn't work with umu-launcher. If you have any ideas or ways to fix this error so that the game works with umu-launcher, please write in the comments.

**If a fix does not work natively even after all I have told you, you can install Steam in the prefix in Bottles, for example, but personally, I don't like this method as Steam through Wine doesn't run very well.**

If I missed something, write in the comments, and I'll try to answer if I know the answer.

Tags: failed read steam environment version 1 mid 3, linux online-fix, steam is not running fix linux, steam is not running online fix linux, cube racer online-fix linux, failed to load steam overlay dll, error code: 126
