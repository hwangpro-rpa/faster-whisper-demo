# voice-grader-demo

STT(faster-whisper, CPU) + 규칙 기반 발음 채점 데모. 단어/문장(한국어·영어)을 화면에 보여주고
녹음하면, 인식된 텍스트와 어떤 부분이 왜 틀렸는지에 대한 피드백을 보여줍니다.

## 구조

- `app/main.py` — FastAPI 서버. `/api/items`, `/api/grade` 제공, `static/`을 서빙.
- `app/grader.py` — 채점 로직. `Grader` 인터페이스에 `HeuristicGrader`(규칙 기반, API 불필요)와
  `ClaudeGrader`(Anthropic API)가 있음. `ANTHROPIC_API_KEY` 환경변수가 있으면 자동으로
  `ClaudeGrader`로 전환됩니다 (`get_grader()`).
- `app/items.py` — 데모용 단어/문장 목록. `hotwords_for(language)`가 인식 정확도를 위한 어휘 힌트도 만듦.
- `app/audio_prep.py` — 인식 전 오디오 정규화(피크 노멀라이즈).
- `static/index.html` — 프론트엔드 (바닐라 JS, 빌드 불필요).

## 실행

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8421
```

첫 실행 시 `small` whisper 모델을 huggingface에서 자동 다운로드합니다 (인터넷 필요, 이후는 캐시 사용).

브라우저에서 `http://localhost:8421` 접속.

## 환경변수 (`.env.example` 참고)

`app/main.py`가 시작할 때 `.env` 파일을 자동으로 읽습니다 (`python-dotenv`). 프로젝트 루트에
`.env`를 만들면 됩니다 (`.gitignore`에 이미 포함되어 있어 커밋되지 않음):

```bash
cp .env.example .env
```

- `ANTHROPIC_API_KEY` — 설정하면 Claude 기반 채점으로 자동 전환.
- `DEMO_TOKEN` — 설정하면 `/api/grade` 요청에 동일한 `token`이 없으면 401.
  **외부에 공개할 때는 반드시 설정할 것** (안 그러면 아무나 CPU에 whisper job을 돌릴 수 있음).
  프론트엔드는 URL에 `?token=값`을 한 번 붙여서 열면 그 값을 브라우저 localStorage에 저장해두고
  이후 모든 요청에 자동으로 실어 보냅니다 — 즉 터널 URL을
  `https://xxxx.trycloudflare.com/?token=값` 형태로 공유하면 됨.
- `WHISPER_MODEL_SIZE` — `tiny`/`base`/`small`(기본)/`medium`. `medium`은 인식이 더 정확할 수 있지만
  4코어 i3 CPU 기준 짧은 문장 하나에 약 14초가 걸려 데모용으로는 느립니다. 속도보다 정확도가
  급하지 않다면 시도해볼 수 있는 정도.

## Cloudflare Tunnel로 외부 노출

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8421
```

출력되는 `https://xxxx.trycloudflare.com` 주소가 외부 접근용 URL입니다 (임시 터널, 재시작마다 URL 바뀜).
공개 전에 `DEMO_TOKEN`을 설정하고, 프론트엔드 요청에 해당 토큰을 넣도록 조정하세요.

## 인식 정확도를 위해 적용한 것들

- **마이크 캡처**: `getUserMedia`에 `echoCancellation`/`noiseSuppression`/`autoGainControl`/16kHz를
  명시적으로 요청하고, `MediaRecorder`도 128kbps로 녹음해 압축 손실을 줄임 (기존엔 브라우저 기본값에
  맡겨서 기기마다 품질이 들쭉날쭉했음).
- **정규화**: 서버에서 디코드한 오디오를 피크 기준으로 정규화(`app/audio_prep.py`). 조용하게 녹음된
  클립의 인식률을 높여줌.
- **hotwords**: 현재 문제의 정답이 아니라, 데모에 있는 모든 단어/문장 텍스트를 `hotwords`로 넘겨서
  Whisper가 이 도메인 어휘를 더 잘 알아듣도록 함 (정답을 알려주는 게 아니라 "이런 단어들이 나올 수
  있다"는 힌트라 채점 의미가 훼손되지 않음).
- **시도했지만 뺀 것 — 노이즈 제거**: `noisereduce` 스펙트럼 노이즈 제거를 붙여봤는데, 깨끗한 짧은
  클립에서는 오히려 음성 에너지 자체를 깎아먹어서 결과가 더 나빠졌습니다 (0.6초짜리 "light" 녹음이
  정규화만 했을 때는 정확히 인식됐는데, 노이즈 제거까지 하니 "Thank you for watching and see you in
  the next video" 같은 완전한 환각으로 바뀜). 실제 배경 소음이 있는 녹음으로 재검증하기 전에는
  다시 넣지 마세요.

## 알려진 한계

- 1음절짜리 아주 짧은 고립 단어(예: "rice")는 여전히 불안정할 수 있습니다 — Whisper는 문맥이 있는
  발화에 최적화돼 있어서, 위 개선을 다 적용해도 극단적으로 짧은 단어는 근본적인 한계가 남습니다.
  문장 단위, 그리고 2음절 이상 단어는 위 개선 이후 눈에 띄게 안정적입니다.
- `HeuristicGrader`는 텍스트 diff 기반이라 실제 억양/음향 품질은 평가하지 못하고, 자주 틀리는
  발음 패턴(r/l, f/p 등)에 대한 추정 가이드만 제공합니다. 진짜 음향 기반 발음 평가가 필요하면
  Azure Pronunciation Assessment류의 전용 모델이 필요합니다.
