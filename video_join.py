"""Join approved clips, preserving per-clip overlays via pre-rendered inputs."""
import json
from PIL import Image
import snapchat as s

def join(clips,dest,temp,ffmpeg,ffprobe):
    frame=temp/'first.png'
    s.run([ffmpeg,'-v','error','-nostdin','-y','-i',clips[0],'-map','0:v:0','-frames:v','1',frame])
    with Image.open(frame) as im:w,h=im.size
    w+=w%2;h+=h%2
    durations=[];sound=[]
    for p in clips:
        meta=json.loads(s.run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',p]))
        stream=next(x for x in meta['streams'] if x['codec_type']=='video')
        durations.append(float(stream.get('duration',meta['format']['duration'])))
        sound.append(any(x['codec_type']=='audio' for x in meta['streams']))
    cmd=[ffmpeg,'-v','error','-nostdin','-y']
    for p in clips:cmd+=['-i',p]
    filters=[]
    for i,duration in enumerate(durations):
        filters.append(f'[{i}:v:0]setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v{i}]')
        if sound[i]:filters.append(f'[{i}:a:0]asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration}[a{i}]')
        else:filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration={duration}[a{i}]')
    filters.append(''.join(f'[v{i}][a{i}]' for i in range(len(clips)))+f'concat=n={len(clips)}:v=1:a=1[v][a]')
    s.run(cmd+['-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-map_metadata','-1','-c:v','libx264','-crf','16','-preset','medium','-c:a','aac','-b:a','192k','-metadata:s:v:0','rotate=0','-movflags','+faststart',dest])
    check=json.loads(s.run([ffprobe,'-v','error','-show_format','-of','json',dest]))
    actual=float(check['format']['duration'])
    if abs(actual-sum(durations))>max(.3,len(clips)*.06):raise RuntimeError('Zusammengesetzte Laufzeit weicht unerwartet ab')
    return dict(Clipdauer=durations,Gesamtdauer=actual,Schnittpunkte=[round(sum(durations[:i]),3) for i in range(1,len(clips))])
