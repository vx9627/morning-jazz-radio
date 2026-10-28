# AI 모닝 재즈 라디오 — iPhone 자동 음성 브리핑

매일 07:15 KST 무렵 GitHub Actions가 신도림 날씨와 Google News RSS를 수집합니다. 미국·국내 주식과 업비트 원화 코인 시세를 조회합니다. Gemini API로 정기님을 위한 DJ형 전체 대본을 작성하고, ElevenLabs API에서 한국어 음성을 짧은 구간으로 나누어 생성하여 오리지널 재즈 BGM과 믹싱합니다. 최종 `output/latest.mp3`를 저장하고, iPhone 단축어가 매일 08:00에 URL에서 파일을 받아 재생합니다.

## 1. 계정 준비

- GitHub **새 공개 저장소**를 생성한 뒤 프로젝트 파일을 업로드. `output/latest.mp3`는 누구나 접근할 수 있으므로 개인 일정이나 민감정보를 원고에 넣지 마세요.
- Settings → Secrets and variables → Actions → **Secrets** 에 `ELEVENLABS_API_KEY` 등록. 선택적으로 `GEMINI_API_KEY` 등록. Google AI Pro 구독과 Gemini API 과금은 별개일 수 있습니다. 키를 코드에 절대로 붙여넣지 마세요.
- 같은 화면 **Variables** 에 `ELEVENLABS_VOICE_ID` 등록(자신의 한국어 지원 음성 ID).
- Settings → Actions → General → Workflow permissions → **Read and write permissions** 허용. 필요한 최소 권한만 부여하세요.
- 저장소의 Actions 탭 → `Generate Morning Radio` → `Run workflow` 수동 실행하여 `output/latest.mp3` 생성 확인.
- GitHub 스케줄은 **정확한 시각에 실행된다는 보장이 없으며 지연/누락될 수 있습니다.** 07:15에 시작하도록 여유를 두었습니다.

## 2. 아이폰 단축어

단축어 앱 → `+` → 새 단축어 이름 `Morning Radio`:

1. **URL**: `https://raw.githubusercontent.com/vx9627/morning-jazz-radio/main/output/latest.mp3`
2. **URL 콘텐츠 가져오기**: GET 방식. 결과는 `파일`/이진 데이터
3. **음량 설정**: 처음에는 40%로 시험한 뒤 조절. 워크플로에서 최종 MP3 음량을 보정합니다.
4. **사운드 재생**: 위의 `URL 콘텐츠 가져오기` 결과를 입력

이후 단축어 앱 → 자동화 → `시간` → `08:00` → `매일` → `즉시 실행` → `Morning Radio` 실행. iOS 버전/권한/잠금화면 상태에 따라 기능 명칭이 다를 수 있으며, **잠금 상태에서 재생되는지 반드시 직접 테스트**하세요. 무음/집중 모드/출력 장치 설정을 확인하세요. 이 방식은 긴급 기상 알람을 대체할 만큼 재생이 보장되지 않습니다.

### 잠금 화면 재생 시험

1. 잠금 해제 상태에서 `Morning Radio`를 한 번 직접 실행하고, 네트워크 접근 권한 요청이 나오면 허용합니다.
2. 시험용 시간 자동화를 현재 시각에서 2분 뒤로 만들고 `즉시 실행`으로 설정합니다.
3. Bluetooth 연결과 실제 출력 장치를 확인한 뒤 화면을 잠급니다.
4. 예약 시각에 음성이 나오는지 확인합니다. 성공하면 시험용 자동화를 삭제하고 매일 08:00 자동화를 사용합니다.
5. 재생되지 않으면 잠금을 풀고 같은 단축어를 직접 실행해 네트워크 오류나 권한 요청을 확인합니다.

## 3. 음악과 테스트

`python build.py --demo`를 실행하면 합성 모닝 재즈 25초 테스트 파일 `output/jazz_preview.mp3`가 만들어집니다. 실제 ElevenLabs 음성 믹스는 API 키 입력 후 `python build.py`로 생성합니다. Python 3.11+와 `pip install -r requirements.txt` 필요. FFmpeg는 파이썬 패키지에 포함되어 설치되므로 별도 apt 설치나 ffprobe가 필요하지 않습니다. 믹싱과 음량 보정도 `build.py`에서 수행합니다.

## 기능 및 주의

