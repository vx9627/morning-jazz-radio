# AI 모닝 재즈 라디오 — iPhone 자동 음성 브리핑

매일 07:15 KST 무렵 GitHub Actions가 신도림·부천 날씨와 Google News RSS를 수집합니다. 선택적으로 Gemini API로 2~3분 원고를 요약하고, ElevenLabs API에서 한국어 음성을 생성하여 오리지널 재즈 BGM과 믹싱합니다. 최종 `output/latest.mp3`를 저장하고, iPhone 단축어가 매일 08:00에 URL에서 파일을 받아 재생합니다.

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

`python build.py --demo`를 실행하면 합성 모닝 재즈 25초 테스트 파일 `output/jazz_preview.mp3`가 만들어집니다. 실제 ElevenLabs 음성 믹스는 API 키 입력 후 `python build.py`로 생성합니다. Python 3.11+, `ffmpeg`, `ffprobe`, `pip install -r requirements.txt` 필요.

## 기능 및 주의

- 날씨 API: Open-Meteo, 기준 위치 대략 신도림·부천. 뉴스: Google News RSS. RSS 제목은 사실의 전체 내용을 담지 않으며 직접 검증된 본문이 아닙니다.
- Gemini 키가 없으면 RSS 헤드라인을 읽는 **기본 원고**를 사용합니다. ChatGPT Plus 구독이 OpenAI API 이용권을 뜻하지 않으므로 별도 API 키를 요구하지 않도록 설계했습니다.
- 이 프로젝트는 변동되는 시장 데이터를 검증된 시세 API에서 조회하지 않습니다. 시세를 임의로 말하지 않도록 설계했습니다.
- 음성 + BGM 파일은 공개 GitHub 저장소에 올라갑니다. 저작권을 침해하지 않도록 BGM은 이 프로젝트에서 생성한 오리지널 합성 패턴입니다.
- ElevenLabs 음성 사용 시 API 크레딧이 소모됩니다. 서비스 사용량/요금제를 점검하세요.
- 공개 저장소가 부담된다면 개인 서버/비공개 인증 미디어 저장소 방식으로 수정해야 합니다.
- 출력 파일이 지난날 것인지 확인하려면 `output/sources.json`의 `generated_at` 필드를 확인하세요. 재생 전 날짜를 검사하는 추가 단축어를 만드는 것도 가능합니다.
