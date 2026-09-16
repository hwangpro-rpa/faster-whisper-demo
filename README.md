# voice-grader-demo

STT(faster-whisper, CPU) + 규칙 기반 발음 채점 데모. 단어/문장(한국어·영어)을 화면에 보여주고
녹음하면, 인식된 텍스트와 어떤 부분이 왜 틀렸는지에 대한 피드백·점수를 보여줍니다. 로그인 없이
기기 단위로 XP·레벨·도장이 쌓이는 게임화 요소도 있습니다.

## 구조

- `app/main.py` — FastAPI 서버. `/api/items`, `/api/grade` 제공, `static/`을 서빙.
- `app/grader.py` — 채점 로직. `Grader` 인터페이스에 `HeuristicGrader`(규칙 기반, API 불필요)와
  `ClaudeGrader`(Anthropic API)가 있음. `ANTHROPIC_API_KEY` 환경변수가 있으면 자동으로
  `ClaudeGrader`로 전환됩니다 (`get_grader()`).
- `app/items.py` — 데모용 단어/문장 목록. `unlock_level`(난이도 잠금), `mode`/`blank_index`(빈칸 채우기),
  `hotwords_for(language)`(인식 정확도용 어휘 힌트)를 가짐.
- `app/audio_prep.py` — 인식 전 오디오 정규화(피크 노멀라이즈).
- `app/progress.py` — 기기 단위(로그인 없음) XP·레벨·도장 진행도. SQLite 파일(`voicegrader.db`,
  git에는 안 올라감) 하나로 저장.
- `static/index.html` — 프론트엔드 (바닐라 JS, 빌드 불필요, 단일 파일). 미니멀한 앱 셸 UI
  (상단바/중앙 카드/하단 컨트롤), 라이트·다크 모드 자동 대응. 목표 문장을 브라우저 내장
  Web Speech API로 읽어주는 "들어보기" 버튼 포함 (서버·API 키 불필요, 빈칸 채우기 항목에서는
  정답이 그대로 들리므로 버튼을 숨김).

## 게임화 요소 (로그인 없음)

- **기기 식별**: 서버에 계정이 없습니다. 프론트엔드가 최초 접속 시 `crypto.randomUUID()`로 만든
  ID를 localStorage에 저장하고, 매 채점 요청마다 `device_id`로 같이 보냅니다. 브라우저 저장소를
  지우면 그 기기의 진행도는 사라집니다 (의도된 트레이드오프).
- **XP·레벨**: 점수(`overall`)를 10으로 나눈 값을 XP로 적립, 20XP마다 레벨업 (`app/progress.py`의
  `XP_PER_LEVEL` 상수로 조정 가능). 레벨에 따라 캐릭터가 진화합니다: 🥚 → 🐣 → 🐤 → 🦜(레벨6, "말을
  따라하는 새") → 🦉(레벨8, 마스터).
- **도장**: 항목별로 점수 80점 이상을 한 번이라도 받으면 그 항목의 도장 획득. 화면 하단 도장판에
  누적 표시.
- **난이도 잠금**: 각 항목에 `unlock_level`이 있어서, 레벨이 낮으면 단어만 뽑히고 레벨이 오르면
  짧은 문장 → 긴 문장 순으로 풀에 추가됩니다.
- **빈칸 채우기**: 일부 문장 항목은 `mode: "fill_blank"`로 지정돼 있어서, 화면엔 한 단어가
  "_____"로 가려진 채 나오고 학습자는 빈칸을 채워서 문장 전체를 말합니다. 채점은 서버에 저장된
  원문 전체와 비교하므로 별도 로직 없이 기존 채점 파이프라인을 그대로 씁니다.

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
  **외부에 공개할 때는 반드시 설정할 것** — Tailscale Funnel은 tailnet 멤버십과 무관하게 URL을 아는
  누구나 접근 가능한 완전 공개 상태라서, 이 토큰이 유일한 접근 제어입니다. 안 걸어두면 아무나 URL로
  CPU에 whisper job을 무제한 돌릴 수 있음. 프론트엔드는 URL에 `?token=값`을 한 번 붙여서 열면 그
  값을 브라우저 localStorage에 저장해두고 이후 모든 요청에 자동으로 실어 보냅니다 — 즉 공유용
  링크를 `https://<주소>/?token=값` 형태로 한 번 전달하면 됨.
- `WHISPER_MODEL_SIZE` — `tiny`/`base`/`small`(기본)/`medium`. `medium`은 인식이 더 정확할 수 있지만
  4코어 i3 CPU 기준 짧은 문장 하나에 약 14초가 걸려 데모용으로는 느립니다. 속도보다 정확도가
  급하지 않다면 시도해볼 수 있는 정도.

## Tailscale Funnel로 외부 노출

처음엔 cloudflared 퀵 터널을 썼는데, 재시작할 때마다 URL이 랜덤으로 바뀌는 게 문제였습니다
(북마크·공유 링크가 매번 깨짐). 지금은 **Tailscale Funnel**로 바꿔서 고정 URL을 씁니다.

```bash
brew install --cask tailscale-app   # 최초 1회, 설치 후 앱에서 로그인 필요
tailscale set --hostname=speaking   # 기기 이름 지정 → URL에 반영됨
tailscale funnel --bg --https=443 8421
```

한 번만 해주면 되는 사전 준비:
- Tailscale 관리 콘솔(`https://login.tailscale.com/admin/dns`)에서 **HTTPS Certificates** 활성화
- 관리 콘솔의 **Access controls → JSON editor**에서 ACL 정책에 아래 추가 (Funnel 사용 권한 부여):
  ```json
  "nodeAttrs": [
    { "target": ["autogroup:member"], "attr": ["funnel"] }
  ]
  ```

이후 접근 주소는 `https://<hostname>.<tailnet 이름>.ts.net` 형태로 고정됩니다 (지금은
`https://speaking.tail8d1c85.ts.net`). tailnet 이름 뒷부분은 무료 플랜에서는 직접 입력이 아니라
관리 콘솔에서 제공하는 후보 중에서만 고를 수 있습니다.

- **왜 ngrok이 아니라 Tailscale인지**: ngrok 무료 플랜은 방문자마다 "이 사이트는 ngrok을 통해
  제공됩니다 - 계속 진행" 경고 페이지를 한 번 거치게 해서 피싱처럼 보일 수 있음. Tailscale Funnel은
  그런 인터스티셜 없이 바로 연결됨.
- 자기 자신(같은 tailnet에 속한 기기)에서 이 URL을 테스트하면 MagicDNS가 내부 IP로 바로 연결해버려서
  진단이 꼬일 수 있습니다 — 외부 확인은 반드시 tailnet 밖의 기기(예: 다른 와이파이/LTE)로 하세요.

### 재부팅해도 자동 시작

- **서버(uvicorn)**: `~/Library/LaunchAgents/com.lavenderlabs.voicegrader.plist`로 launchd에 등록되어
  있어서 로그인 시 자동 시작·크래시 시 자동 재시작됩니다. 코드를 바꾼 뒤에는
  `launchctl unload ~/Library/LaunchAgents/com.lavenderlabs.voicegrader.plist && launchctl load -w ~/Library/LaunchAgents/com.lavenderlabs.voicegrader.plist`로
  재시작하세요 (단, `static/index.html`은 정적 파일이라 재시작 없이 바로 반영됨).
- **Funnel**: Tailscale 앱 자체가 로그인 항목으로 등록되어 있어서 재부팅 후 자동으로 다시
  연결되고, `tailscale funnel` 설정은 tailscaled에 저장되어 있어 별도 재실행 없이 복원됩니다.

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
