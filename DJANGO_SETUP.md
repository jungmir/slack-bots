# Django 전환 가이드

FastAPI에서 Django로 전환이 완료되었습니다.

## 주요 변경 사항

### 1. 프로젝트 구조
```
slack-bots/
├── manage.py              # Django 관리 명령어
├── notipy/                # Django 프로젝트 설정
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── announcements/         # Django 앱
│   ├── models.py          # Django ORM 모델
│   ├── admin.py           # Admin 설정
│   ├── views.py           # Slack 이벤트 뷰
│   ├── slack_handlers.py  # Slack 핸들러 (구현 필요)
│   └── urls.py
└── app_old/               # 기존 FastAPI 코드 (참고용)
```

### 2. 모델
- `Announcement` - 공지사항
- `ReadReceipt` - 읽음 확인
- `BlockKitTemplate` - **블록 킷 템플릿 (새로 추가!)**

### 3. Django Admin
Django Admin에서 다음 기능을 사용할 수 있습니다:

- 공지사항 관리 (읽음/안읽음 현황 포함)
- 읽음 확인 현황 조회
- **Block Kit 템플릿 관리 (JSON 편집기 포함)**

## 설정 방법

### 1. 마이그레이션 (완료됨)
```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

### 2. Admin 사용자 생성
```bash
uv run python manage.py createsuperuser
```

### 3. 개발 서버 실행
```bash
uv run python manage.py runserver 0.0.0.0:3000
```

### 4. Admin 접속
http://localhost:3000/admin

## Slack 핸들러 구현

`announcements/slack_handlers.py`에 Slack 이벤트 핸들러를 구현해야 합니다.

기존 코드를 참고하여 다음과 같이 변환하세요:

### FastAPI → Django 변환 예시

**Before (FastAPI):**
```python
from app.database import SessionLocal
from app.models import Announcement

with SessionLocal() as session:
    announcements = session.execute(
        select(Announcement)
    ).scalars().all()
```

**After (Django):**
```python
from .models import Announcement

announcements = Announcement.objects.all()
```

### 주요 변환 포인트

1. **ORM 쿼리**:
   - `SessionLocal()` → Django ORM 직접 사용
   - `session.execute(select(...))` → `Model.objects.filter(...)`

2. **핸들러 등록**:
   - `@slack_app.event()`, `@slack_app.action()` 등은 동일하게 사용
   - `slack_handlers.py`에 핸들러 작성 후 자동으로 로드됨

3. **Block Kit 템플릿**:
   ```python
   # Admin에서 생성한 템플릿 사용
   template = BlockKitTemplate.objects.get(
       template_type='announcement',
       is_active=True
   )
   blocks = template.blocks  # JSON 데이터
   ```

## Block Kit 템플릿 사용법

1. Admin 로그인
2. "Block Kit 템플릿" 메뉴 선택
3. "템플릿 추가" 클릭
4. JSON 편집기에서 Block Kit JSON 입력
   - [Block Kit Builder](https://app.slack.com/block-kit-builder)에서 미리 작성 가능
5. 저장 후 코드에서 사용

## TODO

- [ ] `app_old/handlers/` 코드를 `announcements/slack_handlers.py`로 이식
- [ ] Block Kit 템플릿 초기 데이터 생성
- [ ] 리마인더 기능 구현
- [ ] 테스트 코드 업데이트

## 참고

- 기존 FastAPI 코드: `app_old/` 디렉토리
- Django 문서: https://docs.djangoproject.com/
- Slack Bolt for Python: https://slack.dev/bolt-python/
