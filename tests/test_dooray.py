from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import httpx
from slack_bolt import App, BoltRequest
from slack_sdk.web import SlackResponse

from src.app import create_app
from src.clients.dooray_client import (
    DoorayApiError,
    DoorayClient,
    DoorayMember,
    DoorayTag,
    DoorayTask,
)
from src.config import Settings
from src.services.dooray_service import DoorayService, DoorayServiceError, UserNotLinkedError
from src.store.dooray_store import DoorayStore
from src.views.dooray_views import (
    build_dooray_create_task_modal,
    build_dooray_error_modal,
    build_dooray_member_search_modal,
    build_dooray_not_linked_modal,
    build_dooray_result_modal,
    build_dooray_setup_modal,
    build_dooray_setup_select_modal,
    build_dooray_task_list_modal,
    build_dooray_usage_modal,
)

_SAMPLE_MEMBERS = [
    DoorayMember(id="M1", name="홍길동", email="hong@test.com"),
    DoorayMember(id="M2", name="김철수", email="kim@test.com"),
]
_SAMPLE_TAGS = [
    DoorayTag(id="TAG1", name="버그", color="red"),
    DoorayTag(id="TAG2", name="기능", color="blue"),
]

_MOCK_AUTH_RESPONSE = SlackResponse(
    client=None,  # type: ignore[arg-type]
    http_verb="POST",
    api_url="https://slack.com/api/auth.test",
    req_args={},
    data={"ok": True, "user_id": "U1234", "bot_id": "B1234", "team_id": "T1234"},
    headers={},
    status_code=200,
)


def _make_settings(**kwargs: str) -> Settings:
    defaults = {
        "slack_bot_token": "xoxb-test",
        "slack_app_token": "xapp-test",
        "slack_signing_secret": "test-secret",
        "dooray_api_token": "test-dooray-token",
        "dooray_project_id": "P1234",
    }
    defaults.update(kwargs)
    return Settings(**defaults)  # type: ignore[arg-type]


def _create_test_app(
    dooray_store: DoorayStore | None = None,
    dooray_client: DoorayClient | None = None,
    settings: Settings | None = None,
) -> App:
    if settings is None:
        settings = _make_settings()
    if dooray_store is None:
        dooray_store = DoorayStore()
    if dooray_client is None:
        dooray_client = DoorayClient("test-token", http_client=MagicMock(spec=httpx.Client))
    with patch("slack_sdk.web.client.WebClient.auth_test", return_value=_MOCK_AUTH_RESPONSE):
        return create_app(
            settings,
            request_verification_enabled=False,
            dooray_client=dooray_client,
            dooray_store=dooray_store,
        )


def _make_mock_client() -> MagicMock:
    return MagicMock(spec=httpx.Client)


# --- DoorayClient Tests ---


