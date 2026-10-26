"""Public command line interface. No account access; all processing is local."""
import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import snapchat as s


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def safe_file(base, relative):
    p = (base / relative).resolve()
    if not p.is_relative_to(base.resolve()) or p == base.resolve():
        raise ValueError('Pfad ausserhalb des Ausgabeordners')
    return p


def inventory(root):
    output = root / '_Ergebnis'
    records = {}
    for marker in sorted((output / '_Pruefprotokolle').glob('*/*.json')):
        data = json.loads(marker.read_text(encoding='utf-8'))
        year = dt.datetime.fromisoformat(data['Datum_UTC']).strftime('%Y')
        files = {}
        if not data['sha256']: raise ValueError('Leeres Pruefprotokoll')
        for name, digest in data['sha256'].items():
            if Path(name).name != name: raise ValueError('Ungueltiger Dateiname')
            path = safe_file(output, year + '/' + name)
            if not path.is_file() or s.sha(path) != digest:
                raise ValueError('Datei fehlt oder wurde veraendert: ' + str(path))
            files[year + '/' + name] = digest
        originals = [f for f in files if '_Original.' in f]
        if len(originals) != 1: raise ValueError('Original nicht eindeutig')
        key = (data['zip'], data['quelle'])
        if key in records: raise ValueError('Mehrere Ergebnisse derselben Quelldatei. Neuen Arbeitsordner verwenden.')
        data['files'] = files
        data['original'] = originals[0]
        records[key] = data
    return records


def choose_record(candidates):
    """Explicit opt-in heuristic, never a claim of factual identity."""
    with_gps = [r for r in candidates if r[1] is not None]
    return sorted(with_gps or candidates, key=lambda r: (r[0], str(r[1])))[0]


def process(args):
    paths, rows, plan, others, overlays = s.inspect_zips(args.root)
    s.save_plan(args.root, rows, plan, paths, others, overlays)
    if args.expected_zips is not None and len(paths) != args.expected_zips:
        raise ValueError('ZIP-Anzahl stimmt nicht: gefunden ' + str(len(paths)))
    if args.mode == 'pruefen': return 0
    if not args.zip_times_utc_confirmed and args.mode == 'alles':
        raise ValueError('Zuerst Testimporte pruefen; danach --zip-times-utc-confirmed angeben. Siehe README.')
    if any(p['status'] in ('KEIN_TREFFER', 'DATUM_WIDERSPRUCH') for p in plan):
        raise ValueError('Zeitstempel/Layout passt nicht. Siehe _Berichte/Zuordnung.csv; keine automatische Korrektur.')
    decisions = []
    if args.ambiguity == 'gps-earliest':
        for p in plan:
            if p['status'] == 'MEHRDEUTIG':
                p['record'] = choose_record(p['candidates'])
                p['status'] = 'REGEL_GPS_FRUEHESTES'
                decisions.append({'Datei': p['entry']['info'].filename,
                                  'Auswahl': [p['record'][0].isoformat(), p['record'][1]],
                                  'Kandidaten': [(d.isoformat(), g) for d,g in p['candidates']]})
    selected = sorted([p for p in plan if p['record'] is not None],
                      key=lambda p: (p['record'][0], p['entry']['uid']))
    if args.mode == 'test':
        samples = {}
        for video in (False, True):
            for overlay in (False, True):
                group = [p for p in selected if (p['entry']['ext'] in ('mp4','mov')) == video
                         and bool(p['overlay']) == overlay]
                for p in group[:2] + group[-2:]:
                    samples[(str(p['entry']['zip']), p['entry']['info'].filename)] = p
        selected = list(samples.values())
    output = args.root / ('_Test' if args.mode == 'test' else '_Ergebnis')
    output.mkdir(exist_ok=True)
    (output / '_temp').mkdir(exist_ok=True)
    exif, ffmpeg = s.tool('exiftool'), s.tool('ffmpeg')
    logs = []
    for i, p in enumerate(selected, 1):
        name = p['entry']['info'].filename
        print(f'[{i}/{len(selected)}] {name}', flush=True)
        try:
            status, detail = s.process(p, output, exif, ffmpeg), ''
        except Exception as exc:
            status, detail = 'FEHLER', str(exc)
            print('FEHLER:', detail, flush=True)
        logs.append({'Datei': name, 'Status': status, 'Hinweis': detail})
        s.csv_write(output / 'Verarbeitung.csv', logs, ['Datei','Status','Hinweis'])
    write_json(output / 'Metadaten_Entscheidungen.json', decisions)
    open_count = sum(p['record'] is None for p in plan)
    errors = sum('FEHLER' in r['Status'] for r in logs)
    print(f'Fertig: {len(logs)} bearbeitet; {errors} Datei-/Overlayfehler; {open_count} Zuordnungen offen.')
    print('Originale mit Overlayfehler bleiben erhalten. Details in den Pruefprotokollen.')
    return 2 if errors or open_count else 0


