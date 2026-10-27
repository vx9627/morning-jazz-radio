import unittest
from datetime import datetime
from unittest.mock import patch, Mock
from zoneinfo import ZoneInfo
import build
import subprocess
import tempfile
from pathlib import Path


class RadioTests(unittest.TestCase):
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
