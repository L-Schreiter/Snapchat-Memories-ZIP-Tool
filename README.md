# Snapchat Memories ZIP Tool

**Fotos und Videos aus Snapchat-ZIP-Exporten aufbereiten – mit Aufnahmedatum, verfügbaren GPS-Koordinaten und separater Overlay-Version.**

Deutsche Anleitung · Windows-Starter · lokale Verarbeitung · öffentliche Beta 0.1.0

Dieses Werkzeug ist für Exporte gedacht, in denen die Bilder und Videos **bereits als echte Dateien in den ZIPs liegen**. Es benötigt keine Download-Links in der JSON. Es meldet unklare Zuordnungen und verändert die Original-ZIPs nicht.

> **Mit KI entwickelt:** Dieses Projekt wurde von Leon in Zusammenarbeit mit ChatGPT (OpenAI) erstellt. Code, Dokumentation und Tests entstanden mit KI-Unterstützung. Die ursprüngliche, individuell angepasste Verarbeitung wurde mit einem realen Snapchat-Export erprobt. Diese öffentliche Version wurde daraus verallgemeinert und mit künstlichen Testdaten geprüft. Das ist keine Garantie für jede Exportvariante. Kein offizielles Produkt von Snapchat, Apple oder OpenAI.

## Was das Werkzeug macht

- Liest beliebig viele `mydata*.zip` direkt. Kein manuelles Zusammenwerfen von `html`-, `json`- oder `memories`-Ordnern.
- Ordnet Metadaten anhand von ZIP-Zeitstempel, Medientyp und Datum im Dateinamen zu.
- Schreibt Datum und verfügbare Koordinaten in Kopien der Bilder/Videos und liest die geschriebenen Werte zur Kontrolle zurück.
- Speichert eine Original-Version und, wenn ein sichtbares unterstütztes Overlay existiert, eine zusätzliche Version mit Overlay.
- Sortiert nach Jahren; keine tausenden Einzelordner.
- Schlägt zusammengehörige Videoclips vor. **Erst nach Sichtprüfung und Freigabe** werden sie verbunden.
- Verwendet bei verbundenen Videos die Overlay-Version **jedes einzelnen Clips**, sofern vorhanden.
- Erstellt einen separaten Importordner mit langen Videos statt der zugehörigen Einzelclips. Die Einzelclips bleiben im Arbeitsbestand erhalten.
- Prüft Ergebnisse mit SHA-256 und unterstützt die Wiederaufnahme unveränderter Ergebnisse.

## Passt mein Export?

Typische Einträge innerhalb der ZIP-Dateien:

```text
json/memories_history.json
memories/YYYY-MM-DD_UUID-main.jpg
memories/YYYY-MM-DD_UUID-main.mp4
memories/YYYY-MM-DD_UUID-overlay.png
```

Die JSON enthält `Saved Media` mit `Date`, `Media Type` und optional `Location`. Ein leeres `Download Link` ist in Ordnung. Die Daten müssen in den Original-ZIPs liegen; eine separat abgelegte JSON wird nicht eingelesen.

Unterstützte Dateiendungen im Namensschema: JPG/JPEG, PNG, WEBP, MP4 und MOV. Andere Dateinamen/-formate können unberücksichtigt bleiben; der Prüfbericht muss gelesen werden. Chat-Medien sind nicht Teil dieses Werkzeugs.

**Nicht geeignet:** Exporte, die nur HTML/JSON mit Download-Links enthalten. Die Medien müssen zunächst vollständig heruntergeladen werden. Snapchat kann Exportformate ändern.

### Die wichtige Einschränkung bei den Metadaten

Fehlt eine direkte Medien-ID in der JSON, ist die Zuordnung über Zeitstempel **eine Heuristik**. Ein ZIP-Zeitstempel hat normalerweise zwei Sekunden Auflösung und enthält keine Zeitzone. Dieses Werkzeug setzt voraus, dass er zur UTC-Zeit in der JSON passt. `EINDEUTIG` bedeutet nur, dass unter dieser Annahme genau ein unterschiedliches Datum/GPS-Paar passt – nicht, dass die Identität bewiesen ist.

Darum zuerst den Testlauf machen und mehrere alte/neue Aufnahmen in Snapchat und nach einem Testimport in Fotos vergleichen. Das Werkzeug korrigiert abweichende ZIP-Zeitzonen nicht automatisch.

## Schritt 1 – Werkzeug herunterladen

