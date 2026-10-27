#!/usr/bin/env python3
"""Morning Radio: no paid dependencies other than optional Gemini and ElevenLabs APIs."""
import os, json, math, wave, random, subprocess, re, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
import requests

ROOT=Path(__file__).parent
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
NOW=datetime.now(ZoneInfo('Asia/Seoul'))
HEADERS={'User-Agent':'MorningRadio/1.0 (+personal RSS reader)'}

def get_json(url, params=None):
    res=requests.get(url, params=params, headers=HEADERS, timeout=25);res.raise_for_status();return res.json()

def weather():
    # Approximate fixed reference points rather than precise device location.
    names={'신도림':(37.5087,126.891), '부천':(37.5035,126.766)}
    results={}
    for name,(lat,lon) in names.items():
        d=get_json('https://api.open-meteo.com/v1/forecast', {'latitude':lat,'longitude':lon,'timezone':'Asia/Seoul', 'current':'temperature_2m,precipitation,weather_code', 'daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','forecast_days':1})
        results[name]={'현재기온':d['current']['temperature_2m'],'현재강수mm':d['current']['precipitation'],'날씨코드':d['current']['weather_code'],'최고기온':d['daily']['temperature_2m_max'][0],'최저기온':d['daily']['temperature_2m_min'][0],'최대강수확률':d['daily']['precipitation_probability_max'][0]}
    return results

def headlines():
    sources=[('주요뉴스','https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko'),('국제','https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko'),('비즈니스','https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko'),('과학기술','https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko')]
    items=[];used=set()
    for section,url in sources:
        try:
            r=requests.get(url,headers=HEADERS,timeout=25);r.raise_for_status();root=ET.fromstring(r.content)
            for item in root.findall('.//item')[:10]:
                title=' '.join((item.findtext('title') or '').split());link=item.findtext('link') or '';pub=item.findtext('pubDate') or ''
                if not title or title in used:continue
                used.add(title);items.append({'분야':section,'제목':title,'발행':pub,'출처':link})
        except Exception as exc:print(f'RSS {section}: {exc}',file=sys.stderr)
    return items[:32]

def fallback_script(w,news):
    day=NOW.strftime('%Y년 %m월 %d일')
    intro=f'좋은 아침입니다. {day}, 오늘의 모닝 라디오입니다. '
    parts=[intro]
    for city,d in w.items():
        parts.append(f'{city} 현재 기온은 {d["현재기온"]}도, 오늘 최고 {d["최고기온"]}도, 최저 {d["최저기온"]}도입니다. 최대 강수 확률은 {d["최대강수확률"]}퍼센트입니다. ')
    parts.append('이어서 확인된 주요 기사 제목입니다. 제목만으로 세부 사실을 단정하지 않고 전해 드립니다. ')
    for i,n in enumerate(news[:6],1):parts.append(f'{i}번째, {n["제목"]}. ')
    parts.append('오늘도 좋은 하루 보내세요.')
    return ''.join(parts)

def script_with_gemini(w,news):
    key=os.environ.get('GEMINI_API_KEY','')
    if not key:return fallback_script(w,news)
    model=os.environ.get('GEMINI_MODEL','gemini-2.5-flash')
    prompt=(f'한국시간 {NOW.isoformat()} 기준 한국어 아침 라디오 원고를 작성해줘. 2~3분 분량, 차분하고 상쾌한 어투, 시작에 날짜, 신도림/부천 날씨와 출근 복장 조언, 이후 중요도순 뉴스 최대 5개, AI 및 반도체 관련 소식, 마무리. '
       '입력 데이터는 날씨 관측/예보와 RSS 기사 제목 및 발행일뿐이므로, 제목에서 확정할 수 없는 사실/수치/원인/실시간 주가를 지어내지 말 것. 제목으로 확인되지 않는 미국 증시 종가도 추정하지 말 것. 비슷한 기사는 합치고 오래된 기사는 배제할 것. '
       '음성 전용으로 부호와 표 없이 문장만 작성. 입력 데이터에 없으면 없다고 말할 것.\n'
       f'날씨: {json.dumps(w,ensure_ascii=False)}\n기사: {json.dumps(news,ensure_ascii=False)}')
    res=requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',params={'key':key},json={'contents':[{'parts':[{'text':prompt}]}],'generationConfig':{'temperature':0.3,'maxOutputTokens':1800}},timeout=75)
    res.raise_for_status()
    text=''.join(x.get('text','') for x in res.json()['candidates'][0]['content']['parts']).strip()
    if not text:raise RuntimeError('Gemini returned empty response')
    return text

