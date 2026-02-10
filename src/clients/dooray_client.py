from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.dooray.com"


class DoorayApiError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Dooray API error ({status_code}): {message}")


@dataclass(frozen=True)
class DoorayTask:
    id: str
    project_id: str
    subject: str
    workflow_name: str
    workflow_class: str
    users_to: list[str]


@dataclass(frozen=True)
class DoorayMember:
    id: str
    name: str
    email: str


@dataclass(frozen=True)
class DoorayTag:
    id: str
    name: str
    color: str


@dataclass(frozen=True)
class DoorayProject:
    id: str
    name: str


@dataclass(frozen=True)
class DoorayWorkflow:
    id: str
    name: str
    workflow_class: str


class DoorayClient:
    def __init__(self, token: str, *, http_client: httpx.Client | None = None) -> None:
        self._client = http_client or httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"dooray-api {token}"},
            timeout=10.0,
        )

    def _request(self, method: str, path: str, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        if timeout is not None:
            kwargs["timeout"] = timeout
        logger.debug("Dooray API %s %s kwargs=%s", method, path, {k: v for k, v in kwargs.items() if k != "headers"})
        response = self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise DoorayApiError(response.status_code, response.text)
        data: dict[str, Any] = response.json()
        header = data.get("header", {})
        if isinstance(header, dict) and header.get("isSuccessful") is False:
            msg = str(header.get("resultMessage", "Unknown error"))
            raise DoorayApiError(response.status_code, msg)
        return data

    def list_my_tasks(self, member_id: str, project_id: str) -> list[DoorayTask]:
        data = self._request(
            "GET",
            f"/project/v1/projects/{project_id}/posts",
            params={
                "toMemberIds": member_id,
                "postWorkflowClasses": "registered,working",
                "size": 20,
                "order": "-createdAt",
            },
        )
        result = data.get("result", [])
        if isinstance(result, list):
            items: list[dict[str, Any]] = result
        elif isinstance(result, dict):
            items = result.get("contents", [])
        else:
            items = []
        logger.warning("list_my_tasks raw items (first 2): %s", [(i.get("id"), i.get("number")) for i in items[:2]])
        return [self._parse_task(item, project_id) for item in items]

    def create_task(
        self,
        *,
        project_id: str,
        subject: str,
        body: str = "",
        to_member_ids: list[str] | None = None,
        tag_ids: list[str] | None = None,
        due_date: str = "",
    ) -> DoorayTask:
        payload: dict[str, Any] = {"subject": subject}
        if body:
            payload["body"] = {"mimeType": "text/x-markdown", "content": body}
        if to_member_ids:
            payload["users"] = {
                "to": [{"type": "member", "member": {"organizationMemberId": mid}} for mid in to_member_ids],
            }
        if tag_ids:
            payload["tagIds"] = tag_ids
        if due_date:
            if len(due_date) == 10:  # "YYYY-MM-DD" from Slack datepicker
                due_date = f"{due_date}T23:59:59+09:00"
            payload["dueDate"] = due_date
        logger.warning("create_task payload: %s", payload)
        data = self._request("POST", f"/project/v1/projects/{project_id}/posts", json=payload)
        result: dict[str, Any] = data.get("result", {})
        logger.warning("create_task response result: %s", result)
        return DoorayTask(
            id=str(result.get("id", "")),
            project_id=project_id,
            subject=subject,
            workflow_name="등록",
            workflow_class="registered",
            users_to=to_member_ids or [],
        )

    def complete_task(self, project_id: str, task_id: str) -> bool:
        workflows = self.list_workflows(project_id)
        closed_wf = next((w for w in workflows if w.workflow_class == "closed"), None)
        if closed_wf is None:
            logger.warning("No closed workflow found for project %s", project_id)
            return False
        logger.warning(
            "complete_task: project_id=%s, task_id=%s, workflow_id=%s",
            project_id,
            task_id,
            closed_wf.id,
        )
        self._request(
            "POST",
            f"/project/v1/projects/{project_id}/posts/{task_id}/set-workflow",
            json={"workflowId": closed_wf.id},
        )
        return True

    def add_comment(self, project_id: str, task_id: str, content: str) -> bool:
        self._request(
            "POST",
            f"/project/v1/projects/{project_id}/posts/{task_id}/logs",
            json={"body": {"mimeType": "text/x-markdown", "content": content}},
        )
        return True

    def list_workflows(self, project_id: str) -> list[DoorayWorkflow]:
        data = self._request("GET", f"/project/v1/projects/{project_id}/workflows")
        result = data.get("result", [])
        return [
            DoorayWorkflow(
                id=str(w.get("id", "")),
                name=str(w.get("name", "")),
                workflow_class=str(w.get("class", "")),
            )
            for w in result
        ]

    def search_members(self, name: str) -> list[DoorayMember]:
        data = self._request(
            "GET",
            "/common/v1/members",
            params={"name": name},
        )
        result = data.get("result", [])
        return [
            DoorayMember(
                id=str(m.get("id", "")),
                name=str(m.get("name", "")),
                email=str(m.get("email", "")),
            )
            for m in result
        ]

    def get_member(self, member_id: str) -> DoorayMember:
        data = self._request(
            "GET",
            f"/common/v1/members/{member_id}",
            timeout=2.0,
        )
        result = data.get("result", {})
        return DoorayMember(
            id=str(result.get("id", member_id)),
            name=str(result.get("name", "")),
            email=str(result.get("email", "")),
        )

    def list_project_tags(self, project_id: str) -> list[DoorayTag]:
        data = self._request(
            "GET",
            f"/project/v1/projects/{project_id}/tags",
            timeout=2.0,
            params={"size": 100},
        )
        result = data.get("result", [])
        if isinstance(result, dict):
            items: list[dict[str, Any]] = result.get("contents", [])
        elif isinstance(result, list):
            items = result
        else:
            items = []
        return [
            DoorayTag(
                id=str(t.get("id", "")),
                name=str(t.get("name", "")),
                color=str(t.get("color", "")),
            )
            for t in items
            if t.get("id")
        ]

    def get_project(self, project_id: str) -> DoorayProject:
        data = self._request(
            "GET",
            f"/project/v1/projects/{project_id}",
            timeout=2.0,
        )
        result = data.get("result", {})
        name = str(result.get("code", "") or result.get("name", "") or "")
        return DoorayProject(id=project_id, name=name)

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _parse_task(item: dict[str, Any], project_id: str) -> DoorayTask:
        workflow_raw = item.get("workflowClass", item.get("workflow", {}))
        if isinstance(workflow_raw, str):
            workflow_name = workflow_raw
            workflow_class = workflow_raw
        elif isinstance(workflow_raw, dict):
            workflow_name = str(workflow_raw.get("name", ""))
            workflow_class = str(workflow_raw.get("class", workflow_raw.get("workflowClass", "")))
        else:
            workflow_name = ""
            workflow_class = ""
        users = item.get("users", {})
        to_list: list[dict[str, Any]] = []
        if isinstance(users, dict):
            to_list = users.get("to", [])
        to_ids = [str(u.get("member", {}).get("organizationMemberId", "")) for u in to_list if isinstance(u, dict)]
        return DoorayTask(
            id=str(item.get("id", "")),
            project_id=project_id,
            subject=str(item.get("subject", "")),
            workflow_name=workflow_name,
            workflow_class=workflow_class,
            users_to=to_ids,
        )
