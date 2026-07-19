@echo off
setlocal
cd /d "%~dp0"
C:\Python310\python.exe -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --name "ATG_PC_AUDIT_RECOVERY" ^
  --icon "assets\app.ico" ^
  --paths "." ^
  --hidden-import win32crypt ^
  recovery_tool\recovery_main.py
if errorlevel 1 exit /b 1
copy /Y README_KHOI_PHUC.txt dist\README_KHOI_PHUC.txt >nul
echo Da tao dist\ATG_PC_AUDIT_RECOVERY.exe
endlocal
