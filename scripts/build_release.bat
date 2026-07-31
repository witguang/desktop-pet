@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
echo Build DesktopPet.exe ...
if exist VERSION (
  set /p VER=<VERSION
  echo VERSION: %VER%
)
call packaging\build_app.bat
exit /b %errorlevel%
