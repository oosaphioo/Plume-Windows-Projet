@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.22.0
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name Plume --collect-data docx main.py
if errorlevel 1 goto fail
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer.iss
  if errorlevel 1 goto fail
  echo Installateur dans le dossier output.
) else (
  echo Version portable dans dist\Plume. Gardez tout le dossier ensemble.
  echo Installez Inno Setup 6 pour generer aussi un installateur.
)
pause
exit /b 0
:fail
echo La construction a echoue. Copiez le message d'erreur pour obtenir de l'aide.
pause
exit /b 1
