from __future__ import annotations

import threading
import time

import structlog

from src.services.notice_service import NoticeService

logger = structlog.get_logger()


class NoticeScheduler:
    def __init__(self, service: NoticeService, interval: int = 60) -> None:
        self._service = service
        self._interval = interval

    def start(self) -> None:
        thread = threading.Thread(target=self._loop, daemon=True, name="notice-scheduler")
        thread.start()

    def _loop(self) -> None:
        while True:
            self._dispatch()
            time.sleep(self._interval)

    def _dispatch(self) -> None:
        try:
            count = self._service.dispatch_due_notices()
            if count:
                logger.info("scheduled_notices_dispatched", count=count)
        except Exception:
            logger.exception("scheduler_dispatch_error")
