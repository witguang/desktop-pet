@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
echo Build DesktopPet.exe ...
if exist packaging\VERSION (
  set /p VER=<packaging\VERSION
  echo VERSION: %VER%
)
call packaging\build_app.bat
exit /b %errorlevel%
