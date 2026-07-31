@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ========================================
echo   Desktop Pet build (PyInstaller)
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] python not found in PATH
  pause
  exit /b 1
)

echo [1/4] Install deps ...
python -m pip install -U pip
python -m pip install -r packaging\requirements.txt
python -m pip install -U pyinstaller
if errorlevel 1 (
  echo [ERROR] pip install failed
  pause
  exit /b 1
)

echo [2/4] Check PyInstaller ...
python -c "import PyInstaller; print(PyInstaller.__version__)"
if errorlevel 1 (
  echo [ERROR] PyInstaller still missing
  pause
  exit /b 1
)

echo [3/4] Building single DesktopPet.exe ...
python packaging\build_app.py
if errorlevel 1 (
  echo [ERROR] build failed
  pause
  exit /b 1
)

echo [4/4] Done
echo.
echo Only one file for friends:
echo   dist\DesktopPet.exe
echo   dist\DesktopPet-v*-windows.zip  ^(zip 内也只有这一个 exe^)
echo.
pause
exit /b 0
