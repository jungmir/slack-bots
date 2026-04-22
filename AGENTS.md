# AGENTS.md

AI 에이전트를 위한 프로젝트 컨텍스트. CLAUDE.md와 함께 참조하세요.

## Tech Stack

- **Runtime**: Python 3.13, `uv` 패키지 매니저
- **Framework**: Slack Bolt for Python (Socket Mode)
- **HTTP Client**: httpx (Dooray API 통신)
- **Storage**: SQLite (parameterized queries, `data/` 디렉토리)
- **Logging**: structlog (JSON 또는 컬러 콘솔)
- **Error Tracking**: Sentry (선택적)
- **Deployment**: Docker + Railway

## Architecture Decisions

- `create_app(settings)` 팩토리 패턴 — 테스트 시 의존성 주입 가능
- Dooray 기능은 완전히 선택적: 환경변수 없으면 커맨드 자체가 등록되지 않음
- 헬스체크 서버는 별도 스레드에서 실행 (Railway health probe용)
- Socket Mode 사용 — 퍼블릭 HTTP 엔드포인트 불필요

## Commands Available

| 커맨드 | 파일 | 설명 |
|--------|------|------|
| `/ping` | `app.py` | 연결 확인 |
| `/공지`, `/공지목록`, `/공지삭제` | `commands/notice.py` | 공지 관리 |
| `/dooray`, `/dooray목록` | `commands/dooray.py` | Dooray 태스크 관리 |

## Testing

```bash
uv run pytest                    # 전체 테스트
uv run pytest tests/test_app.py  # 특정 파일
uv run pytest -v                 # 상세 출력
```

**테스트 작성 시 필수 패턴:**
```python
from unittest.mock import patch, MagicMock

with patch("slack_sdk.web.client.WebClient.auth_test", return_value={"ok": True}):
    app = create_app(settings, request_verification_enabled=False)
```

## Code Style

```bash
uv run ruff check . --fix   # lint + autofix
uv run ruff format .        # format
uv run mypy src/            # type check
```

- mypy strict 모드 적용
- 모든 공개 함수에 타입 어노테이션 필수
- `from __future__ import annotations` 파일 상단에 포함

## Adding New Features

1. **새 슬래시 커맨드**: `src/commands/` 에 모듈 추가 → `app.py`의 `create_app()`에서 등록
2. **새 이벤트 핸들러**: `src/events/` 에 모듈 추가
3. **외부 API 클라이언트**: `src/clients/` 에 추가 (httpx 사용, timeout=10.0)
4. **데이터 저장**: `src/store/` 에 SQLite 기반 store 추가, parameterized query 사용
