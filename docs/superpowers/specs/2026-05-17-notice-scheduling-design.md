# 공지 예약 발송 설계

**날짜**: 2026-05-17  
**상태**: 승인됨

## 개요

`/공지`와 `/정기회의` 커맨드에 예약 발송 기능을 추가한다. 사용자는 모달에서 날짜/시간을 지정해 공지를 예약할 수 있고, 앱 홈 탭에서 예약 목록을 확인하고 취소할 수 있다. 예약된 공지는 발송 시점 이후 기존 공지와 동일하게 동작한다(읽음 확인, 출석 응답, 리마인드 등).

## 데이터 모델

### `notices` 테이블 컬럼 추가

```sql
scheduled_at REAL     -- 예약 발송 시각(Unix timestamp). NULL이면 즉시 발송.
status TEXT NOT NULL DEFAULT 'active'
  -- 'scheduled': 발송 대기 중
  -- 'active'   : 발송 완료 (기존 공지의 기본값)
  -- 'cancelled': 취소됨
```

### `Notice` / `MeetingNotice` 모델

`src/store/models.py`에 `scheduled_at: float | None = None`과 `status: str = 'active'` 필드 추가.

## 컴포넌트 구조

| 파일 | 변경 내용 |
|------|-----------|
| `src/store/models.py` | `Notice`/`MeetingNotice`에 `scheduled_at`, `status` 필드 추가 |
| `src/store/notice_store.py` | `scheduled_at`, `status` 컬럼 추가. `list_pending_scheduled()`, `update_notice_status()` 메서드 추가 |
| `src/services/notice_service.py` | `create_scheduled_notice()`, `create_scheduled_meeting_notice()`, `cancel_scheduled_notice()`, `dispatch_due_notices()` 추가 |
| `src/views/notice_views.py` | 모달에 예약 옵션(라디오 + datetimepicker) 추가. 홈 탭에 "예약된 공지" 섹션 추가 |
| `src/commands/notice.py` | 모달 제출 핸들러에서 즉시/예약 분기 처리. 취소 버튼 action 핸들러 추가 |
| `src/scheduler.py` | **신규** — `NoticeScheduler` 클래스. 데몬 스레드로 1분 폴링 루프 실행 |
| `src/app.py` | `create_app()`에서 `NoticeScheduler` 시작 |

## UX 흐름

### 1. 예약 공지 작성

1. 사용자가 `/공지` 또는 `/정기회의` 입력
2. 모달 하단에 "예약 발송 시각" `datetimepicker` 추가 (선택 사항, hint: "비워두면 즉시 발송")
3. 제출:
   - datetime 미입력: 즉시 발송, 기존 동작 그대로 (`chat.postMessage`)
   - datetime 입력: DB에 `status='scheduled'`로 저장, 메시지 미발송. 작성자에게 DM으로 "예약 등록됨 (발송 예정: YYYY-MM-DD HH:mm KST)" 확인 메시지 발송

> **구현 참고**: Slack 모달은 액션 없이 필드를 동적으로 숨길 수 없으므로, 라디오 대신 선택적 datetimepicker 단일 필드를 사용한다.

### 2. 예약 목록 확인 및 취소

- 앱 홈 탭 최상단에 "예약된 공지" 섹션 표시 (예약 없으면 섹션 숨김)
- 각 예약 항목: 제목, 채널, 예약 시각, **취소** 버튼
- 취소 버튼 클릭 → `status='cancelled'` 로 변경, 홈 탭 갱신

### 3. 예약 발송 실행

- `NoticeScheduler`가 1분 주기로 `status='scheduled' AND scheduled_at <= now()` 인 공지 조회
- 각 공지에 대해 `chat.postMessage` 호출 → `message_ts` 저장 → `status='active'` 로 업데이트
- 발송 후 기존 공지와 동일하게 동작 (읽음 확인, 리마인드, 수정, 삭제 등)

## `NoticeScheduler` 구현

```python
class NoticeScheduler:
    def __init__(self, service: NoticeService, interval: int = 60) -> None: ...

    def start(self) -> None:
        # threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while True:
            self._dispatch()
            time.sleep(self._interval)

    def _dispatch(self) -> None:
        # store.list_pending_scheduled() → service.dispatch_due_notices()
```

헬스체크 서버와 동일한 데몬 스레드 패턴 사용.

## 에러 처리

- 발송 실패(Slack API 오류) 시: `status`를 `'scheduled'`로 유지하여 다음 폴링 주기에 재시도. 오류를 structlog로 기록.
- 취소된 공지는 폴링에서 제외 (`status != 'scheduled'`).

## 테스트 계획

- `NoticeStore.list_pending_scheduled()`: `scheduled_at <= now`이고 `status='scheduled'`인 항목만 반환하는지 검증
- `NoticeService.dispatch_due_notices()`: 발송 후 `status='active'`, `message_ts` 업데이트 검증
- `NoticeService.cancel_scheduled_notice()`: `status='cancelled'` 업데이트 검증
- 모달 제출 핸들러: 즉시/예약 분기 처리 검증
- 기존 즉시 발송 테스트가 통과하는지 확인 (회귀 방지)