def make_jazz_wav(path,seconds=32,sr=22050):
    """Original synthesized morning-jazz instrumental loop: soft keys, walking bass, light shaker."""
    import array
    rng=random.Random(27)
    # Cmaj7, Am7, Dm7, G7. Swingy chord comping and bass; intentionally simple royalty-free original.
    chords=[[261.63,329.63,392,493.88],[220,261.63,329.63,392],[293.66,349.23,440,523.25],[196,246.94,349.23,392]]
    bass=[130.81,110,146.83,98]
    frames=array.array('h');total=int(seconds*sr)
    for i in range(total):
        t=i/sr;bar=int(t//3.2)%4;bt=t%3.2
        v=0.0
        # 4/4 lightly swinging, each bar 3.2s.
        for j,fr in enumerate(chords[bar]):
            for onset in (0,1.17,2.4):
                age=bt-onset
                if 0<=age<0.68:
                    env=(1-math.exp(-age*40))*math.exp(-age*6.5)
                    v+=0.055*env*math.sin(2*math.pi*fr*age+0.1*j)
        pulse=int(bt//0.8);age=bt-pulse*0.8;f=bass[bar]*(2 if pulse==3 else 1)
        v+=0.13*math.exp(-age*6)*math.sin(2*math.pi*f*age)
        # brushed shaker, pitched noise
        hp=t%0.4
        if hp<0.042:
            v+=0.013*rng.uniform(-1,1)*(1-hp/0.042)
        fade=min(1,t/1.6,(seconds-t)/2.0)
        frames.append(max(-32767,min(32767,int(v*32767*max(0,fade)))))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(frames.tobytes())

def voice_tts(script,path):
    key=os.getenv('ELEVENLABS_API_KEY');voice=os.getenv('ELEVENLABS_VOICE_ID')
    if not key or not voice:raise RuntimeError('ELEVENLABS_API_KEY와 ELEVENLABS_VOICE_ID를 설정해야 실제 음성을 생성할 수 있습니다.')
    res=requests.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}',params={'output_format':'mp3_44100_128'},headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg'},json={'text':script[:4900],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.55,'similarity_boost':0.75}},timeout=120)
    res.raise_for_status();path.write_bytes(res.content)

def mix(voice,music,out):
    # Gentle music bed ~ -23dB relative to original, intro 4s; looping music under all speech.
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','-1','-i',str(music),'-i',str(voice),'-filter_complex',
         '[0:a]volume=0.20[bg];[1:a]adelay=4000|4000,volume=1.0[vo];[bg][vo]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.95[m]',
         '-map','[m]','-t',str(round(duration(voice)+8,2)),'-codec:a','libmp3lame','-b:a','160k',str(out)]
    subprocess.run(cmd,check=True)

def duration(audio):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nokey=1:noprint_wrappers=1',str(audio)],text=True).strip())

def main():
    demo='--demo' in sys.argv
    music=OUT/'morning_jazz.wav';make_jazz_wav(music)
    if demo:
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(music),'-t','25','-codec:a','libmp3lame',str(OUT/'jazz_preview.mp3')],check=True)
        print('Preview ready:',OUT/'jazz_preview.mp3');return
    w=weather();news=headlines()
    if not news:raise RuntimeError('뉴스 피드를 가져오지 못해 오래된 브리핑 덮어쓰기를 중단합니다.')
    script=script_with_gemini(w,news)
    (OUT/'latest.txt').write_text(script,encoding='utf-8')
    (OUT/'sources.json').write_text(json.dumps({'generated_at':NOW.isoformat(),'weather':w,'articles':news},ensure_ascii=False,indent=2),encoding='utf-8')
    voice=OUT/'voice.mp3';voice_tts(script,voice)
    mix(voice,music,OUT/'latest.mp3')
    print('Generated:',OUT/'latest.mp3', 'duration:',duration(OUT/'latest.mp3'))

if __name__=='__main__':main()
