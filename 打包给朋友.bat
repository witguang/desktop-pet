@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   打包桌宠 → 只要一个 DesktopPet.exe
echo ========================================
echo.
if exist "%~dp0VERSION" (
  set /p VER=<"%~dp0VERSION"
  echo 当前 VERSION: %VER%
)
echo 输出: dist\DesktopPet.exe
echo       dist\DesktopPet-v*-windows.zip  ^(内仅一个 exe^)
echo.

call "%~dp0packaging\build_app.bat"
exit /b %errorlevel%
