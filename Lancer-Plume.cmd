@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Installez Python 3.12 depuis https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -c "import PySide6, docx" >nul 2>&1
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Installation des dependances impossible. Verifiez votre connexion.
  pause
  exit /b 1
)
.venv\Scripts\python.exe main.py
if errorlevel 1 pause
