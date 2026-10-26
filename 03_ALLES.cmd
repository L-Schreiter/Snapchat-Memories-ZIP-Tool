@echo off
cd /d "%~dp0"
echo Zuerst Testdateien in Fotos pruefen: Datum, Uhrzeit, Ort, Overlays.
choice /C JN /N /M "Stimmen die Testimporte mit Snapchat ueberein? [J/N] "
if errorlevel 2 exit /b 1
if not exist ".venv\Scripts\python.exe" (
 echo Bitte zuerst EINRICHTEN.cmd starten.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" tool.py alles --zip-times-utc-confirmed
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo Offene Punkte oder Fehler. Bitte Ausgabe und README beachten.
pause
exit /b %RESULT%
