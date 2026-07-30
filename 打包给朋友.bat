@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   打包桌宠 → 生成可发给朋友的 zip
echo ========================================
echo.

call "%~dp0packaging\build_app.bat"
exit /b %errorlevel%
