@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe -c "import snapchat as s; print(s.tool('exiftool')); print(s.tool('ffmpeg')); print(s.tool('ffprobe'))"
if errorlevel 1 goto error
echo Einrichtung abgeschlossen. Jetzt 01_PRUEFEN.cmd starten.
pause
exit /b 0
:error
echo Einrichtung fehlgeschlagen. Bitte die Installationsschritte in README.md lesen.
pause
exit /b 1
