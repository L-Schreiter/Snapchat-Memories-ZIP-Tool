# Einmalige Einrichtung unter Windows

[← Zur Startseite](../README.md)

Du richtest das Tool einmal ein. Danach verwendest du die nummerierten `.cmd`-Dateien per Doppelklick.

## 1. Tool herunterladen

[Gesamtpaket herunterladen](https://github.com/L-Schreiter/Snapchat-Memories-ZIP-Tool/archive/refs/heads/main.zip) und mit **Rechtsklick → Alle extrahieren** entpacken.

Öffne den entpackten Ordner, in dem `EINRICHTEN.cmd` liegt. Alle folgenden Dateien kommen in diesen Ordner bzw. seinen Unterordner `tools`.

## 2. Python installieren

Lade [Python für Windows](https://www.python.org/downloads/windows/) herunter und installiere **Version 3.11 oder neuer** mit dem **`py`-Launcher**. Falls angeboten, aktiviere „Add Python to PATH“.

## 3. ExifTool hinzufügen

ExifTool schreibt Datum und Standort in die Dateien.

1. Lade das Windows-Paket von [exiftool.org](https://exiftool.org/) herunter und entpacke es.
2. Erstelle im Tool-Ordner einen Unterordner namens **`tools`**.
3. Kopiere **`exiftool(-k).exe`** und den gesamten zugehörigen Ordner **`exiftool_files`** nach `tools`.
4. Benenne `exiftool(-k).exe` in **`exiftool.exe`** um.

Der Ordner `exiftool_files` muss direkt neben der EXE bleiben. Falls Windows Dateiendungen ausblendet, blende sie vor dem Umbenennen ein, damit nicht versehentlich `exiftool.exe.exe` entsteht.

## 4. FFmpeg hinzufügen

FFmpeg verarbeitet die Videos; FFprobe liest deren Eigenschaften.

1. Öffne die [FFmpeg-Downloadseite](https://ffmpeg.org/download.html) und wähle einen verlinkten **Windows-Build** mit `libx264`.
2. Entpacke das heruntergeladene Paket.
3. Kopiere aus dessen Ordner **`bin`** die Dateien **`ffmpeg.exe`** und **`ffprobe.exe`** ebenfalls nach `tools`.

Zur Kontrolle:

| Datei oder Ordner | Liegt im Tool unter … |
| --- | --- |
| ExifTool | `tools\exiftool.exe` |
| ExifTool-Zusatzdateien | `tools\exiftool_files\…` |
| FFmpeg | `tools\ffmpeg.exe` |
| FFprobe | `tools\ffprobe.exe` |

Bereits global installierte Programme können ebenfalls verwendet werden; dann müssen sie über den Windows-`PATH` erreichbar sein.

## 5. Einrichtung starten

Doppelklicke **`EINRICHTEN.cmd`** und warte auf **„Einrichtung abgeschlossen“**.

Dabei wird eine eigene Python-Umgebung angelegt und die Bildbibliothek Pillow heruntergeladen. Dafür ist Internet nötig. Python, ExifTool und FFmpeg müssen bereits vorhanden sein.

**Fertig → [weiter mit „Snapchat-ZIPs hineinlegen“](../README.md#2-snapchat-zips-hineinlegen).**

### Wenn die Einrichtung abbricht

- **`py` nicht gefunden:** Python einschließlich Launcher installieren. Danach ein neues Terminalfenster öffnen bzw. den Starter erneut ausführen.
- **ExifTool/FFmpeg/FFprobe nicht gefunden:** Die oben genannten Namen und Speicherorte kontrollieren. Die EXE-Dateien müssen wirklich entpackt sein.
- **Pillow konnte nicht installiert werden:** Internetverbindung prüfen und `EINRICHTEN.cmd` erneut starten. Die genaue Fehlermeldung beachten.

[Manuelle Befehle, eigene Datenpfade und macOS/Linux](ANLEITUNG.md).
