@echo off
setlocal
cd /d "%~dp0"
C:\Python310\python.exe -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --uac-admin ^
  --name "ATG_PC_AUDIT" ^
  --icon "assets\app.ico" ^
  --version-file "assets\version_info.txt" ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --hidden-import win32com.client ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --hidden-import win32crypt ^
  --hidden-import sqlite3 ^
  --collect-all openpyxl ^
  main.py
if errorlevel 1 exit /b 1
echo Da tao dist\ATG_PC_AUDIT.exe
endlocal
