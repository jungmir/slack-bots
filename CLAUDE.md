# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Slack bots for PyCon Korea. Python 3.13.5 project managed with `uv`.

## Development Environment

- **Package manager**: `uv`
- **Python version**: 3.13.5 (specified in `.python-version`)
- **Install dependencies**: `uv sync`
- **Add a dependency**: `uv add <package>`
- **Add a dev dependency**: `uv add --group dev <package>`

## Project Structure

```
src/
├── app.py                  # create_app() 팩토리 + main() 엔트리포인트
├── config.py               # Settings dataclass — env var 로드
├── healthcheck.py          # HTTP 헬스체크 서버 (별도 스레드)
├── logging_config.py       # structlog 설정
├── sentry_config.py        # Sentry 초기화 (DSN 없으면 비활성화)
├── clients/                # 외부 API 클라이언트 (DoorayClient)
├── commands/               # 슬래시 커맨드 핸들러 (notice, dooray)
├── events/                 # 이벤트 핸들러 (app_home_opened)
├── middleware/             # 요청 로깅 미들웨어
├── services/               # 비즈니스 로직
├── store/                  # SQLite 기반 데이터 저장소
├── views/                  # Modal 뷰 빌더
└── utils/                  # 공통 유틸리티
tests/
├── test_app.py
├── test_dooray.py
├── test_healthcheck.py
└── test_notice.py
```

## Environment Variables

**Required:**
- `SLACK_BOT_TOKEN` — xoxb-* 형식
- `SLACK_APP_TOKEN` — xapp-* 형식 (Socket Mode용)
- `SLACK_SIGNING_SECRET`

**Optional:**
- `DOORAY_API_TOKEN` + `DOORAY_PROJECT_ID` — 둘 다 설정 시 `/dooray` 커맨드 활성화
- `SENTRY_DSN` — 설정 시 Sentry 에러 추적 활성화
- `LOG_LEVEL` — DEBUG/INFO/WARNING/ERROR (기본값: INFO)
- `LOG_JSON` — true=JSON 로그(운영), false=컬러 콘솔(개발) (기본값: true)
- `HEALTHCHECK_PORT` — 헬스체크 HTTP 포트 (기본값: 8080)
- `DATA_DIR` — SQLite DB 저장 경로 (기본값: data/)

## Running the App

1. `.env.example`을 `.env`로 복사하고 Slack 토큰을 설정
2. `uv sync` — 의존성 설치
3. `uv run python -m src` — Socket Mode로 앱 실행

## Docker

```bash
docker build -t pycon-slack-bots .
docker run --env-file .env pycon-slack-bots
```

## Development Tools

- **Linter/Formatter**: `ruff` — run `uv run ruff check .` and `uv run ruff format .`
- **Type checker**: `mypy` — run `uv run mypy src/`
- **Tests**: `pytest` — run `uv run pytest`
- **Pre-commit hooks**: `pre-commit` — run `uv run pre-commit run --all-files`

## Key Patterns & Gotchas

- **Dooray 기능은 선택적**: `DOORAY_API_TOKEN`과 `DOORAY_PROJECT_ID` 모두 설정해야 커맨드 등록됨
- **테스트 시 WebClient mock 필요**: `App()` 초기화 시 실제 API 호출 발생 → `slack_sdk.web.client.WebClient.auth_test` mock 필요
- **mypy**: `SocketModeHandler.start()`에 `# type: ignore[no-untyped-call]` 필요
- **SQLite DB**: `DATA_DIR` 경로에 생성됨 — Railway 배포 시 Volume 마운트 필요
