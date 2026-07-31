@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] python not found
  echo Download zip from GitHub Releases (no Python needed):
  echo   https://github.com/witguang/desktop-pet/releases
  pause
  exit /b 1
)

python -c "import PIL" 2>nul
if errorlevel 1 (
  echo [1/2] Install deps ...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip failed
    pause
    exit /b 1
  )
)

echo Starting Desktop Pet ...
python packaging\entry_main.py %*
if errorlevel 1 (
  echo Exit code %errorlevel%
  pause
)
exit /b %errorlevel%
