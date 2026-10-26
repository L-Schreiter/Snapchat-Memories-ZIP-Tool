"""Synthetic fixtures only; no personal Snapchat data."""
import argparse, datetime as dt, io, json, shutil, tempfile, unittest, zipfile
from pathlib import Path
from PIL import Image
import snapchat as s
import tool, videos
from video_join import join
UID='00000000-0000-0000-0000-000000000001'
STAMP=(2020,1,2,12,0,0)
def picture(mode='RGB', color='red'):
    b=io.BytesIO(); Image.new(mode,(32,48),color).save(b,'PNG' if mode=='RGBA' else 'JPEG'); return b.getvalue()
def row(date='2020-01-02 12:00:01 UTC',location=''):
    return {'Date':date,'Media Type':'Image','Location':location,'Download Link':''}
def archive(root,entries,rows,name='mydata-test.zip'):
    with zipfile.ZipFile(root/name,'w') as z:
        z.writestr('json/memories_history.json',json.dumps({'Saved Media':rows}))
        for filename,stamp,body in entries: z.writestr(zipfile.ZipInfo('memories/'+filename,stamp),body)
def entry(day='2020-01-02',stamp=STAMP): return (f'{day}_{UID}-main.jpg',stamp,picture())
def args(root): return argparse.Namespace(root=root,expected_zips=None,mode='alles',zip_times_utc_confirmed=True,ambiguity='skip')
class CoreTests(unittest.TestCase):
    def test_missing_location_odd_second(self):
        status,record,_=s.match({'info':zipfile.ZipInfo('x',STAMP),'ext':'jpg','day':'2020-01-02'},s.index_rows([row()]))
        self.assertEqual(status,'EINDEUTIG'); self.assertEqual(record[0].second,1); self.assertIsNone(record[1])
    def test_ambiguous_and_day_conflict(self):
        idx=s.index_rows([row(),row('2020-01-02 12:00:00 UTC')])
        e={'info':zipfile.ZipInfo('x',STAMP),'ext':'jpg','day':'2020-01-02'}
        self.assertEqual(s.match(e,idx)[0],'MEHRDEUTIG'); self.assertIsNone(s.match(e,idx)[1])
        e['day']='2020-01-03'; self.assertEqual(s.match(e,idx)[0],'DATUM_WIDERSPRUCH')
    def test_same_uuid_different_days_split_overlay(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); rows=[row(),row('2020-01-03 12:00:01 UTC')]
            archive(root,[entry(),entry('2020-01-03',(2020,1,3,12,0,0))],rows)
            archive(root,[(f'2020-01-02_{UID}-overlay.png',STAMP,b'overlay')],rows,'mydata-2.zip')
            plan=s.inspect_zips(root)[2]
            self.assertEqual([p['status'] for p in plan],['EINDEUTIG']*2)
            self.assertEqual(sum(p['overlay'] is not None for p in plan),1)
    def test_duplicate_day_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); archive(root,[entry()],[row()]); archive(root,[entry()],[row()],'mydata-2.zip')
            self.assertTrue(all(p['record'] is None for p in s.inspect_zips(root)[2]))
    def test_conflicting_manifests(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); archive(root,[entry()],[row()]); archive(root,[],[row('2020-01-03 12:00:00 UTC')],'mydata-2.zip')
            with self.assertRaises(RuntimeError): s.inspect_zips(root)
    def test_policy_preserves_pair(self):
        a=(dt.datetime(2020,1,2,12,0,tzinfo=s.UTC),None); b=(dt.datetime(2020,1,2,12,0,1,tzinfo=s.UTC),(10.,20.))
        self.assertEqual(tool.choose_record([a,b]),b)
    def test_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError): tool.safe_file(Path(td),'../outside')
    def test_overlay_aspect(self):
        with self.assertRaises(RuntimeError): s.resize_overlay(Image.new('RGBA',(10,10)),(10,20))
    def test_conservative_video_candidates(self):
        def clip(second,duration,digest):
            return {'zip_time':dt.datetime(2020,1,2,12,0,second),'duration':duration,
                    'record':{'vorher':{'QuickTime:CreateDate':'2020:01:02 12:00:00'},'Quelle_SHA256':digest}}
        a,b=clip(0,10,'a'),clip(10,5,'b'); self.assertEqual(len(videos.candidates([b,a])),1)
        a['duration']=2; self.assertEqual(videos.candidates([a,b]),[])
        a['duration']=10; b['record']['Quelle_SHA256']='a'; self.assertEqual(videos.candidates([a,b]),[])

