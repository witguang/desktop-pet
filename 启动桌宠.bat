@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 Python。
  echo.
  echo 普通用户请从 GitHub Releases 下载 exe 版，无需 Python：
  echo   https://github.com/witguang/desktop-pet/releases
  echo.
  pause
  exit /b 1
)

python -c "import PIL" 2>nul
if errorlevel 1 (
  echo [1/2] 安装依赖 ...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
  )
)

echo 启动桌宠 ...
python main.py %*
if errorlevel 1 (
  echo.
  echo 程序异常退出，代码 %errorlevel%
  pause
)
exit /b %errorlevel%
