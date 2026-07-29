@echo off
setlocal EnableExtensions
cd /d "%~dp0"

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
python -m pip install -r requirements.txt
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

echo [3/4] Building ...
python build_app.py
if errorlevel 1 (
  echo [ERROR] build failed
  pause
  exit /b 1
)

echo [4/4] Done
echo.
echo Output: dist\DesktopPet\DesktopPet.exe
echo Share the whole dist\DesktopPet folder.
echo User data: data_store next to the exe.
echo.
pause
exit /b 0