@unittest.skipUnless(all(shutil.which(x) for x in ('exiftool','ffmpeg','ffprobe')), 'Requires ExifTool, FFmpeg and FFprobe on PATH')
class IntegrationTests(unittest.TestCase):
    def test_photo_resume_audit_import_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); archive(root,[entry(),(f'2020-01-02_{UID}-overlay.png',STAMP,picture('RGBA',(0,255,0,128)))],
                                   [row(location='Latitude, Longitude: -10.0, -20.0')])
            before=s.sha(root/'mydata-test.zip')
            self.assertEqual(tool.process(args(root)),0); self.assertEqual(tool.process(args(root)),0)
            self.assertEqual(tool.audit(root)['Bestandspruefung'],'BESTANDEN')
            tool.prepare_import(root); self.assertEqual(len(list((root/'_Import_Jahre/2020').glob('*.jpg'))),2)
            self.assertEqual(s.sha(root/'mydata-test.zip'),before)
            with self.assertRaises(ValueError): tool.prepare_import(root)
            next((root/'_Ergebnis/2020').glob('*_Original.jpg')).write_bytes(b'changed')
            with self.assertRaises(ValueError): tool.inventory(root)
    def test_broken_overlay_keeps_original(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); archive(root,[entry(),(f'2020-01-02_{UID}-overlay.png',STAMP,b'bad PNG')],[row()])
            self.assertEqual(tool.process(args(root)),2); self.assertEqual(len(tool.inventory(root)),1)
            self.assertEqual(len(tool.audit(root)['Overlayfehler']),1)
            with self.assertRaises(ValueError): tool.prepare_import(root)
            tool.prepare_import(root,True); self.assertEqual(len(list((root/'_Import_Jahre/2020').glob('*.jpg'))),1)
    def test_join_preserves_per_clip_pixels_and_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); clips=[root/'a.mp4',root/'b.mp4']
            for path,color in zip(clips,('red','blue')):
                s.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',f'color=c={color}:s=32x48:r=30:d=0.5','-c:v','libx264','-pix_fmt','yuv420p',path])
            out=root/'joined.mp4'; check=join(clips,out,root,'ffmpeg','ffprobe')
            self.assertAlmostEqual(check['Gesamtdauer'],1,delta=.15)
            s.write_metadata('exiftool',out,(dt.datetime(2020,1,2,12,0,tzinfo=s.UTC),(-10.,-20.)))
            for second,channel in (('0.1',0),('0.7',2)):
                frame=root/f'{second}.png'; s.run(['ffmpeg','-v','error','-nostdin','-ss',second,'-i',out,'-frames:v','1',frame])
                with Image.open(frame) as im: pixel=im.convert('RGB').getpixel((10,10))
                self.assertGreater(pixel[channel],200)

@unittest.skipUnless(all(shutil.which(x) for x in ('exiftool','ffmpeg','ffprobe')), 'Requires media tools')
class FullVideoWorkflowTests(unittest.TestCase):
    def test_video_approval_join_import_and_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); rows=[]; entries=[]
            for index,(duration,color) in enumerate(((10,'red'),(1,'blue'))):
                path=root/f'clip{index}.mp4'
                s.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i',f'color=c=black:s=32x48:r=30:d={duration}',
                       '-c:v','libx264','-pix_fmt','yuv420p',path])
                s.run(['exiftool','-overwrite_original','-QuickTime:CreateDate=2020:01:02 12:00:00',path])
                uid=f'00000000-0000-0000-0000-{index+1:012d}'
                stamp=(2020,1,2,12,0,index*10)
                entries.extend([(f'2020-01-02_{uid}-main.mp4',stamp,path.read_bytes()),
                                (f'2020-01-02_{uid}-overlay.png',stamp,picture('RGBA',color))])
                r=row(f'2020-01-02 12:00:{index*10:02d} UTC'); r['Media Type']='Video'; rows.append(r)
            archive(root,entries,rows)
            self.assertEqual(tool.process(args(root)),0)
            videos.propose(root)
            proposal=root/'_Berichte/Videos_Vorschlaege.json'
            doc=json.loads(proposal.read_text()); self.assertEqual(len(doc['Serien']),1)
            with self.assertRaises(ValueError): videos.merge(root)
            doc['Serien'][0]['approved']=True; tool.write_json(proposal,doc)
            videos.merge(root); videos.merge(root)
            tool.prepare_import(root)
            self.assertEqual(len(list((root/'_Import_Jahre/2020').glob('*.mp4'))),2)
            self.assertEqual(len(list((root/'_Ergebnis/2020').glob('*.mp4'))),4)
            output=next((root/'_Import_Jahre/2020').glob('*Mit_Overlay.mp4'))
            for second,channel in (('1',0),('10.5',2)):
                frame=root/f'frame{channel}.png'; s.run(['ffmpeg','-v','error','-nostdin','-ss',second,'-i',output,'-frames:v','1',frame])
                with Image.open(frame) as im: pixel=im.convert('RGB').getpixel((10,10))
                self.assertGreater(pixel[channel],200)
            # New JSON/ZIP provenance must not be accepted against old outputs.
            rows[0]['Date']='2020-01-02 12:00:01 UTC'
            archive(root,entries,rows)
            with self.assertRaises(ValueError): tool.audit(root)

if __name__=='__main__': unittest.main()
