# voice-grader-demo

STT(faster-whisper, CPU) + 규칙 기반 발음 채점 데모. 단어/문장(한국어·영어)을 화면에 보여주고
녹음하면, 인식된 텍스트와 어떤 부분이 왜 틀렸는지에 대한 피드백을 보여줍니다.

## 구조

- `app/main.py` — FastAPI 서버. `/api/items`, `/api/grade` 제공, `static/`을 서빙.
- `app/grader.py` — 채점 로직. `Grader` 인터페이스에 `HeuristicGrader`(규칙 기반, API 불필요)와
  `ClaudeGrader`(Anthropic API)가 있음. `ANTHROPIC_API_KEY` 환경변수가 있으면 자동으로
  `ClaudeGrader`로 전환됩니다 (`get_grader()`).
- `app/items.py` — 데모용 단어/문장 목록.
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

- `ANTHROPIC_API_KEY` — 설정하면 Claude 기반 채점으로 자동 전환.
- `DEMO_TOKEN` — 설정하면 `/api/grade` 요청에 동일한 `token` 폼 필드가 없으면 401.
  **외부에 공개할 때는 반드시 설정할 것** (안 그러면 아무나 CPU에 whisper job을 돌릴 수 있음).
- `WHISPER_MODEL_SIZE` — `tiny`/`base`/`small`(기본)/`medium`. 단어 단위 인식은 `small` 이상 권장.

## Cloudflare Tunnel로 외부 노출

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8421
```

출력되는 `https://xxxx.trycloudflare.com` 주소가 외부 접근용 URL입니다 (임시 터널, 재시작마다 URL 바뀜).
공개 전에 `DEMO_TOKEN`을 설정하고, 프론트엔드 요청에 해당 토큰을 넣도록 조정하세요.

## 알려진 한계

- 1~2음절 고립 단어는 문맥이 없어 Whisper 인식이 불안정할 수 있습니다 (예: "rice"가 "license"로 인식되는 경우 있음). 문장 단위가 상대적으로 안정적입니다.
- `HeuristicGrader`는 텍스트 diff 기반이라 실제 억양/음향 품질은 평가하지 못하고, 자주 틀리는
  발음 패턴(r/l, f/p 등)에 대한 추정 가이드만 제공합니다. 진짜 음향 기반 발음 평가가 필요하면
  Azure Pronunciation Assessment류의 전용 모델이 필요합니다.
