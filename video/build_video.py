"""Build MiniQuant's chaptered, approximately 30-minute Chinese video.

Inputs: scenes.json and figs/*.png. Outputs: MP4, SRT, narration, chapters.
Uses the configured quant environment's edge-tts and ffmpeg; no brokerage data.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
SCENES=json.loads((ROOT/'scenes.json').read_text())
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
FONT=ROOT/'assets'/'NotoSansCJKsc-Regular.otf'
EDGE_TTS=os.environ.get('MINIQUANT_EDGE_TTS','edge-tts')
FFMPEG=os.environ.get('MINIQUANT_FFMPEG','ffmpeg')
FFPROBE=os.environ.get('MINIQUANT_FFPROBE','ffprobe')
PROXY=os.environ.get('MINIQUANT_TTS_PROXY')
VOICE=os.environ.get('MINIQUANT_TTS_VOICE','zh-CN-XiaoxiaoNeural')
RATE=os.environ.get('MINIQUANT_TTS_RATE','-5%')
def run(*args):subprocess.run([str(a) for a in args],check=True)
def font(size):return ImageFont.truetype(str(FONT),size)
def duration(path):
    raw=subprocess.check_output([str(FFPROBE),'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)])
    return float(raw)
def stamp(t):
    n=round(t*1000);h,n=divmod(n,3600000);m,n=divmod(n,60000);s,n=divmod(n,1000)
    return f'{h:02}:{m:02}:{s:02},{n:03}'
def seconds(t):
    h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
def slide(scene,idx):
    if scene.get('figure'):
        figure=PROJECT/scene['figure']
        if not figure.is_file():raise FileNotFoundError(figure)
        im=Image.open(figure).convert('RGB').resize((1280,720),Image.Resampling.LANCZOS)
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((1108,24,1250,68),radius=10,fill='#132c4c')
        d.text((1120,30),f'{idx:02}/{len(SCENES):02}',font=font(23),fill='white')
        return im
    im=Image.new('RGB',(1280,720),'#0d1729');d=ImageDraw.Draw(im)
    d.rounded_rectangle((38,28,1242,692),radius=26,fill='#14243c',outline='#355171',width=2)
    for x,color in [(66,'#f37871'),(94,'#f6c66f'),(122,'#78cfad')]:d.ellipse((x,57,x+17,74),fill=color)
    d.text((68,105),scene['chapter'],font=font(25),fill='#81c5d4')
    d.text((68,148),scene['title'],font=font(45),fill='#f2f6fb')
    d.line((68,218,1210,218),fill='#42607d',width=2)
    for j,line in enumerate(scene['terminal']):
        d.text((78,263+j*80),line,font=font(30),fill='#d8e8f3')
    d.rounded_rectangle((66,575,1214,655),radius=14,fill='#183f51')
    d.text((84,596),'要点',font=font(26),fill='#8bd8cf')
    d.text((156,596),scene['takeaway'],font=font(26),fill='#f4e4ac')
    d.text((1110,40),f'{idx:02}/{len(SCENES):02}',font=font(20),fill='#9baec5')
    return im
def short_captions(start, end, caption, limit=28):
    caption=''.join(caption.splitlines())
    if not caption:return []
    pieces=[caption[i:i+limit] for i in range(0,len(caption),limit)]
    span=max(end-start,0.1)
    total=sum(len(x) for x in pieces)
    cursor=start
    out=[]
    for i,piece in enumerate(pieces):
        stop=end if i==len(pieces)-1 else cursor+span*len(piece)/total
        out.append((cursor,stop,piece))
        cursor=stop
    return out

def read_srt(path):
    text=path.read_text().strip()
    for block in re.split(r'\n\s*\n',text):
        lines=block.splitlines()
        time_idx=next((i for i,line in enumerate(lines) if '-->' in line),None)
        if time_idx is None:continue
        start,end=[seconds(x.strip()) for x in lines[time_idx].split('-->')]
        content='\n'.join(lines[time_idx+1:]).strip()
        if content:yield start,end,content

def main():
    if not 25<=len(SCENES)<=60:raise ValueError('Expected a chaptered long-form script')
    all_subs=[];segments=[];chapter_times=[];cursor=0.0;current_chapter=None
    for idx,scene in enumerate(SCENES,1):
        if scene['chapter']!=current_chapter:
            chapter_times.append((scene['chapter'],cursor));current_chapter=scene['chapter']
        png=OUT/f'scene_{idx:02}.png';mp3=OUT/f'scene_{idx:02}.mp3';local_srt=OUT/f'scene_{idx:02}.srt';part=OUT/f'scene_{idx:02}.mp4'
        slide(scene,idx).save(png)
        narration=scene['narration']
        fingerprint=hashlib.sha256(f'{VOICE}|{RATE}|{narration}'.encode()).hexdigest()
        marker=OUT/f'scene_{idx:02}.sha256'
        if not(mp3.exists() and local_srt.exists() and marker.exists() and marker.read_text()==fingerprint):
            tts_args=[EDGE_TTS,'--voice',VOICE,f'--rate={RATE}','--text',narration]
            if PROXY: tts_args.extend(['--proxy',PROXY])
            run(*tts_args,'--write-media',mp3,'--write-subtitles',local_srt)
            marker.write_text(fingerprint)
        audio_len=duration(mp3)
        scene_len=audio_len+0.45
        run(FFMPEG,'-y','-loglevel','error','-loop','1','-framerate','1','-i',png,'-i',mp3,'-t',str(scene_len),
            '-vf','fps=25,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','22','-r','25','-c:a','aac','-b:a','112k','-af','apad',part)
        segments.append(part)
        for start,end,caption in read_srt(local_srt):
            all_subs.extend((cursor+a,cursor+b,text) for a,b,text in short_captions(start,min(end,audio_len),caption))
        cursor+=duration(part)
        print(f'{idx:02}/{len(SCENES):02} {scene["title"]}: {audio_len:.1f}s',flush=True)
    concat=OUT/'concat.txt';concat.write_text(''.join(f"file '{x}'\n" for x in segments))
    raw=OUT/'MiniQuant_30min_raw.mp4'
    run(FFMPEG,'-y','-loglevel','error','-f','concat','-safe','0','-i',concat,'-c','copy',raw)
    srt=ROOT/'MiniQuant_30min.srt'
    srt.write_text('\n'.join(f'{i}\n{stamp(start)} --> {stamp(max(end,start+0.1))}\n{caption}\n' for i,(start,end,caption) in enumerate(all_subs,1)))
    meta=OUT/'chapters.ffmeta';chunks=[';FFMETADATA1\n','title=MiniQuant：从零到量化研究与500元操作实验\n']
    for j,(name,start) in enumerate(chapter_times):
        end=chapter_times[j+1][1] if j+1<len(chapter_times) else cursor
        chunks.append(f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start*1000)}\nEND={round(end*1000)}\ntitle={name}\n')
    meta.write_text(''.join(chunks))
    final=ROOT/'MiniQuant_30min.mp4';tmp=OUT/'MiniQuant_30min_final.mp4'
    run(FFMPEG,'-y','-loglevel','error','-i',raw,'-i',srt,'-i',meta,'-map','0:v:0','-map','0:a:0','-map','1:0',
        '-map_metadata','2','-map_chapters','2','-c:v','copy','-c:a','copy','-c:s','mov_text','-metadata:s:s:0','language=chi','-movflags','+faststart',tmp)
    if duration(tmp)<27*60:raise RuntimeError(f'Video too short: {duration(tmp):.1f}s; expand script before publishing')
    os.replace(tmp,final)
    (ROOT/'narration.txt').write_text('\n\n'.join(f"{x['chapter']} · {x['title']}\n{x['narration']}" for x in SCENES)+'\n')
    (ROOT/'CHAPTERS.md').write_text('# MiniQuant 长版视频章节\n\n'+''.join(f'- {int(t//60):02}:{int(t%60):02}　{name}\n' for name,t in chapter_times)+f'\n总时长：{duration(final)/60:.1f} 分钟。\n')
    print(f'BUILT {final} seconds={duration(final):.2f} bytes={final.stat().st_size} subtitles={len(all_subs)} chapters={len(chapter_times)}',flush=True)
    if os.environ.get('MINIQUANT_KEEP_BUILD')!='1':shutil.rmtree(OUT)
if __name__=='__main__':main()
