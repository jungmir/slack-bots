from __future__ import annotations

import structlog

from src.clients.dooray_client import DoorayApiError, DoorayClient, DoorayMember, DoorayTag, DoorayTask
from src.store.dooray_store import DoorayStore

logger = structlog.get_logger()


class UserNotLinkedError(Exception):
    pass


class DoorayServiceError(Exception):
    pass


class DoorayService:
    def __init__(
        self,
        *,
        dooray_client: DoorayClient,
        store: DoorayStore,
        default_project_id: str,
    ) -> None:
        self._client = dooray_client
        self._store = store
        self._default_project_id = default_project_id

    def get_my_tasks(self, slack_user_id: str) -> list[DoorayTask]:
        member_id = self._store.get_dooray_member_id(slack_user_id)
        if member_id is None:
            raise UserNotLinkedError
        try:
            return self._client.list_my_tasks(member_id, self._default_project_id)
        except DoorayApiError as e:
            logger.warning("dooray_list_tasks_failed", slack_user_id=slack_user_id, error=str(e))
            raise DoorayServiceError(str(e)) from e

    def create_task(
        self,
        *,
        subject: str,
        body: str = "",
        slack_user_id: str = "",
        tag_ids: list[str] | None = None,
        due_date: str = "",
    ) -> DoorayTask:
        to_member_ids: list[str] = []
        if slack_user_id:
            member_id = self._store.get_dooray_member_id(slack_user_id)
            if member_id:
                to_member_ids = [member_id]
        try:
            return self._client.create_task(
                project_id=self._default_project_id,
                subject=subject,
                body=body,
                to_member_ids=to_member_ids,
                tag_ids=tag_ids,
                due_date=due_date,
            )
        except DoorayApiError as e:
            logger.warning("dooray_create_task_failed", error=str(e))
            raise DoorayServiceError(str(e)) from e

    def setup_user(self, slack_user_id: str, dooray_member_id: str) -> None:
        self._store.set_user_mapping(slack_user_id, dooray_member_id)

    def search_members(self, name: str) -> list[DoorayMember]:
        try:
            return self._client.search_members(name)
        except DoorayApiError as e:
            logger.warning("dooray_search_members_failed", name=name, error=str(e))
            raise DoorayServiceError(str(e)) from e

    def list_project_tags(self) -> list[DoorayTag]:
        try:
            return self._client.list_project_tags(self._default_project_id)
        except DoorayApiError as e:
            logger.warning("dooray_list_tags_failed", error=str(e))
            raise DoorayServiceError(str(e)) from e
