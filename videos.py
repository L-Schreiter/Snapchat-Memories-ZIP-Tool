"""Suggest conservative video sequences; merge only explicitly approved lists."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import snapchat as s
from tool import inventory, write_json
from video_join import join


def candidates(videos):
    """Heuristic proposals, NOT proof. Missing timestamps never form a group."""
    groups = {}
    for video in videos:
        stamp = video['record']['vorher'].get('QuickTime:CreateDate')
        if not stamp or stamp.startswith(('0000:', '1904:', '1970:')): continue
        groups.setdefault(stamp, []).append(video)
    result = []
    for stamp, items in groups.items():
        items.sort(key=lambda v: v['zip_time'])
        if not 2 <= len(items) <= 6: continue
        try:
            internal = dt.datetime.strptime(stamp, '%Y:%m:%d %H:%M:%S')
        except ValueError: continue
        if abs((items[0]['zip_time'] - internal).total_seconds()) > 2: continue
        if len({v['record']['Quelle_SHA256'] for v in items}) != len(items): continue
        if not all(9.5 <= v['duration'] <= 10.5 for v in items[:-1]): continue
        if not 0 < items[-1]['duration'] <= 10.5: continue
        if not all(8 <= (b['zip_time'] - a['zip_time']).total_seconds() <= 12
                   for a,b in zip(items,items[1:])): continue
        result.append(items)
    return result


def propose(root):
    target = root / '_Berichte/Videos_Vorschlaege.json'
    if target.exists(): raise ValueError('Vorschlagsliste existiert. Erst sichern/umbenennen; Freigaben werden nicht ueberschrieben.')
    records = inventory(root)
    ffprobe = s.tool('ffprobe')
    videos, failures = [], []
    for record in records.values():
        original = record['original']
        if Path(original).suffix.lower() not in ('.mp4','.mov'): continue
        if record.get('Overlay_Fehler'):
            failures.append({'Datei': original, 'Fehler': 'Overlay ungeklaert; vorerst keine Verbindung'})
            continue
        try:
            meta = json.loads(s.run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',root/'_Ergebnis'/original]))
            stream = next(x for x in meta['streams'] if x['codec_type']=='video')
            duration = float(stream.get('duration', meta['format'].get('duration', 0)))
            videos.append({'record':record, 'zip_time':dt.datetime(*record['ZIP_Zeit']), 'duration':duration})
        except Exception as exc:
            failures.append({'Datei':original,'Fehler':str(exc)})
    proposals = []
    for group in candidates(videos):
        names = [v['record']['original'] for v in group]
        identifier = hashlib.sha256(json.dumps(names).encode()).hexdigest()[:16]
        proposals.append({'id':identifier,'approved':False,'clips':names,
                          'duration_seconds':[v['duration'] for v in group],
                          'expected_sha256':{n:h for v in group for n,h in v['record']['files'].items()}})
    write_json(target, {'Hinweis':'Jede Serie visuell pruefen, dann approved auf true setzen. Keine automatische Freigabe.',
                        'Serien':proposals,'Nicht_geprueft':failures})
    print(f'{len(proposals)} Vorschlaege; {len(failures)} nicht pruefbare Videos. Liste: {target}')


def merge(root):
    document = json.loads((root/'_Berichte/Videos_Vorschlaege.json').read_text(encoding='utf-8-sig'))
    by_name = {r['original']:r for r in inventory(root).values()}
    selected = [p for p in document['Serien'] if p.get('approved') is True]
    if not selected: raise ValueError('Keine Serie mit approved: true freigegeben')
    plans, claimed = [], set()
    for proposal in selected:
        names = proposal['clips']
        if not 2 <= len(names) <= 6 or len(set(names)) != len(names): raise ValueError('2 bis 6 unterschiedliche Clips erforderlich')
        if any(n not in by_name or n in claimed for n in names): raise ValueError('Clip fehlt oder mehrfach verwendet')
        claimed.update(names)
        records = [by_name[n] for n in names]
        inputs = {n:h for r in records for n,h in r['files'].items()}
        if inputs != proposal['expected_sha256']: raise ValueError('Vorschlag passt nicht mehr zum aktuellen Bestand')
        if any(r.get('Overlay_Fehler') for r in records): raise ValueError('Overlayfehler zuerst klaeren')
        identifier = hashlib.sha256(json.dumps(names).encode()).hexdigest()[:16]
        plans.append((identifier, names, records, inputs))
    ffmpeg, ffprobe, exif = s.tool('ffmpeg'), s.tool('ffprobe'), s.tool('exiftool')
    work = root/'_Verbunden'; work.mkdir(exist_ok=True)
    for identifier, names, records, inputs in plans:
        receipt = work/'_Protokolle'/(identifier+'.json')
        if receipt.exists():
            saved=json.loads(receipt.read_text(encoding='utf-8'))
            if saved['inputs'] != inputs or any(not (work/n).is_file() or s.sha(work/n)!=h for n,h in saved['outputs'].items()):
                raise ValueError('Vorhandene Serie veraendert')
            print('Bereits fertig:',identifier); continue
        date=dt.datetime.fromisoformat(records[0]['Datum_UTC'])
        coord=tuple(records[0]['GPS']) if records[0]['GPS'] is not None else None
        originals=[root/'_Ergebnis'/n for n in names]
        overlay=[]
        for record, original in zip(records,originals):
            variants=[root/'_Ergebnis'/n for n in record['files'] if '_Mit_Overlay.' in n]
            overlay.append(variants[0] if variants else original)
        variants=[('Original',originals)]
        if overlay != originals: variants.append(('Mit_Overlay',overlay))
        outputs, checks = {}, {}
        with tempfile.TemporaryDirectory(dir=work) as temp:
            temp=Path(temp)
            for label, clips in variants:
                name=date.strftime('%Y-%m-%d_%H-%M-%S_UTC_')+identifier+'_Verbunden_'+label+'.mp4'
                print('Verbinde:',name,flush=True)
                out=temp/name
                checks[label]=join(clips,out,temp,ffmpeg,ffprobe)
                s.write_metadata(exif,out,(date,coord))
                rel=date.strftime('%Y')+'/'+name
                dest=work/rel; dest.parent.mkdir(exist_ok=True)
                digest=s.sha(out)
                if dest.exists() and s.sha(dest)!=digest: raise ValueError('Zielkonflikt: '+name)
                if not dest.exists(): os.replace(out,dest)
                outputs[rel]=digest
        write_json(receipt,{'inputs':inputs,'outputs':outputs,'clips':names,'checks':checks,
                           'Datum_UTC':date.isoformat(),'GPS':coord,
                           'Hinweis':'Metadaten vom ersten Clip. Standortwechsel werden nicht als Route gespeichert.'})
    print('Fertig. Verbundene Videos ansehen; danach tool.py import ausfuehren.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['vorschlagen','verbinden'])
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent/'daten')
    args=p.parse_args()
    (propose if args.mode=='vorschlagen' else merge)(args.root.resolve())


if __name__=='__main__':
    try: main()
    except KeyboardInterrupt: print('Abgebrochen; Quellen unveraendert.'); sys.exit(130)
    except Exception as exc: print('ABBRUCH:',exc); sys.exit(1)