Auf dieser GitHub-Seite **Code → Download ZIP** wählen. Das ZIP vollständig entpacken, zum Beispiel nach:

```text
C:\Snapchat-Memories-ZIP-Tool
```

Die Programme nicht direkt aus der ZIP-Vorschau starten. Alternativ mit installiertem Git:

```cmd
git clone https://github.com/L-Schreiter/Snapchat-Memories-ZIP-Tool.git
cd Snapchat-Memories-ZIP-Tool
```

## Schritt 2 – Snapchat-Daten ablegen

Alle zusammengehörigen Original-Export-ZIPs in den mitgelieferten Ordner `daten` kopieren. Die ZIPs **nicht vorher neu packen**, da ihre ursprünglichen Zeitstempel gebraucht werden.

Beispiel:

```text
daten/mydata-export.zip
daten/mydata-export-2.zip
daten/mydata-export-3.zip
```

Alle Teile desselben Exports verwenden. Nicht verschiedene Exportanforderungen vermischen. Wiederholte identische JSON-Listen werden akzeptiert; unterschiedliche Listen führen zum Abbruch. Die Anzahl muss nicht 13 sein.

ZIPs und Ergebnisse benötigen Platz. Original-Versionen, Overlay-Versionen, verbundene Videos, Testdateien und der abschließende Importordner können zusammen deutlich mehr Speicher als die ZIPs belegen.

## Schritt 3 – Programme installieren (Windows)

Benötigt werden:

