@echo off
rem Runs a local Windows build made with scripts\build-windows.sh (MSYS2 UCRT64)
set MSYS2=C:\msys64
set PREFIX=%MSYS2%\home\%USERNAME%\sofl-install
set PATH=%MSYS2%\ucrt64\bin;%PATH%
set PYTHONUTF8=1
set XDG_DATA_DIRS=%PREFIX%\share;%MSYS2%\ucrt64\share
set GSETTINGS_SCHEMA_DIR=%PREFIX%\share\glib-2.0\schemas
"%MSYS2%\ucrt64\bin\python3.exe" "%PREFIX%\bin\sofl" %*
