# 👻 Snapchat Memories ZIP Tool

**Deine Snapchat-Erinnerungen in deiner Fotogalerie – mit Datum, Standort und auf Wunsch auch Texten und Stickern.**

Du hast deine Memories heruntergeladen, aber Datum oder Standort fehlen in den Dateien? Texte und Sticker liegen als separate Bilder daneben, und längere Videos bestehen aus kurzen Clips?

Dieses Tool bereitet deinen Snapchat-Export für den Import in Apple Fotos oder eine andere Fotogalerie vor. Du bekommst nach Jahren sortierte Fotos und Videos. Deine ursprünglichen ZIP-Dateien bleiben unverändert.

**[⬇️ Gesamtpaket herunterladen](https://github.com/L-Schreiter/Snapchat-Memories-ZIP-Tool/archive/refs/heads/main.zip)** · **[Einrichtung](docs/INSTALLATION.md)** · **[Ausführliche Anleitung](docs/ANLEITUNG.md)**

## Das bekommst du

| Funktion | Ergebnis |
| --- | --- |
| 📅 Datum & Standort | Verfügbare Aufnahmedaten werden direkt in die Dateien geschrieben. |
| 🖼️ Texte & Sticker | Original-Version **plus** eine zusätzliche Version mit unterstütztem Overlay. |
| 🎬 Geteilte Videos | Passende Clips werden vorgeschlagen und nach deiner Prüfung verbunden. |
| 📂 Ordnung nach Jahren | Ein fertiger Importordner, zum Beispiel mit den Unterordnern `2017`, `2018`, `2019`. |

*„Overlay“ bedeutet hier: die separat gespeicherten Texte, Sticker oder Bildeffekte einer Aufnahme.*

## Passt das zu meinem Export?

**Ja**, wenn deine `mydata…zip`-Dateien bereits Fotos/Videos im Ordner `memories` und eine `memories_history.json` enthalten. Die Download-Links in der JSON dürfen leer sein.

**Nein**, wenn du bisher nur eine HTML-Seite mit Download-Links hast. Lade dann zuerst die eigentlichen Medien herunter.

Du brauchst **Windows, Python, ExifTool und FFmpeg**. Die einmalige Einrichtung ist [hier Schritt für Schritt erklärt](docs/INSTALLATION.md). Danach startest du die Schritte per Doppelklick – Terminalbefehle sind für den normalen Ablauf nicht nötig.

## Los geht’s

### 1. Herunterladen & einrichten

[Gesamtpaket herunterladen](https://github.com/L-Schreiter/Snapchat-Memories-ZIP-Tool/archive/refs/heads/main.zip), vollständig entpacken und die [Einrichtung](docs/INSTALLATION.md) durchführen.

### 2. Snapchat-ZIPs hineinlegen

Kopiere **alle ZIP-Teile desselben Snapchat-Exports** in den Ordner **`daten`** im entpackten Tool.

**Die Snapchat-ZIPs nicht entpacken oder neu packen.** Das Tool liest sie direkt. Du musst keine gleichnamigen `html`-, `json`- oder `memories`-Ordner zusammenführen.

### 3. Prüfen & ausprobieren

Starte nacheinander per Doppelklick:

1. **`01_PRUEFEN.cmd`** – prüft, ob der Export zum Tool passt.
2. **`02_TEST.cmd`** – verarbeitet eine kleine Auswahl.

Öffne die Ergebnisse in **`daten → _Test → Jahr`**. Vergleiche Datum, Uhrzeit, Standort und Overlays mit Snapchat. Importiere auch ein paar Testdateien in deine Foto-App.

> **Warum der Test?** Bei Exporten ohne direkte Zuordnung nutzt das Tool Zeitstempel. Das kann mehrdeutig sein. Nicht eindeutig zugeordnete Aufnahmen bleiben zunächst offen; ein Standort wird nicht erfunden.

### 4. Alle Aufnahmen verarbeiten

Wenn die Testdateien passen, starte **`03_ALLES.cmd`**. Bestätige die vorherige Prüfung und lass den Vorgang durchlaufen.

Du kannst einen abgebrochenen Lauf erneut starten. Bereits fertige, unveränderte Ergebnisse werden erkannt. Immer nur einen Lauf gleichzeitig starten.

### 5. Fertigen Importordner erstellen

Wenn du geteilte Videos verbinden möchtest, erledige zuerst den optionalen Schritt unten. Ansonsten starte direkt:

1. **`06_ENDKONTROLLE.cmd`** – prüft Ergebnisse und meldet offene Punkte.
2. **`07_IMPORTORDNER.cmd`** – erstellt den Ordner für den Import.

**Deine fertigen Aufnahmen findest du unter `daten → _Import_Jahre → Jahr`.**

Importiere nur die Medien aus diesen Jahresordnern. Die Test- und Arbeitsordner nicht zusätzlich importieren, sonst entstehen doppelte Aufnahmen. Das Tool selbst lädt nichts zu iCloud hoch.

<details>
<summary><strong>🎬 Optional: kurze Videoclips wieder zusammensetzen</strong></summary>

Vor Schritt 5:

1. **`04_VIDEOS_VORSCHLAGEN.cmd`** starten.
2. **`daten\_Berichte\Videos_Vorschlaege.json`** mit einem Texteditor öffnen.
3. Die bei jeder Serie unter `clips` genannten Videos ansehen. Nur wenn sie zusammengehören, `"approved": false` in `"approved": true` ändern und speichern.
4. **`05_VIDEOS_VERBINDEN.cmd`** starten. Ergebnisse unter **`daten → _Verbunden → Jahr`** prüfen.
5. Danach mit Schritt 5 oben fortfahren.

Die Overlays der einzelnen Clips bleiben in der jeweiligen Videopassage erhalten. Im fertigen Importordner ersetzen die langen Videos ihre Einzelclips; die Einzelclips bleiben im Arbeitsordner gesichert.

Nicht jede zusammengehörige Serie wird erkannt. [Details zur Videoerkennung und Freigabe](docs/ANLEITUNG.md#schritt-7--geteilte-videos-prüfen-und-verbinden-optional).

</details>

## Etwas klappt nicht?

**Fehlermeldung oder offene Aufnahmen?** Nicht einfach ungeprüft importieren. Die [ausführliche Anleitung](docs/ANLEITUNG.md) erklärt Fehler, Sonderfälle und alle Befehle. Probleme kannst du auch als [GitHub-Issue melden](https://github.com/L-Schreiter/Snapchat-Memories-ZIP-Tool/issues). Bitte keine privaten Fotos, vollständigen JSON-Dateien oder GPS-Berichte öffentlich hochladen.

**Noch eine Beta:** Manche Spezialoverlays werden nicht unterstützt; dann bleibt die Original-Version erhalten. Videoverbindungen müssen geprüft werden. 13 automatisierte Tests unter Linux bestanden; ein vollständiger Test der öffentlichen Version auf Windows/macOS steht noch aus. [Grenzen und Fehlermeldungen](docs/ANLEITUNG.md#grenzen-und-fehlermeldungen).

---

**Von Leon gemeinsam mit ChatGPT (OpenAI) entwickelt.** Code, Anleitung und Tests wurden mit KI-Unterstützung erstellt. Kein offizielles Produkt von Snapchat, Apple oder OpenAI. Verarbeitung lokal auf deinem Computer. [MIT-Lizenz](LICENSE).
