from __future__ import annotations

import logging

from src.clients.dooray_client import DoorayApiError, DoorayClient, DoorayMember, DoorayTag, DoorayTask
from src.store.dooray_store import DoorayStore

logger = logging.getLogger(__name__)


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
            logger.warning("Failed to list tasks for %s: %s", slack_user_id, e)
            raise DoorayServiceError(str(e)) from e

    def create_task(
        self,
        *,
        subject: str,
        body: str = "",
        project_id: str = "",
        slack_user_id: str = "",
        to_member_ids: list[str] | None = None,
        tag_ids: list[str] | None = None,
        due_date: str = "",
    ) -> DoorayTask:
        pid = project_id or self._default_project_id
        if to_member_ids is None:
            to_member_ids = []
        if not to_member_ids and slack_user_id:
            member_id = self._store.get_dooray_member_id(slack_user_id)
            if member_id:
                to_member_ids = [member_id]
        try:
            return self._client.create_task(
                project_id=pid,
                subject=subject,
                body=body,
                to_member_ids=to_member_ids,
                tag_ids=tag_ids,
                due_date=due_date,
            )
        except DoorayApiError as e:
            logger.warning("Failed to create task: %s", e)
            raise DoorayServiceError(str(e)) from e

    def complete_task(self, task_id: str, project_id: str = "") -> bool:
        pid = project_id or self._default_project_id
        try:
            return self._client.complete_task(pid, task_id)
        except DoorayApiError as e:
            logger.warning("Failed to complete task %s: %s", task_id, e)
            raise DoorayServiceError(str(e)) from e

    def add_comment(self, task_id: str, content: str, project_id: str = "") -> bool:
        pid = project_id or self._default_project_id
        try:
            return self._client.add_comment(pid, task_id, content)
        except DoorayApiError as e:
            logger.warning("Failed to add comment to task %s: %s", task_id, e)
            raise DoorayServiceError(str(e)) from e

    def setup_user(self, slack_user_id: str, dooray_member_id: str) -> None:
        self._store.set_user_mapping(slack_user_id, dooray_member_id)

    def search_members(self, name: str) -> list[DoorayMember]:
        try:
            return self._client.search_members(name)
        except DoorayApiError as e:
            logger.warning("Failed to search members: %s", e)
            raise DoorayServiceError(str(e)) from e

    def list_project_tags(self) -> list[DoorayTag]:
        try:
            return self._client.list_project_tags(self._default_project_id)
        except DoorayApiError as e:
            logger.warning("Failed to list project tags: %s", e)
            raise DoorayServiceError(str(e)) from e

    def get_project_name(self) -> str:
        try:
            project = self._client.get_project(self._default_project_id)
            return project.name
        except DoorayApiError as e:
            logger.warning("Failed to get project name: %s", e)
            return ""