1. **Python 3.11 oder neuer**, einschließlich `py`-Launcher: [python.org](https://www.python.org/downloads/windows/).
2. **ExifTool**: [exiftool.org](https://exiftool.org/). Beim portablen Windows-Paket `exiftool(-k).exe` in `exiftool.exe` umbenennen. Den zugehörigen Ordner `exiftool_files` mit allen Dateien daneben behalten.
3. **FFmpeg und FFprobe**: [offizielle Downloadseite](https://ffmpeg.org/download.html). Einen Windows-Build mit `libx264` verwenden.

ExifTool, FFmpeg und FFprobe müssen entweder im `PATH` liegen oder im Unterordner `tools` dieses Projekts. Für eine portable Installation:

```text
tools/exiftool.exe
tools/exiftool_files/...
tools/ffmpeg.exe
tools/ffprobe.exe
```

Anschließend `EINRICHTEN.cmd` doppelklicken. Das erstellt eine eigene Python-Umgebung und installiert Pillow. Es installiert nicht automatisch Python, ExifTool oder FFmpeg.

Falls du die Einrichtung lieber selbst ausführst: **Eingabeaufforderung (CMD)** im Projektordner öffnen und eingeben:

```cmd
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -c "import snapchat as s; print(s.tool('exiftool')); print(s.tool('ffmpeg')); print(s.tool('ffprobe'))"
```

Die folgenden Befehle sind ebenfalls für **CMD**. In PowerShell lokale Programme mit `& .\.venv\Scripts\python.exe ...` starten. Am einfachsten sind die mitgelieferten `.cmd`-Starter.

## Schritt 4 – Export prüfen

`01_PRUEFEN.cmd` starten oder:

```cmd
.venv\Scripts\python.exe tool.py pruefen
```

Ergebnisse stehen in `daten\_Berichte\Zuordnung.csv` und `Zusammenfassung.json`. Dieser Schritt braucht noch kein ExifTool und FFmpeg.

| Status | Bedeutung |
| --- | --- |
| `EINDEUTIG` | Ein Datum/GPS-Paar passt zur Zeitstempel-Heuristik. |
| `MEHRDEUTIG` | Mehrere Paare passen. Standardmäßig keine Verarbeitung. |
| `KEIN_TREFFER` | Kein passender JSON-Eintrag. Test-/Gesamtlauf wird abgebrochen. |
| `DATUM_WIDERSPRUCH` | Dateiname und Kandidatendatum passen nicht. Keine automatische Korrektur. |
| `DOPPELTE_DATEI_ID` | Mehrere Hauptdateien oder Overlays mit gleichem Datum und gleicher ID. Manuell prüfen. |

Gleiche UUIDs an **unterschiedlichen Tagen** werden getrennt behandelt. Es gibt keine automatische inhaltliche Dublettenlöschung.

Optional die erwartete Anzahl der ZIPs prüfen:

```cmd
.venv\Scripts\python.exe tool.py pruefen --expected-zips 13
```

Die `13` durch die eigene Anzahl ersetzen. Fehlende ZIPs können ohne diese Angabe nicht zuverlässig erkannt werden.

## Schritt 5 – Kleine Auswahl testen

`02_TEST.cmd` starten oder:

```cmd
.venv\Scripts\python.exe tool.py test
```

Die Auswahl enthält nach Möglichkeit alte und neue Fotos/Videos mit und ohne Overlay. Ergebnisse stehen in `daten\_Test\JAHR`.

Prüfe:

- Aufnahmedatum und Uhrzeit im Vergleich zur Snapchat-App.
- Standort, soweit er tatsächlich in Snapchat/JSON vorhanden ist.
- Bildausrichtung und Position der Overlays.
- Ton und Ausrichtung der Videos.
- Einige Testdateien nach dem Import in die verwendete Foto-App.

Die Dateinamen enthalten ausdrücklich **UTC**. Die Anzeige einer Foto-App kann die Zeit in eine lokale Zeitzone umrechnen. Nicht pauschal eine oder zwei Stunden addieren. Das Werkzeug schreibt UTC und zugehörige Offset-Felder; es rekonstruiert keine fehlenden Zeitzonen anhand vermuteter Reiseorte.

## Schritt 6 – Alle eindeutig zugeordneten Aufnahmen verarbeiten

`03_ALLES.cmd` starten und die vorherige Prüfung bestätigen. Oder nach erfolgreichem Test:

```cmd
.venv\Scripts\python.exe tool.py alles --zip-times-utc-confirmed
```

Ergebnisse liegen in `daten\_Ergebnis\JAHR`.

- `..._Original.jpg/mp4/...`: Kopie mit geschriebenen Metadaten. Der Foto-/Videoinhalt wird für diese Einzeldateien nicht neu encodiert; die Datei ist wegen der Metadaten nicht byteidentisch mit der ZIP-Quelle.
- `..._Mit_Overlay.jpg/mp4`: separate gerenderte Version. Fotos werden als JPEG gespeichert; Videos werden neu encodiert.
- Vollständig transparente Overlays erzeugen keine unnötige zweite Datei.
- Unlesbare oder geometrisch unpassende Overlays führen zu einem protokollierten Fehler; das Original bleibt trotzdem erhalten.

Pro Arbeitsordner immer nur einen Lauf gleichzeitig starten. Bei einem Abbruch denselben Befehl erneut ausführen. Vorhandene, unveränderte Ergebnisse werden über ihre Protokolle geprüft und wiederverwendet. Ergebnisse oder Protokolle nicht manuell überschreiben. Bei einer geänderten Auswahlregel oder reparierten Quelldaten einen **neuen Arbeitsordner** verwenden.

### Optional: Mehrdeutige Metadaten nach einer festen Regel auswählen

Nur verwenden, wenn du die Kandidaten in `Zuordnung.csv` geprüft hast und eine Näherung akzeptierst:

```cmd
.venv\Scripts\python.exe tool.py alles --zip-times-utc-confirmed --ambiguity gps-earliest
```

Die Regel bevorzugt Kandidaten mit GPS und danach das früheste vorhandene Datum/GPS-Paar. Bei Gleichstand entscheidet eine feste Koordinaten-Sortierung. Datum und GPS werden immer aus demselben Kandidaten genommen, niemals gemittelt. **Das kann den falschen Standort wählen**, wenn mehrere Aufnahmen im gleichen Zwei-Sekunden-Fenster liegen. Es ist keine automatische Reparatur und ersetzt keine Sichtprüfung. Die Auswahl wird in `Metadaten_Entscheidungen.json` und den Einzelprotokollen festgehalten.

## Schritt 7 – Geteilte Videos prüfen und verbinden (optional)

Zuerst `04_VIDEOS_VORSCHLAGEN.cmd` oder:

```cmd
.venv\Scripts\python.exe videos.py vorschlagen
```

Das erzeugt `daten\_Berichte\Videos_Vorschlaege.json`. Bestehende Listen werden nicht überschrieben.

Die Vorschläge sind bewusst eng gefasst: gleicher ursprünglicher interner Videozeitstempel, erster ZIP-Zeitstempel nahe daran, 2–6 unterschiedliche Clips, ungefähr zehn Sekunden lange vorherige Clips und passende Zeitabstände. Das wird über **alle Jahre** geprüft. Fehlende/unpassende Zeitstempel, längere Serien und ungeklärte Overlays können dazu führen, dass eine echte Serie nicht vorgeschlagen wird. Nicht vorgeschlagene Videos bleiben einzeln erhalten.

1. Die in einer Serie unter `clips` genannten Videos aus `daten\_Ergebnis` ansehen.
2. Inhalt, Reihenfolge, Ton und Übergänge prüfen.
3. In der JSON ausschließlich bei bestätigten Serien `"approved": false` in `"approved": true` ändern.
4. Datei speichern; dann `05_VIDEOS_VERBINDEN.cmd` starten oder:

```cmd
.venv\Scripts\python.exe videos.py verbinden
```

Ergebnisse stehen in `daten\_Verbunden\JAHR`. Wiederum stichprobenartig **alle Übergänge der freigegebenen Serien** ansehen. Metadaten der fertigen Serie stammen vom ersten Clip. Eine GPS-Route wird nicht gespeichert; die Einzelclip-Protokolle behalten ihre jeweiligen Daten.

Beim Verbinden werden Videos auf die Abmessungen des ersten Clips, 30 Bilder/s und H.264 vereinheitlicht; Ton wird zu AAC/Stereo/48 kHz umgewandelt. Das ist nicht verlustfrei. Fehlender Ton einzelner Clips wird durch Stille ergänzt. Die Laufzeit wird kontrolliert.

Wenn eine bereits verbundene Serie doch falsch ist: nicht einfach `approved` zurücksetzen. Die fertigen Serienprotokolle werden beim Import weiterhin berücksichtigt. Einen neuen Arbeitsordner aufbauen oder die betreffende Ausgabe samt Protokoll gezielt außerhalb des Arbeitsordners sichern, bevor der Importordner erstellt wird. Ein fertiger Importordner aktualisiert sich nicht automatisch.

## Schritt 8 – Endkontrolle und Importordner

`06_ENDKONTROLLE.cmd` oder:

```cmd
.venv\Scripts\python.exe tool.py kontrolle
```

Prüft ZIP-Eintragseigenschaften und JSON-Kandidaten gegen die gespeicherte Herkunft sowie die einzelnen aufbereiteten Aufnahmen gegen ihre gespeicherten Hashes und meldet fehlende Aufnahmen, fremde Ergebnisse und Overlayfehler. Bericht: `daten\_Berichte\Endkontrolle.json`.

Danach `07_IMPORTORDNER.cmd` oder:

```cmd
.venv\Scripts\python.exe tool.py import
```

Der Importlauf prüft zusätzlich die Protokolle/Hashes verbundener Serien und kopiert das endgültige Ergebnis nach `daten\_Import_Jahre\JAHR`. Darin stehen die langen Videos **anstelle** ihrer Einzelclips. Die Quellen in `_Ergebnis` und `_Verbunden` bleiben erhalten. Der Importordner wird nie ungefragt überschrieben.

Bei bewusst akzeptierten offenen Punkten, etwa nicht unterstützten Spezialoverlays:

```cmd
.venv\Scripts\python.exe tool.py import --allow-open
```

Dieser Befehl nimmt nur die vorhandenen geprüften Ergebnisse auf. Nicht zugeordnete Aufnahmen fehlen dann im Import; nicht gerenderte Overlays werden nicht nachgebildet. Fehlende/veränderte Ergebnisdateien und Serienkonflikte bleiben auch mit diesem Schalter harte Fehler.

**Nur die Medien aus `_Import_Jahre\JAHR` importieren.** Test-, Arbeits- und Sicherungsordner nicht zusätzlich importieren, sonst entstehen doppelte Aufnahmen. Jahresordner können vom ältesten zum neuesten nacheinander importiert werden. Eine exakt chronologische Reihenfolge in „Zuletzt hinzugefügt“ wird dadurch nicht garantiert.

Das Werkzeug meldet sich nicht bei iCloud an, lädt nichts hoch und löscht keine vorhandene Fotomediathek. Bestehende Apple-Alben oder Herkunftsangaben wie „Von WhatsApp gesichert“ werden nicht rekonstruiert.

## Eigener Datenpfad / macOS / Linux

Alle Python-Befehle akzeptieren `--root`:

```cmd
.venv\Scripts\python.exe tool.py pruefen --root "D:\Snapchat-Export"
```

Die nummerierten Windows-Starter verwenden immer den mitgelieferten Ordner `daten`. Für einen anderen Pfad die Befehle selbst ausführen und in allen Schritten denselben Pfad angeben.

Unter macOS/Linux Python 3.11+, ExifTool, FFmpeg und FFprobe installieren. Dann:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tool.py pruefen --root "/Pfad/zum/Export"
.venv/bin/python tool.py test --root "/Pfad/zum/Export"
```

Die Windows-Starter sind dort nicht verwendbar. Die öffentliche Version wurde lokal unter Linux getestet; ein vollständiger Test auf Windows/macOS und mit weiteren echten Exporten steht noch aus.

## Grenzen und Fehlermeldungen

- **SCOF-Spezialoverlays:** Manche Dateien heißen `.png`, sind aber ein anderer Container. Diese werden nicht automatisch zusammengesetzt. Original erhalten, Overlayfehler protokolliert.
- **Abweichendes Seitenverhältnis:** Ab mehr als 2,5 % Abweichung wird das Overlay nicht automatisch gestreckt. Original erhalten, manuelle Prüfung nötig.
- **Fehlende GPS-Daten:** Es werden keine Koordinaten erfunden. `0,0` wird als fehlender Standort behandelt.
- **Nicht passender Export:** Keine geratenen Zeitzonenverschiebungen, keine automatische Zusammenführung unterschiedlicher JSON-Listen.
- **Keine universelle Dublettenbereinigung:** Gleiche Bilder an verschiedenen Tagen werden nicht automatisch gelöscht.
- **Vollständigkeit:** Die Prüfung bezieht sich auf unterstützte Hauptdateien im vorliegenden Export. Sie beweist weder, dass Snapchat alle Memories exportiert hat, noch dass heuristisch zugeordnete Metadaten sachlich korrekt sind.
- **Keine Cloud-Beschleunigung:** Das Werkzeug beeinflusst weder iCloud-Uploadgeschwindigkeit noch die Reihenfolge paralleler Uploads.

Exitcodes: `0` erfolgreich, `1` Abbruch/ungültige Voraussetzungen, `2` offene Zuordnungen oder Datei-/Overlayfehler, `130` vom Benutzer abgebrochen. Die Videovorschlagsliste kann nicht prüfbare Videos melden; sie bleiben als Einzelclips erhalten.

## Datenschutz und Fehlermeldungen auf GitHub

Die Verarbeitung erfolgt lokal. Nur die Installation von Python-Abhängigkeiten benötigt Internet. ZIPs, Fotos, Videos und Berichte gehören **nicht** in dieses Repository. Die `.gitignore` schließt die üblichen Datenordner aus; vor jedem Upload trotzdem den Inhalt prüfen.

Berichte enthalten möglicherweise GPS-Koordinaten, Zeitstempel, UUIDs und lokale Pfade. Für ein Issue möglichst die Fehlermeldung und ein künstliches/anonymisiertes Beispiel verwenden. Keine vollständige persönliche JSON oder Medienarchive öffentlich anhängen.

## Tests und Entwicklung

```cmd
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Validierung dieser Erstveröffentlichung: 13 Tests unter Linux bestanden, einschließlich ExifTool-/FFmpeg-Integration; kein Test übersprungen.

Die Tests erzeugen künstliche Fotos und Videos. Integrationstests erfordern ExifTool, FFmpeg und FFprobe im `PATH`; andernfalls werden sie ausdrücklich übersprungen. Die Tests prüfen unter anderem Zuordnungskonflikte, über ZIPs verteilte Overlays, Wiederaufnahme, beschädigte Ergebnisse, Metadaten-Rücklesen und Videoinhalte vor/nach einem Schnitt.

## Verwandtes Projekt

[sean-mehra/Snapchat_Memories_Tool](https://github.com/sean-mehra/Snapchat_Memories_Tool) bietet ebenfalls Overlay-Verarbeitung, Metadaten und Videoverbindungen. Die bei Erstellung dieser Version geprüfte Implementierung nutzt IDs aus `Download Link` für die Zuordnung. Dieses Projekt konzentriert sich auf ZIP-Exporte mit bereits enthaltenen Medien und fehlenden Download-Links. Es übernimmt keinen Code aus diesem Repository.

## Lizenz

MIT für den Projektcode; siehe [LICENSE](LICENSE). Python, Pillow, ExifTool und FFmpeg bleiben eigenständige Projekte mit ihren jeweiligen Lizenzen. Ihre Binärdateien werden hier nicht mitgeliefert.
