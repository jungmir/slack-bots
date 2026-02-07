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
├── __init__.py
├── __main__.py             # python -m src 엔트리포인트
├── app.py                  # Bolt 앱 초기화 및 엔트리포인트
├── config.py               # 환경 변수 및 설정 (Settings dataclass)
├── commands/               # 슬래시 커맨드 핸들러
├── events/                 # 이벤트 핸들러
├── services/               # 비즈니스 로직
├── views/                  # Modal / Home Tab 뷰
├── store/                  # 데이터 저장소
└── utils/                  # 유틸리티
tests/
└── test_app.py             # 앱 핸들러 테스트
```

## Running the App

1. `.env.example`을 `.env`로 복사하고 Slack 토큰을 설정
2. `uv sync` — 의존성 설치
3. `uv run python -m src` — Socket Mode로 앱 실행

## Development Tools

- **Linter/Formatter**: `ruff` — run `uv run ruff check .` and `uv run ruff format .`
- **Type checker**: `mypy` — run `uv run mypy src/`
- **Tests**: `pytest` — run `uv run pytest`
- **Pre-commit hooks**: `pre-commit` — run `uv run pre-commit run --all-files`
