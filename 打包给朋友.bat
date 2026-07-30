@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo   打包桌宠 → 生成可发给朋友的 zip
echo ========================================
echo.

call "%~dp0build_app.bat"
if errorlevel 1 exit /b 1

echo.
echo ----------------------------------------
echo  输出位置：
echo    dist\DesktopPet\          （整文件夹也可拷贝）
echo    dist\DesktopPet-v*-windows.zip
echo.
echo  发给朋友：把 zip 传过去，让对方解压后
echo  运行 DesktopPetSetup.exe 即可。
echo.
echo  发布到 GitHub（需已登录 gh）：
echo    gh release create vX.Y.Z dist\DesktopPet-vX.Y.Z-windows.zip --title "vX.Y.Z" --notes "Windows 桌宠安装包"
echo ----------------------------------------
pause
exit /b 0