def audit(root):
    _, _, plan, others, _ = s.inspect_zips(root)
    records = inventory(root)
    expected = [(p['entry']['zip'].name, p['entry']['info'].filename) for p in plan]
    if len(expected) != len(set(expected)):
        raise ValueError('Doppelte Hauptdateinamen innerhalb des ZIP-Bestands')
    # Check current archive headers and candidate data against saved provenance.
    # This is not a cryptographic re-read of every compressed source file.
    for item in plan:
        e = item['entry']; key = (e['zip'].name, e['info'].filename)
        if key not in records: continue
        r = records[key]
        current_overlay_crc = item['overlay']['info'].CRC if item['overlay'] else None
        saved_record = (dt.datetime.fromisoformat(r['Datum_UTC']), tuple(r['GPS']) if r['GPS'] is not None else None)
        if (r['ZIP_CRC'] != e['info'].CRC or r['ZIP_Bytes'] != e['info'].file_size
            or r['ZIP_Zeit'] != list(e['info'].date_time) or r['Overlay_CRC'] != current_overlay_crc
            or saved_record not in item['candidates'] or item['status'] == 'DOPPELTE_DATEI_ID'):
            raise ValueError('Quellen/Zuordnung seit Verarbeitung veraendert: ' + str(key))
    missing = [key for key in expected if key not in records]
    extra = [key for key in records if key not in expected]
    overlay_errors = [key for key, r in records.items() if r.get('Overlay_Fehler')]
    result = {'Hauptdateien_im_Export': len(expected), 'Gepruefte_Ergebnisse': len(records),
              'Offen': missing, 'Fremde_Ergebnisse': extra, 'Overlayfehler': overlay_errors,
              'Nicht_unterstuetzte_Dateien': others,
              'Bestandspruefung': 'BESTANDEN' if not missing and not extra and not overlay_errors and not others else 'OFFENE_PUNKTE',
              'Hinweis': 'Hash-/Bestandspruefung; kein Beweis der Metadaten-Zuordnung oder eines vollstaendigen Snapchat-Exports.'}
    write_json(root / '_Berichte/Endkontrolle.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def copy_verified(source, dest, digest):
    if s.sha(source) != digest: raise ValueError('Quelle veraendert: ' + str(source))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    if s.sha(dest) != digest: raise ValueError('Kopie stimmt nicht: ' + str(dest))


def prepare_import(root, allow_open=False):
    check = audit(root)
    if check['Bestandspruefung'] != 'BESTANDEN' and not allow_open:
        raise ValueError('Offene Punkte pruefen. --allow-open exportiert bewusst nur die vorhandenen Ergebnisse.')
    destination = root / '_Import_Jahre'
    if destination.exists():
        raise ValueError('_Import_Jahre existiert bereits. Vor erneutem Erstellen ausserhalb des Arbeitsordners sichern/umbenennen.')
    records = inventory(root)
    files = {name: (root / '_Ergebnis' / name, digest) for r in records.values() for name, digest in r['files'].items()}
    excluded = set()
    for receipt in sorted((root / '_Verbunden/_Protokolle').glob('*.json')):
        data = json.loads(receipt.read_text(encoding='utf-8'))
        if not data['outputs'] or not data['inputs']: raise ValueError('Leeres Serienprotokoll')
        for name, digest in data['inputs'].items():
            if name in excluded or name not in files or files[name][1] != digest:
                raise ValueError('Serienkonflikt oder veraenderter Clip: ' + name)
            excluded.add(name)
        for name, digest in data['outputs'].items():
            source = safe_file(root / '_Verbunden', name)
            if s.sha(source) != digest or name in files: raise ValueError('Serienausgabe fehlt/konfliktbehaftet')
            files[name] = (source, digest)
    # Build in a temporary directory; publish only when every copy verifies.
    with tempfile.TemporaryDirectory(prefix='_Import_temp_', dir=root) as temp:
        temp = Path(temp)
        for name, (source, digest) in files.items():
            if name not in excluded: copy_verified(source, safe_file(temp, name), digest)
        write_json(temp / 'Importprotokoll.json', {'Dateien': {n:h for n,(_,h) in files.items() if n not in excluded},
                   'Ersetzte_Einzelclips': sorted(excluded), 'Endkontrolle': check})
        os.replace(temp, destination)
    print('Importordner:', destination)
    print('Nur Medien aus den Jahresordnern importieren. Einzelclips bleiben in _Ergebnis gesichert.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pruefen','test','alles','kontrolle','import'])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent / 'daten')
    parser.add_argument('--expected-zips', type=int)
    parser.add_argument('--zip-times-utc-confirmed', action='store_true')
    parser.add_argument('--ambiguity', choices=['skip','gps-earliest'], default='skip')
    parser.add_argument('--allow-open', action='store_true')
    args = parser.parse_args()
    args.root = args.root.resolve()
    if args.mode == 'kontrolle': return 0 if audit(args.root)['Bestandspruefung']=='BESTANDEN' else 2
    if args.mode == 'import': prepare_import(args.root, args.allow_open); return 0
    return process(args)


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: print('Abgebrochen. Quellen bleiben erhalten.'); sys.exit(130)
    except Exception as exc: print('ABBRUCH:', exc); sys.exit(1)
