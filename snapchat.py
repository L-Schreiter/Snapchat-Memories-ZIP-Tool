"""Snapchat export processor: public beta 0.1.0. Only reads ZIPs; writes separate outputs.
ZIP timestamp matching is a heuristic, not a proven identity.
No network access or source deletion.
"""
import argparse, collections, csv, datetime as dt, hashlib, json, os, re
import shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2})_([0-9a-fA-F-]{36})-(main|overlay)\.(jpg|jpeg|png|mp4|mov|webp)$', re.I)
UTC = dt.timezone.utc

def run(cmd):
    p = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-2500:])
    return p.stdout

def gps(text):
    m = re.fullmatch(r'Latitude, Longitude:\s*([-\d.]+),\s*([-\d.]+)', text.strip())
    if not m: raise ValueError('Unbekanntes GPS-Format')
    lat, lon = map(float, m.groups())
    if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError('GPS ausserhalb des Wertebereichs')
    return None if (lat, lon) == (0, 0) else (lat, lon)

def index_rows(rows):
    idx = collections.defaultdict(list)
    for r in rows:
        date = dt.datetime.strptime(r['Date'], '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=UTC)
        typ = r['Media Type']
        if typ not in ('Image', 'Video'): raise ValueError('Unbekannter Medientyp')
        record = (date, gps(r['Location']) if r.get('Location', '').strip() else None)
        idx[(date.replace(second=date.second // 2 * 2), typ)].append(record)
    return idx

def match(entry, idx):
    # DOS ZIP timestamps have 2-second resolution and no zone.
    # UTC alignment is an export-specific assumption requiring user validation.
    stamp = dt.datetime(*entry['info'].date_time, tzinfo=UTC)
    typ = 'Video' if entry['ext'] in ('mp4', 'mov') else 'Image'
    candidates = set(idx.get((stamp, typ), []))
    if not candidates: return 'KEIN_TREFFER', None, []
    if any(e[0].strftime('%Y-%m-%d') != entry['day'] for e in candidates):
        return 'DATUM_WIDERSPRUCH', None, sorted(candidates, key=str)
    if len(candidates) != 1: return 'MEHRDEUTIG', None, sorted(candidates, key=str)
    record = next(iter(candidates))
    if entry['day'] != record[0].strftime('%Y-%m-%d'):
        return 'DATUM_WIDERSPRUCH', None, list(candidates)
    return 'EINDEUTIG', record, list(candidates)

def inspect_zips(root):
    paths = sorted(p for p in root.iterdir() if p.is_file() and p.name.lower().startswith('mydata') and p.suffix.lower() == '.zip')
    if not paths: raise RuntimeError('Keine mydata*.zip im ausgewaehlten Ordner.')
    manifests, entries, others = [], [], []
    for path in paths:
        print('Lese', path.name, flush=True)
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                name = info.filename.replace('\\', '/')
                if name.endswith('/memories_history.json') or name == 'memories_history.json':
                    manifests.append(json.loads(z.read(info).decode('utf-8-sig'))['Saved Media'])
                m = PATTERN.fullmatch(name.rsplit('/', 1)[-1])
                if m:
                    entries.append(dict(zip=path, info=info, day=m[1], uid=m[2].upper(), role=m[3].lower(), ext=m[4].lower()))
                elif not info.is_dir() and Path(name).suffix.lower() in ('.jpg','.mp4','.png','.mov','.webp','.jpeg'):
                    others.append(name)
    if not manifests: raise RuntimeError('memories_history.json fehlt.')
    if not entries: raise RuntimeError('Keine passenden Mediendateien in den ZIPs. Reine Link-Exporte werden nicht unterstuetzt.')
    # Identical repeated manifests are allowed; different ones require review.
    signatures = {json.dumps(x, sort_keys=True) for x in manifests}
    if len(signatures) != 1: raise RuntimeError('Mehrere unterschiedliche JSON-Listen: keine automatische Vermischung.')
    rows = manifests[0]
    idx = index_rows(rows)
    by_id = collections.defaultdict(list)
    for e in entries: by_id[(e['day'], e['uid'])].append(e)
    plan = []
    for e in entries:
        if e['role'] != 'main': continue
        group = by_id[(e['day'], e['uid'])]
        overlays = [x for x in group if x['role'] == 'overlay']
        status, record, candidates = match(e, idx)
        if len([x for x in group if x['role'] == 'main']) != 1 or len(overlays)>1:
            status, record = 'DOPPELTE_DATEI_ID', None
        plan.append(dict(entry=e, overlay=overlays[0] if len(overlays)==1 else None,
                         status=status, record=record, candidates=candidates))
    return paths, rows, plan, others, sum(e['role']=='overlay' for e in entries)

def csv_write(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=';');w.writeheader();w.writerows(rows)

def save_plan(root, rows, plan, paths, others, overlays):
    report = root / '_Berichte';report.mkdir(exist_ok=True)
    records=[]
    for p in plan:
        e=p['entry']; records.append(dict(ZIP=e['zip'].name, Datei=e['info'].filename,
          Status=p['status'], Kandidaten=json.dumps([(a.isoformat(),b) for a,b in p['candidates']]),
          Overlay=p['overlay']['info'].filename if p['overlay'] else ''))
    csv_write(report/'Zuordnung.csv',records,['ZIP','Datei','Status','Kandidaten','Overlay'])
    summary=dict(ZIPs=len(paths),JSON_Eintraege=len(rows),Hauptdateien=len(plan),Overlays=overlays,
                 Status=dict(collections.Counter(p['status'] for p in plan)),Unbekannte_Dateien=others)
    (report/'Zusammenfassung.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False), flush=True)
    return report

def tool(name):
    found = shutil.which(name)
    if found: return found
    # Support portable executables alongside this program and common ExifTool installer path.
    for base in [Path(__file__).parent/'tools', Path(os.environ.get('ProgramFiles',''))/'ExifTool',
                 Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'ExifTool',
                 Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft'/'WinGet'/'Links']:
        p=base/(name+'.exe')
        if p.is_file(): return str(p)
    raise RuntimeError(name+' nicht gefunden. Zuerst EINRICHTEN.cmd starten und danach neue Konsole oeffnen.')

def extract(e, target):
    with zipfile.ZipFile(e['zip']) as z, z.open(e['info']) as source, target.open('wb') as dest:
        shutil.copyfileobj(source,dest)
    if target.stat().st_size!=e['info'].file_size: raise RuntimeError('Dateigroesse stimmt nicht')
    return target

def read_metadata(exif, path):
    return json.loads(run([exif,'-j','-G1','-n','-DateTimeOriginal','-OffsetTimeOriginal',
      '-CreateDate','-CreationDate','-GPSLatitude','-GPSLongitude','-Composite:GPSLatitude','-Composite:GPSLongitude','-GPSCoordinates',path]))[0]

def write_metadata(exif, path, record):
    date, coord = record
    date_str=date.strftime('%Y:%m:%d %H:%M:%S')
    video=path.suffix.lower() in ('.mp4','.mov')
    args=[exif,'-overwrite_original','-P']
    if video:
        # Default QuickTimeUTC=0: supplied numeric QuickTime timestamps are raw UTC.
        args+=['-api','QuickTimeUTC=0']
        for tag in ['QuickTime:CreateDate','QuickTime:ModifyDate','QuickTime:TrackCreateDate',
                    'QuickTime:TrackModifyDate','QuickTime:MediaCreateDate','QuickTime:MediaModifyDate']:
            args.append('-'+tag+'='+date_str)
        args+=['-Keys:CreationDate='+date_str+'+00:00']
        if coord: args+=['-Keys:GPSCoordinates=%+.7f%+.7f/'%coord]
    else:
        args+=['-EXIF:DateTimeOriginal='+date_str,'-EXIF:CreateDate='+date_str,
               '-EXIF:ModifyDate='+date_str,'-EXIF:OffsetTimeOriginal=+00:00',
               '-EXIF:OffsetTimeDigitized=+00:00','-EXIF:OffsetTime=+00:00']
        if coord:
            lat,lon=coord
            args+=['-EXIF:GPSLatitude='+str(abs(lat)), '-EXIF:GPSLatitudeRef='+('N' if lat>=0 else 'S'),
                   '-EXIF:GPSLongitude='+str(abs(lon)), '-EXIF:GPSLongitudeRef='+('E' if lon>=0 else 'W')]
    run(args+[path])
    os.utime(path,(date.timestamp(),date.timestamp()))
    meta=read_metadata(exif,path)
    if video:
        if meta.get('QuickTime:CreateDate') != date_str or meta.get('Keys:CreationDate') != date_str+'+00:00':
            raise RuntimeError('Video-Datumspruefung fehlgeschlagen: '+str(meta))
        if coord:
            numbers=re.findall(r'[-+]?\d+(?:\.\d+)?',str(meta.get('Keys:GPSCoordinates','')))
            if len(numbers)<2 or any(abs(float(numbers[i])-coord[i])>1e-5 for i in range(2)):
                raise RuntimeError('Video-GPS-Pruefung fehlgeschlagen: '+str(meta))
    else:
        if meta.get('ExifIFD:DateTimeOriginal')!=date_str or meta.get('ExifIFD:OffsetTimeOriginal')!='+00:00':
            raise RuntimeError('Foto-Datumspruefung fehlgeschlagen')
        if coord:
            lat=float(meta.get('Composite:GPSLatitude',meta.get('GPS:GPSLatitude',999)))
            lon=float(meta.get('Composite:GPSLongitude',meta.get('GPS:GPSLongitude',999)))
            # Numeric EXIF latitude may be unsigned; use refs via Composite values when available.
            if abs(lat-coord[0])>1e-5 or abs(lon-coord[1])>1e-5:
                raise RuntimeError('Foto-GPS-Pruefung fehlgeschlagen: '+str(meta))
    return meta

def resize_overlay(im, size):
    from PIL import Image
    if abs((im.width/im.height)/(size[0]/size[1])-1)>0.025:
        raise RuntimeError('Overlay-Seitenverhaeltnis weicht ab; manuelle Kontrolle erforderlich.')
    return im.resize(size,Image.Resampling.LANCZOS)

def compose_photo(source, overlay, dest):
    from PIL import Image,ImageOps
    with Image.open(source) as raw:
        base=ImageOps.exif_transpose(raw).convert('RGBA')
        layer=resize_overlay(overlay,base.size)
        result=Image.alpha_composite(base,layer).convert('RGB')
        opts=dict(quality=98,subsampling=0)
        if raw.info.get('icc_profile'):opts['icc_profile']=raw.info['icc_profile']
        result.save(dest,**opts)

def compose_video(ffmpeg, source, overlay, dest, temp):
    from PIL import Image
    # FFmpeg autorotation determines actual display dimensions, not coded dimensions.
    frame=temp/'frame.png'
    run([ffmpeg,'-v','error','-nostdin','-y','-i',source,'-frames:v','1',frame])
    with Image.open(frame) as im: size=im.size
    layer=resize_overlay(overlay,size);layerpath=temp/'layer.png';layer.save(layerpath)
    run([ffmpeg,'-v','error','-nostdin','-y','-i',source,'-i',layerpath,
      '-filter_complex','[0:v:0][1:v:0]overlay=0:0:eof_action=repeat:format=auto,format=yuv420p[v]',
      '-map','[v]','-map','0:a?','-map_metadata','-1','-c:v','libx264','-preset','medium',
      '-crf','16','-c:a','copy','-metadata:s:v:0','rotate=0','-movflags','+faststart',dest])

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def process(p, output, exif, ffmpeg):
    from PIL import Image
    e=p['entry'];date,coord=p['record'];stem=date.strftime('%Y-%m-%d_%H-%M-%S_UTC_')+e['uid']+'_'+hashlib.sha256((e['zip'].name+'|'+e['info'].filename).encode()).hexdigest()[:8]
    final=output/date.strftime('%Y')
    fingerprint=hashlib.sha256(json.dumps([e['zip'].name,e['info'].filename,e['info'].CRC,
      p['overlay']['info'].CRC if p['overlay'] else None,date.isoformat(),coord,'public-0.1.0'],sort_keys=True).encode()).hexdigest()
    marker=output/'_Pruefprotokolle'/date.strftime('%Y')/(stem+'.json')
    if marker.is_file():
        saved=json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('fingerprint')==fingerprint and all((final/n).is_file() and sha(final/n)==h for n,h in saved['sha256'].items()):
            return saved['Overlay']
        raise RuntimeError('Vorhandenes Ergebnis veraendert: '+str(final))
    final.mkdir(parents=True,exist_ok=True)
    marker.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='snap_',dir=output/'_temp') as tmp:
        temp=Path(tmp);bundle=temp/'fertig';bundle.mkdir()
        source=extract(e,temp/('source.'+e['ext']))
        before=read_metadata(exif,source)
        original=bundle/(stem+'_Original.'+e['ext']);shutil.copyfile(source,original)
        write_metadata(exif,original,p['record'])
        overlay_state='KEIN_OVERLAY'
        overlay_error = None
        if p['overlay']:
            try:
                op=extract(p['overlay'],temp/'overlay.bin')
                with Image.open(op) as opened: layer=opened.convert('RGBA')
                if layer.getchannel('A').getextrema()[1]==0:
                    overlay_state='TRANSPARENT_KEINE_ZWEITE_VERSION'
                else:
                    video=e['ext'] in ('mp4','mov')
                    rendered=bundle/(stem+'_Mit_Overlay'+('.mp4' if video else '.jpg'))
                    if video: compose_video(ffmpeg,source,layer,rendered,temp)
                    else: compose_photo(source,layer,rendered)
                    # Preserve available descriptive metadata; exclude structural/orientation tags.
                    run([exif,'-overwrite_original','-TagsFromFile',original,'-XMP:All','-IPTC:All','-GPS:All','-Keys:GPSCoordinates',rendered])
                    write_metadata(exif,rendered,p['record'])
                    overlay_state='ZWEI_VERSIONEN'

            except Exception as exc:
                overlay_state = 'ORIGINAL_OHNE_OVERLAY_FEHLER'
                overlay_error = str(exc)
                for partial in bundle.iterdir():
                    if partial != original: partial.unlink()
        hashes={f.name:sha(f) for f in bundle.iterdir() if f.is_file()}
        (bundle/'geprueft.json').write_text(json.dumps(dict(fingerprint=fingerprint,sha256=hashes,
           quelle=e['info'].filename,zip=e['zip'].name,vorher=before,
           Datum_UTC=date.isoformat(),GPS=coord,Overlay=overlay_state,Overlay_Fehler=overlay_error,
           Quelle_SHA256=sha(source),ZIP_Zeit=list(e['info'].date_time),Zuordnung=p['status'],
           ZIP_CRC=e['info'].CRC,ZIP_Bytes=e['info'].file_size,
           Overlay_CRC=p['overlay']['info'].CRC if p['overlay'] else None,
           Kandidaten=[(d.isoformat(),g) for d,g in p['candidates']]),indent=2,ensure_ascii=False),encoding='utf-8')
        # Publish each media file, then the completion marker. A partial run
        # can resume only when existing files match the newly checked bytes.
        for name, digest in hashes.items():
            target=final/name
            if target.exists() and (not target.is_file() or sha(target)!=digest):
                raise RuntimeError('Vorhandene Datei weicht ab: '+str(target))
        for name in hashes:
            target=final/name
            if not target.exists(): os.replace(bundle/name,target)
        os.replace(bundle/'geprueft.json',marker)
    return overlay_state