class TestDoorayClient:
    def test_create_task(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "TASK_001"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        task = client.create_task(project_id="P1", subject="Test task", body="body text")
        assert task.id == "TASK_001"
        assert task.subject == "Test task"

    def test_create_task_with_assignee(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "TASK_002"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        task = client.create_task(project_id="P1", subject="Assigned", to_member_ids=["M1"])
        assert task.users_to == ["M1"]

    def test_create_task_with_tags_and_due_date(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "TASK_003"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        task = client.create_task(
            project_id="P1",
            subject="Tagged",
            tag_ids=["TAG1", "TAG2"],
            due_date="2026-03-01",
        )
        assert task.id == "TASK_003"
        call_kwargs = mock_http.request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["tagIds"] == ["TAG1", "TAG2"]
        assert payload["dueDate"] == "2026-03-01T23:59:59+09:00"

    def test_list_my_tasks(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "id": "T1",
                    "subject": "Task 1",
                    "workflowClass": {"name": "진행중", "class": "working"},
                    "users": {"to": []},
                },
                {
                    "id": "T2",
                    "subject": "Task 2",
                    "workflowClass": {"name": "등록", "class": "registered"},
                    "users": {"to": []},
                },
            ],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        tasks = client.list_my_tasks("M1", "P1")
        assert len(tasks) == 2
        assert tasks[0].subject == "Task 1"

    def test_search_members(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {"id": "M1", "name": "홍길동", "email": "hong@example.com"},
                {"id": "M2", "name": "홍길순", "email": "hongsun@example.com"},
            ],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        members = client.search_members("홍")
        assert len(members) == 2
        assert members[0].name == "홍길동"

    def test_api_error_raises(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        try:
            client.list_my_tasks("M1", "P1")
            assert False, "Should have raised"
        except DoorayApiError as e:
            assert e.status_code == 401

    def test_list_project_tags(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {"id": "TAG1", "name": "버그", "color": "red"},
                {"id": "TAG2", "name": "기능", "color": "blue"},
            ],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)

        tags = client.list_project_tags("P1")
        assert len(tags) == 2
        assert tags[0].id == "TAG1"
        assert tags[0].name == "버그"
        assert tags[0].color == "red"



# --- DoorayStore Tests ---


class TestDoorayStore:
    def test_set_and_get_mapping(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M5678")
        assert store.get_dooray_member_id("U1234") == "M5678"
        store.close()

    def test_get_nonexistent_mapping(self) -> None:
        store = DoorayStore()
        assert store.get_dooray_member_id("UNKNOWN") is None
        store.close()

    def test_update_mapping(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M_OLD")
        store.set_user_mapping("U1234", "M_NEW")
        assert store.get_dooray_member_id("U1234") == "M_NEW"
        store.close()

    def test_remove_mapping(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M5678")
        store.remove_user_mapping("U1234")
        assert store.get_dooray_member_id("U1234") is None
        store.close()


# --- DoorayViews Tests ---


class TestDoorayViews:
    def test_usage_modal(self) -> None:
        modal = build_dooray_usage_modal()
        assert modal["type"] == "modal"
        text = modal["blocks"][0]["text"]["text"]
        assert "/dooray me" in text
        assert "/dooray create" in text

    def test_task_list_modal_empty(self) -> None:
        modal = build_dooray_task_list_modal([])
        assert modal["type"] == "modal"
        assert "없습니다" in modal["blocks"][0]["text"]["text"]

    def test_task_list_modal_with_tasks(self) -> None:
        tasks = [
            DoorayTask(
                id="T1",
                project_id="P1",
                subject="Task 1",
                workflow_name="진행중",
                workflow_class="working",
                users_to=[],
            ),
        ]
        modal = build_dooray_task_list_modal(tasks)
        assert modal["type"] == "modal"
        sections = [b for b in modal["blocks"] if b["type"] == "section"]
        assert len(sections) == 1
        assert "Task 1" in sections[0]["text"]["text"]

    def test_create_task_modal_has_fields(self) -> None:
        modal = build_dooray_create_task_modal()
        block_ids = [b["block_id"] for b in modal["blocks"]]
        assert "subject_block" in block_ids
        assert "body_block" in block_ids
        assert "tag_block" in block_ids
        assert "due_date_block" in block_ids
        assert "assignee_block" not in block_ids
        assert "project_block" not in block_ids

    def test_result_modal(self) -> None:
        modal = build_dooray_result_modal("제목", "내용입니다")
        assert modal["type"] == "modal"
        assert modal["title"]["text"] == "제목"
        assert "내용입니다" in modal["blocks"][0]["text"]["text"]

    def test_setup_modal(self) -> None:
        modal = build_dooray_setup_modal()
        assert modal["callback_id"] == "dooray_setup_modal"
        block_ids = [b.get("block_id") for b in modal["blocks"] if "block_id" in b]
        assert "search_name_block" in block_ids

    def test_setup_select_modal_empty(self) -> None:
        modal = build_dooray_setup_select_modal([])
        assert "submit" not in modal
        assert "없습니다" in modal["blocks"][0]["text"]["text"]

    def test_setup_select_modal_with_members(self) -> None:
        members = [DoorayMember(id="M1", name="홍길동", email="hong@test.com")]
        modal = build_dooray_setup_select_modal(members)
        assert modal["callback_id"] == "dooray_setup_select_modal"
        options = modal["blocks"][0]["element"]["options"]
        assert len(options) == 1
        assert options[0]["value"] == "M1"

    def test_member_search_modal_empty(self) -> None:
        modal = build_dooray_member_search_modal([])
        assert modal["type"] == "modal"
        assert "없습니다" in modal["blocks"][0]["text"]["text"]

    def test_member_search_modal_with_results(self) -> None:
        members = [DoorayMember(id="M1", name="홍길동", email="hong@test.com")]
        modal = build_dooray_member_search_modal(members)
        sections = [b for b in modal["blocks"] if b["type"] == "section"]
        assert len(sections) == 1
        assert "홍길동" in sections[0]["text"]["text"]

    def test_error_modal(self) -> None:
        modal = build_dooray_error_modal("something broke")
        assert modal["type"] == "modal"
        assert "something broke" in modal["blocks"][0]["text"]["text"]

    def test_not_linked_modal(self) -> None:
        modal = build_dooray_not_linked_modal()
        assert modal["type"] == "modal"
        assert "연결되지" in modal["blocks"][0]["text"]["text"]

    def test_create_task_modal_with_tags_dropdown(self) -> None:
        modal = build_dooray_create_task_modal(tags=_SAMPLE_TAGS)
        tag_block = next(b for b in modal["blocks"] if b["block_id"] == "tag_block")
        element = tag_block["element"]
        assert element["type"] == "multi_static_select"
        assert len(element["options"]) == 2
        assert element["options"][0]["value"] == "TAG1"


# --- DoorayService Tests ---


class TestDoorayService:
    def _make_service(
        self,
        store: DoorayStore | None = None,
        client: DoorayClient | None = None,
    ) -> DoorayService:
        if store is None:
            store = DoorayStore()
        if client is None:
            mock_http = _make_mock_client()
            client = DoorayClient("token", http_client=mock_http)
        return DoorayService(dooray_client=client, store=store, default_project_id="P_DEFAULT")

    def test_get_my_tasks_not_linked(self) -> None:
        service = self._make_service()
        try:
            service.get_my_tasks("UNKNOWN_USER")
            assert False, "Should have raised"
        except UserNotLinkedError:
            pass

    def test_get_my_tasks_success(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M5678")
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "id": "T1",
                    "subject": "My task",
                    "workflowClass": {"name": "진행중", "class": "working"},
                    "users": {"to": []},
                },
            ],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        service = self._make_service(store=store, client=client)

        tasks = service.get_my_tasks("U1234")
        assert len(tasks) == 1

    def test_get_my_tasks_api_error(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M5678")
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        service = self._make_service(store=store, client=client)

        try:
            service.get_my_tasks("U1234")
            assert False, "Should have raised"
        except DoorayServiceError:
            pass

    def test_create_task_with_extra_fields(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "T_NEW"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        service = self._make_service(client=client)

        task = service.create_task(
            subject="New task",
            tag_ids=["TAG1"],
            due_date="2026-03-01",
        )
        assert task.id == "T_NEW"

    def test_setup_user(self) -> None:
        store = DoorayStore()
        service = self._make_service(store=store)
        service.setup_user("U1234", "M5678")
        assert store.get_dooray_member_id("U1234") == "M5678"

    def test_search_members(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [{"id": "M1", "name": "홍길동", "email": "hong@test.com"}],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        service = self._make_service(client=client)

        members = service.search_members("홍")
        assert len(members) == 1

    def test_list_project_tags(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [{"id": "TAG1", "name": "버그", "color": "red"}],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        service = self._make_service(client=client)

        tags = service.list_project_tags()
        assert len(tags) == 1
        assert tags[0].name == "버그"



# --- DoorayCommands Integration Tests ---


class TestDoorayCommands:
    def test_no_subcommand_opens_usage_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert view["type"] == "modal"
            assert "사용법" in view["blocks"][0]["text"]["text"]

    def test_me_not_linked_opens_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=me&user_id=U_UNKNOWN&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            time.sleep(0.5)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert "연결되지" in view["blocks"][0]["text"]["text"]

    def test_me_success_opens_task_list_modal(self) -> None:
        store = DoorayStore()
        store.set_user_mapping("U1234", "M5678")
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [
                {
                    "id": "T1",
                    "subject": "My task",
                    "workflowClass": {"name": "진행중", "class": "working"},
                    "users": {"to": []},
                },
            ],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_store=store, dooray_client=client)

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=me&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            time.sleep(0.5)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert view["type"] == "modal"
            assert view["title"]["text"] == "내 업무 목록"

    def test_create_opens_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=create&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            time.sleep(0.5)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert view["callback_id"] == "dooray_create_task_modal"

    def test_setup_no_args_opens_setup_modal(self) -> None:
        app = _create_test_app()
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=setup&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert view["callback_id"] == "dooray_setup_modal"

    def test_setup_with_id_registers_and_opens_modal(self) -> None:
        store = DoorayStore()
        app = _create_test_app(dooray_store=store)
        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=setup+M9999&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            time.sleep(0.5)
            assert response.status == 200
            assert store.get_dooray_member_id("U1234") == "M9999"
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert "M9999" in view["blocks"][0]["text"]["text"]

    def test_setup_search_opens_modal(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [{"id": "M1", "name": "홍길동", "email": "hong@example.com"}],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        with patch("slack_sdk.web.client.WebClient.views_open") as mock_open:
            request = BoltRequest(
                body="command=%2Fdooray&text=setup+search+%ED%99%8D&user_id=U1234&trigger_id=T123&channel_id=C1234",
                headers={"content-type": ["application/x-www-form-urlencoded"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            mock_open.assert_called_once()
            view = mock_open.call_args.kwargs["view"]
            assert view["type"] == "modal"


class TestDooraySetupFlow:
    def test_setup_modal_search_updates_to_select(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": [{"id": "M1", "name": "홍길동", "email": "hong@test.com"}],
        }
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_setup_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "search_name_block": {
                            "search_name_input": {"value": "홍"},
                        },
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        request = BoltRequest(
            body=json.dumps(view_payload),
            headers={"content-type": ["application/json"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        # response_action="update" returns the new view in the body
        body_data = json.loads(response.body) if response.body else {}
        assert body_data.get("response_action") == "update"

    def test_setup_select_modal_saves_mapping(self) -> None:
        store = DoorayStore()
        app = _create_test_app(dooray_store=store)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_setup_select_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "member_select_block": {
                            "member_select_input": {
                                "selected_option": {
                                    "text": {"type": "plain_text", "text": "홍길동"},
                                    "value": "M_SELECTED",
                                },
                            },
                        },
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        with patch("slack_sdk.web.client.WebClient.chat_postMessage") as mock_post:
            request = BoltRequest(
                body=json.dumps(view_payload),
                headers={"content-type": ["application/json"]},
            )
            response = app.dispatch(request)
            assert response.status == 200
            time.sleep(0.5)
            assert store.get_dooray_member_id("U1234") == "M_SELECTED"
            mock_post.assert_called_once()
            assert "연결되었습니다" in mock_post.call_args.kwargs.get("text", "")


class TestDoorayCreateTaskModal:
    def test_modal_submission_with_all_fields(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "T_NEW"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_create_task_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "subject_block": {"subject_input": {"value": "New Task"}},
                        "body_block": {"body_input": {"value": "Details"}},
                        "tag_block": {"tag_input": {"value": "TAG1, TAG2"}},
                        "due_date_block": {"due_date_input": {"selected_date": "2026-03-01"}},
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        request = BoltRequest(
            body=json.dumps(view_payload),
            headers={"content-type": ["application/json"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        body_data = json.loads(response.body) if response.body else {}
        assert body_data.get("response_action") == "update"
        view = body_data.get("view", {})
        assert "T_NEW" in view["blocks"][0]["text"]["text"]

    def test_modal_submission_with_dropdown_selections(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "T_DROP"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_create_task_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "subject_block": {"subject_input": {"value": "Dropdown Task"}},
                        "body_block": {"body_input": {"value": None}},
                        "tag_block": {
                            "tag_input": {
                                "type": "multi_static_select",
                                "selected_options": [
                                    {"text": {"type": "plain_text", "text": "버그"}, "value": "TAG1"},
                                ],
                            },
                        },
                        "due_date_block": {"due_date_input": {"selected_date": None}},
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        request = BoltRequest(
            body=json.dumps(view_payload),
            headers={"content-type": ["application/json"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        body_data = json.loads(response.body) if response.body else {}
        assert body_data.get("response_action") == "update"
        assert "T_DROP" in body_data["view"]["blocks"][0]["text"]["text"]
        call_kwargs = mock_http.request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["tagIds"] == ["TAG1"]

    def test_modal_submission_minimal(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"id": "T_MIN"}}
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_create_task_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "subject_block": {"subject_input": {"value": "Simple Task"}},
                        "body_block": {"body_input": {"value": None}},
                        "tag_block": {"tag_input": {"value": None}},
                        "due_date_block": {"due_date_input": {"selected_date": None}},
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        request = BoltRequest(
            body=json.dumps(view_payload),
            headers={"content-type": ["application/json"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        body_data = json.loads(response.body) if response.body else {}
        assert body_data.get("response_action") == "update"
        assert "T_MIN" in body_data["view"]["blocks"][0]["text"]["text"]

    def test_modal_submission_error_shows_error_modal(self) -> None:
        mock_http = _make_mock_client()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http.request.return_value = mock_response
        client = DoorayClient("token", http_client=mock_http)
        app = _create_test_app(dooray_client=client)

        view_payload = {
            "type": "view_submission",
            "user": {"id": "U1234"},
            "view": {
                "type": "modal",
                "callback_id": "dooray_create_task_modal",
                "private_metadata": "",
                "state": {
                    "values": {
                        "subject_block": {"subject_input": {"value": "Fail Task"}},
                        "body_block": {"body_input": {"value": None}},
                        "tag_block": {"tag_input": {"value": None}},
                        "due_date_block": {"due_date_input": {"selected_date": None}},
                    },
                },
            },
            "token": "test-token",
            "team": {"id": "T1234"},
        }

        request = BoltRequest(
            body=json.dumps(view_payload),
            headers={"content-type": ["application/json"]},
        )
        response = app.dispatch(request)
        assert response.status == 200
        body_data = json.loads(response.body) if response.body else {}
        assert body_data.get("response_action") == "update"
        assert "오류" in body_data["view"]["title"]["text"]


class TestDoorayDisabled:
    def test_dooray_disabled_when_no_token(self) -> None:
        settings = _make_settings(dooray_api_token="", dooray_project_id="")
        with patch("slack_sdk.web.client.WebClient.auth_test", return_value=_MOCK_AUTH_RESPONSE):
            app = create_app(settings, request_verification_enabled=False)
        request = BoltRequest(
            body="command=%2Fdooray&text=me&user_id=U1234&trigger_id=T123&channel_id=C1234",
            headers={"content-type": ["application/x-www-form-urlencoded"]},
        )
        response = app.dispatch(request)
        assert response.status == 404
