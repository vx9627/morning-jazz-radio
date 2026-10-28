import unittest
from datetime import datetime
from unittest.mock import patch, Mock
from zoneinfo import ZoneInfo
import build
import subprocess
import tempfile
import json
from pathlib import Path


class RadioTests(unittest.TestCase):
    def test_saved_preview_preserves_script_and_rejects_stale_facts(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(build,'OUT',Path(temp)):
            script='정기님, 좋은 아침이에요. 저장한 대본이에요.'
            (build.OUT/'preview.txt').write_text(script,encoding='utf-8')
            meta={'generated_at':build.NOW.isoformat(),'writer':{'engine':'gemini'}}
            (build.OUT/'preview_sources.json').write_text(json.dumps(meta),encoding='utf-8')
            with patch.object(build.requests,'post',side_effect=AssertionError('No regeneration')):
                self.assertEqual(build.saved_preview()[0]['script'],script)
            meta['generated_at']=(build.NOW-build.timedelta(hours=3)).isoformat()
            (build.OUT/'preview_sources.json').write_text(json.dumps(meta),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'older than two hours'):build.saved_preview()

    def writer_fixture(self):
        weather={'신도림':{'현재기온':3.6,'최저기온':1.9,'최고기온':10.9,'최대강수확률':0}}
        news=[{'분야':'주요뉴스','제목':'주민 2명 구조 - 보도사'},{'분야':'국제','제목':'국제 회의 개최 - 보도사'}]
        quotes=[]
        for group,name,symbol in [('미국','나스닥','^IXIC'),('국내','코스피','^KS11'),('종목','삼성전자','005930.KS'),('코인','비트코인','KRW-BTC')]:
            quotes.append({'group':group,'name':name,'symbol':symbol,'session_date':'2026-10-27','session_state':'장중','price':1234.5,'change_pct':-1.23,'as_of':'2026-10-28T03:30:00+09:00'})
        tokens,required,data=build.writer_facts(weather,news,{'quotes':quotes,'errors':[]})
        draft={s:' '.join('{{'+key+'}}' for key in sorted(required[s])) for s in build.WRITER_SECTIONS}
        draft['opening']='정기님, 좋은 아침이에요. {{date}}, 모닝 재즈 라디오입니다. 편안한 재즈와 함께 하루를 시작해 볼까요.'
        draft['weather']='신도림 날씨부터 챙겨볼게요. '+draft['weather']+' 아침저녁으로 걸칠 겉옷을 챙겨두시면 좋겠네요. 밖에 나서실 때 따뜻하게 준비해 주세요.'
        draft['news']='기사 제목을 기준으로 전해 드릴게요. 주민 {{n0.v0}}이 구조됐다는 소식이 전해졌어요. 자세한 후속 소식도 함께 확인해 보시면 좋겠습니다.'
        draft['us']='이제 미국 시장 흐름을 살펴볼까요. '+draft['us']+'한 모습이에요. 미국 시장의 거래일과 장중 여부를 함께 확인해 주세요.'
        draft['korea']='국내 증시로 넘어가 볼게요. '+draft['korea']+'한 수치예요. 거래일 기준의 흐름을 차분하게 살펴보시면 좋겠습니다.'
        draft['stocks']='반도체 종목도 함께 챙겨보죠. '+draft['stocks']+'한 모습인데요. 기준 시점과 주가를 함께 전해 드렸어요.'
        draft['crypto']='끝으로 코인 시장입니다. '+draft['crypto']+'한 수치예요. 업비트 전일 종가와 비교한 흐름으로 살펴봤어요.'
        draft['closing']='작은 쉼표가 다음 걸음을 가볍게 해주기도 해요. 정기님, 오늘은 잠깐의 여유도 챙겨보세요.'
        draft['news_ids']=[0]
        return tokens,required,data,draft

    def test_ai_writer_binds_facts_and_rejects_missing_or_invented_numbers(self):
        tokens,required,data,draft=self.writer_fixture()
        result=build.validate_writer(draft,tokens,required,data['articles'],[])
        self.assertTrue(result['script'].startswith('정기님, 좋은 아침이에요.'))
        self.assertNotIn('{{',result['script'])
        self.assertIn('두 명',result['script'])
        alias=dict(draft);alias['us']+=' S&P 500 지수도 함께 살펴봤어요.'
        self.assertNotIn('S&P 500',build.validate_writer(alias,tokens,required,data['articles'],[])['script'])
        particles=dict(draft);particles['crypto']+=' {{q3.price}}를 확인했어요.'
        self.assertIn('원'+ '을 확인했어요',build.validate_writer(particles,tokens,required,data['articles'],[])['script'])
        missing=dict(draft);missing['stocks']=missing['stocks'].replace('{{q2.change}}','')
        with self.assertRaisesRegex(ValueError,'Missing required'):
            build.validate_writer(missing,tokens,required,data['articles'],[])
        wrong=dict(draft);wrong['weather']+=' 오늘 99도예요.'
        with self.assertRaisesRegex(ValueError,'bypassed'):
            build.validate_writer(wrong,tokens,required,data['articles'],[])

    def test_ai_writer_checks_recent_closings_and_same_day_reuse(self):
        tokens,required,data,draft=self.writer_fixture()
        yesterday=(build.NOW.date()-build.timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'repeats'):
            build.validate_writer(draft,tokens,required,data['articles'],[{'date':yesterday,'closing':draft['closing']}])
        with self.assertRaisesRegex(ValueError,'same closing'):
            build.validate_writer(draft,tokens,required,data['articles'],[{'date':build.NOW.date().isoformat(),'closing':'오늘 이미 사용한 다른 인사예요. 정기님, 편안한 하루 보내세요.'}])

    def test_preview_never_generates_audio_or_changes_live_output_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            for name in ('latest.mp3','latest.txt','sources.json','closing_history.json'):
                (out/name).write_bytes(b'unchanged')
            draft={'script':'정기님, 좋은 아침이에요. 오늘의 검토용 원고예요.','engine':'gemini','closing':'정기님, 좋은 하루 보내세요.','model':'test'}
            with patch.object(build,'OUT',out),patch.object(build.sys,'argv',['build.py','--prepare-only','--require-ai']),patch.object(build,'weather',return_value={}),patch.object(build,'headlines',return_value=[{}]),patch.object(build,'markets',return_value={}),patch.object(build,'script_with_gemini',return_value=draft),patch.object(build,'voice_tts') as voice,patch.object(build,'make_jazz_wav') as music,patch('builtins.print'):
                build.main()
            voice.assert_not_called();music.assert_not_called()
            for name in ('latest.mp3','latest.txt','sources.json','closing_history.json'):
                self.assertEqual((out/name).read_bytes(),b'unchanged')
            self.assertFalse(json.loads((out/'preview_sources.json').read_text())['speech']['generated'])
            self.assertEqual((out/'preview.txt').read_text(),draft['script'])

    def test_new_key_selects_an_available_stable_model(self):
        response=Mock(ok=True);response.json.return_value={'models':[{'name':'models/gemini-2.5-flash','supportedGenerationMethods':['generateContent']},{'name':'models/gemini-3.8-flash','supportedGenerationMethods':['generateContent']}]}
        with patch.dict(build.os.environ,{'GEMINI_MODEL':''}),patch.object(build.requests,'get',return_value=response):
            self.assertEqual(build.gemini_model('test-key'),'gemini-3.8-flash')

    def test_transient_provider_failure_gets_one_bounded_retry(self):
        unavailable=Mock(ok=False,status_code=503);success=Mock(ok=True)
        with patch.object(build.requests,'post',side_effect=[unavailable,success]) as post,patch.object(build.time,'sleep'),patch('builtins.print'):
            self.assertIs(build.post_gemini('test-key','gemini-3.8-flash',{}),success)
            self.assertEqual(post.call_count,2)
        unauthorized=Mock(ok=False,status_code=403)
        with patch.object(build.requests,'post',return_value=unauthorized) as post,self.assertRaisesRegex(RuntimeError,'HTTP 403'):
            build.post_gemini('test-key','gemini-3.8-flash',{})
        self.assertEqual(post.call_count,1)

    def test_bundled_audio_tools_decode_and_mix_real_mp3(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            voice=root/'voice.mp3';music=root/'music.wav';out=root/'mixed.mp3'
            subprocess.run([build.FFMPEG,'-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=1','-codec:a','libmp3lame',str(voice)],check=True)
            build.make_jazz_wav(music,seconds=2)
            build.mix(voice,music,out)
            self.assertAlmostEqual(build.duration(voice),1.04,delta=0.08)
            self.assertAlmostEqual(build.duration(out),9.04,delta=0.08)

    def test_numbers_are_written_for_korean_speech(self):
        self.assertEqual(build.korean_integer(107375000), '일억 칠백삼십칠만 오천')
        self.assertEqual(build.spoken_number(-3.6), '영하 삼 점 육')
        self.assertEqual(build.spoken_number(1.995, 2), '이')
        self.assertEqual(build.movement(-0.004), '보합입니다')
        self.assertEqual(build.subject('수이'), '수이는')
        self.assertEqual(build.subject('비트코인'), '비트코인은')
        self.assertEqual(build.speech_text('30대 1명 부상, 대응 1단계'), '삼십대 한 명 부상, 대응 일 단계')
        self.assertEqual(build.speech_text('20명 대피'), '스무 명 대피')

    def test_script_has_one_weather_and_required_markets_without_ordinals(self):
        weather={'신도림':{'현재기온':3.6,'최저기온':1.9,'최고기온':10.9,'최대강수확률':0}}
        news=[{'분야':'주요뉴스','제목':'[종합] 주민 100명 대피…화재 진화 - 연합뉴스'},
              {'분야':'국제','제목':'주요국 회의 개최 - 보도사'},
              {'분야':'과학기술','제목':'AI 반도체 개발 - 보도사'}]
        quotes=[]
        for group,name,symbol in [('미국','나스닥','^IXIC'),('국내','코스피','^KS11'),('종목','삼성전자','005930.KS'),('코인','비트코인','KRW-BTC')]:
            quotes.append({'group':group,'name':name,'symbol':symbol,'session_date':'2026-10-27','session_state':'장중','price':1234.5,'change_pct':-1.23,'as_of':'2026-10-28T03:30:00+09:00'})
        script=build.fallback_script(weather,news,{'quotes':quotes,'errors':[]})
        for text in ['부천','번째','연합뉴스','…','[종합]']:
            self.assertNotIn(text,script)
        for text in ['신도림','나스닥','코스피','삼성전자','비트코인','장중','전 거래일 종가','업비트 전일 종가']:
            self.assertIn(text,script)
        self.assertTrue(all(len(x)<=650 for x in build.speech_chunks(script)))
        self.assertFalse(any(c.isdigit() for x in build.speech_chunks(script) for c in x))

    def test_daily_history_uses_previous_exchange_date_and_labels_intraday(self):
        zone=ZoneInfo('America/New_York')
        quote_time=datetime(2026,10,27,14,0,tzinfo=zone)
        previous=datetime(2026,10,26,9,30,tzinfo=zone)
        current=datetime(2026,10,27,9,30,tzinfo=zone)
        result={'meta':{'symbol':'^GSPC','regularMarketTime':int(quote_time.timestamp()),'regularMarketPrice':110,'exchangeTimezoneName':'America/New_York','currentTradingPeriod':{'regular':{'start':int(current.timestamp()),'end':int(datetime(2026,10,27,16,0,tzinfo=zone).timestamp())}}},'timestamp':[int(previous.timestamp()),int(current.timestamp())],'indicators':{'quote':[{'close':[100,110]}]}}
        response=Mock();response.json.return_value={'chart':{'result':[result]}}
        with patch.object(build,'NOW',quote_time),patch.object(build.requests,'get',return_value=response):
            quote=build.yahoo_quote('^GSPC','에스앤피 오백','미국')
        self.assertAlmostEqual(quote['change_pct'],10)
        self.assertEqual(quote['session_state'],'장중')
        self.assertEqual(quote['session_date'],'2026-10-27')

    def test_stale_stock_data_is_rejected(self):
        result={'meta':{'symbol':'^GSPC','regularMarketTime':0,'regularMarketPrice':110}}
        response=Mock();response.json.return_value={'chart':{'result':[result]}}
        with patch.object(build.requests,'get',return_value=response),self.assertRaisesRegex(ValueError,'stale'):
            build.yahoo_quote('^GSPC','에스앤피 오백','미국')

    def test_missing_data_is_disclosed_without_inventing_prices(self):
        text=build.market_script({'quotes':[],'errors':[{'name':'network'}]})
        self.assertIn('미국 증시 시세를 확인하지 못했습니다',text)
        self.assertIn('코인 시세는 확인하지 못했습니다',text)
        self.assertNotIn('올랐습니다',text)


if __name__=='__main__':
    unittest.main()