- 날씨 API: Open-Meteo, 기준 위치 대략 신도림. 뉴스: Google News RSS. RSS 제목은 사실의 전체 내용을 담지 않으며 직접 검증된 본문이 아닙니다.
- Gemini 키가 없으면 RSS 헤드라인을 읽는 **기본 원고**를 사용합니다. ChatGPT Plus 구독이 OpenAI API 이용권을 뜻하지 않으므로 별도 API 키를 요구하지 않도록 설계했습니다.
- 주식: Yahoo Finance의 최근 정규장 시세와 전 거래일 종가를 비교합니다. 미국 3대 지수, 코스피·코스닥, 삼성전자·SK하이닉스를 다룹니다. 공급자 데이터는 지연될 수 있으며, 장중/최근 정규장 및 거래일을 읽습니다.\n- 코인: 업비트 공개 API에서 비트코인·이더리움·수이의 원화 시세를 조회합니다. 등락률은 **업비트 전일 종가 대비**이며 24시간 수익률이 아닙니다. 조회 시세의 기준 시각을 함께 읽습니다.\n- `output/sources.json`에 종목별 가격, 등락률, 기준 시각, 출처, 조회 실패를 보관합니다. 주식은 7일, 코인은 15분보다 오래된 시세를 읽지 않습니다. 실패한 시세는 추정하지 않고 확인하지 못했다고 안내합니다.\n- 숫자·약어는 한국어 발음으로 정규화하고, 순번 낭독과 기사 제목의 괄호·말줄임표·언론사 접미사를 제거합니다. 동일한 음성을 유지하며 안정성 0.75, 속도 0.96으로 생성합니다.\n- API 키 없이 `python build.py --prepare-only`로 실제 뉴스·날씨·시세 원고를 확인할 수 있습니다. `python -m unittest -v test_build.py`로 시세 기준과 원고 처리 검증을 실행합니다.
- 음성 + BGM 파일은 공개 GitHub 저장소에 올라갑니다. 저작권을 침해하지 않도록 BGM은 이 프로젝트에서 생성한 오리지널 합성 패턴입니다.
- ElevenLabs 음성 사용 시 API 크레딧이 소모됩니다. 서비스 사용량/요금제를 점검하세요.
- 공개 저장소가 부담된다면 개인 서버/비공개 인증 미디어 저장소 방식으로 수정해야 합니다.
- 출력 파일이 지난날 것인지 확인하려면 `output/sources.json`의 `generated_at` 필드를 확인하세요. 재생 전 날짜를 검사하는 추가 단축어를 만드는 것도 가능합니다.

## DJ형 대본 검토와 방송 생성

- `RADIO_STYLE.md`의 확정한 인사·톤·마무리 지침을 읽어 **전체** 원고를 작성합니다. `GEMINI_API_KEY`를 GitHub Actions Secret에 등록해야 합니다.
- 수동 `Run workflow`의 기본값은 `preview`입니다. 이 모드는 Gemini만 호출하며 ElevenLabs 키는 전달하지 않습니다. `output/preview.txt`와 `output/preview_sources.json`만 게시합니다.
- `python build.py --prepare-only --require-ai`로 원고만 생성합니다. API 오류나 원고 검증 실패를 기본 원고 성공으로 숨기지 않습니다.
- 사용자가 원고를 확인한 뒤 수동 모드를 `audio`로 선택하면 음성을 생성합니다. 기존 매일 07:15 KST 예약은 방송 생성 모드로 유지됩니다.
- 원고는 가격·등락률·기준 시각을 사실 토큰으로 삽입합니다. 필수 종목 누락·알 수 없는 토큰·토큰을 우회한 숫자·인사 누락·최근 끝인사 반복을 검사합니다. 뉴스 내용의 의미가 원자료를 벗어나지 않는지 검토도 필요합니다.
- `output/closing_history.json`은 최근 30회 방송 마무리를 기록합니다. 대본 검토는 이력을 변경하지 않습니다. 당일 음성을 다시 만들 때는 같은 마무리를 사용합니다.
- 기본 모델이 새 키에서 제공되지 않을 수 있어, API에서 사용 가능한 안정 버전 Flash 모델을 확인합니다. 모델을 고정하려면 GitHub Actions Variable에 `GEMINI_MODEL`을 등록하세요. 실제 사용 모델은 sources의 writer.model에 남깁니다.
