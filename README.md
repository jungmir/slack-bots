# PyCon Korea Slack Bot

PyCon Korea 준비위원회를 위한 Slack 봇. 두레이 업무 관리와 공지 관리를 슬랙에서 바로 수행할 수 있습니다.

## 기능

### 공지 관리

| 커맨드 | 설명 |
|--------|------|
| `/공지` | 공지 작성 (모달) — 대상 채널에 공지 게시, 멤버 읽음 확인 버튼 포함 |
| `/정기회의` | 정기회의 공지 작성 — 온라인/오프라인/미참석 참석 여부 수집 |

공지 메시지에서 직접 현황 조회, 리마인드 발송, 수정·삭제를 할 수 있습니다.

### 두레이 업무 관리 (선택적)

`DOORAY_API_TOKEN`과 `DOORAY_PROJECT_ID` 설정 시 활성화됩니다.

| 커맨드 | 설명 |
|--------|------|
| `/내업무` | 나에게 할당된 두레이 업무 목록 조회 |
| `/새업무` | 두레이 업무 생성 (모달) |
| `/두레이연동` | 두레이 계정 연결 |

### 기타

| 커맨드 | 설명 |
|--------|------|
| `/ping` | 봇 상태 확인 |

앱 홈 탭에서 공지 목록을 확인할 수 있습니다.

## 시작하기

### 사전 준비

- Python 3.13
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- Slack App (Socket Mode 활성화)

### 설치

```bash
git clone https://github.com/your-org/pycon-slack-bots.git
cd pycon-slack-bots
uv sync
```

### Slack App 설정

1. [api.slack.com/apps](https://api.slack.com/apps) 에서 새 앱 생성
2. `manifest.json` 내용을 App Manifest에 붙여넣기
3. Socket Mode 활성화 후 App-Level Token 발급 (`connections:write` 스코프)
4. 앱을 워크스페이스에 설치하고 Bot Token 복사

### 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에서 아래 값을 채웁니다:

| 변수 | 필수 | 설명 |
|------|------|------|
| `SLACK_BOT_TOKEN` | ✅ | xoxb-* 형식 Bot Token |
| `SLACK_APP_TOKEN` | ✅ | xapp-* 형식 App-Level Token |
| `SLACK_SIGNING_SECRET` | ✅ | Slack App Signing Secret |
| `DOORAY_API_TOKEN` | | 두레이 Personal Access Token |
| `DOORAY_PROJECT_ID` | | 두레이 프로젝트 ID |
| `SENTRY_DSN` | | Sentry DSN (에러 추적) |
| `LOG_LEVEL` | | DEBUG/INFO/WARNING/ERROR (기본값: INFO) |
| `LOG_JSON` | | true=JSON 로그, false=컬러 콘솔 (기본값: true) |
| `HEALTHCHECK_PORT` | | 헬스체크 HTTP 포트 (기본값: 8080) |
| `DATA_DIR` | | SQLite DB 저장 경로 (기본값: data/) |

### 실행

```bash
uv run python -m src
```

## 개발

```bash
# 린트 및 포맷
uv run ruff check . --fix
uv run ruff format .

# 타입 체크
uv run mypy src/

# 테스트
uv run pytest

# 전체 pre-commit 검사
uv run pre-commit run --all-files
```

## Docker

```bash
docker build -t pycon-slack-bots .
docker run --env-file .env pycon-slack-bots
```

## 배포 (Railway)

Railway Volume을 `DATA_DIR` 경로에 마운트하면 SQLite 데이터가 유지됩니다. 헬스체크는 `HEALTHCHECK_PORT` (기본 8080)의 `/health` 엔드포인트를 사용합니다.

## 프로젝트 구조

```
src/
├── app.py              # create_app() 팩토리 + 엔트리포인트
├── config.py           # Settings dataclass
├── healthcheck.py      # HTTP 헬스체크 서버
├── logging_config.py   # structlog 설정
├── sentry_config.py    # Sentry 초기화
├── clients/            # 외부 API 클라이언트
├── commands/           # 슬래시 커맨드 핸들러
├── events/             # 이벤트 핸들러
├── middleware/         # 요청 로깅 미들웨어
├── services/           # 비즈니스 로직
├── store/              # SQLite 데이터 저장소
└── views/              # Slack Block Kit 뷰 빌더
```
