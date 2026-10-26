@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Bitte zuerst EINRICHTEN.cmd starten.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" videos.py vorschlagen
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Offene Punkte oder Fehler. Bitte Ausgabe und README beachten.
pause
exit /b %RESULT%
