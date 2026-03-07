from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token


def _make_mock_pb_client(
    user_id: str = "user-123",
    credits: int = 10,
    deduct_called: list[int] | None = None,
) -> MagicMock:
    mock = MagicMock(spec=PocketBaseClient)
    mock.get_current_user_id.return_value = user_id
    mock.get_user_credits.return_value = credits
    mock.get_auth_token.return_value = "token"

    if deduct_called is None:
        deduct_called = []

    def capture_deduct(uid: str, amount: int) -> None:
        deduct_called.append(amount)

    mock.deduct_user_credits.side_effect = capture_deduct

    mock.client = MagicMock()
    call_count = [0]

    def create_record(data: dict) -> MagicMock:
        call_count[0] += 1
        if "analyses" in data:
            return MagicMock(id="idea-1")
        return MagicMock(id=f"analysis-{call_count[0]}")

    mock.client.collection.return_value.create.side_effect = create_record
    mock.client.collection.return_value.delete = MagicMock()

    return mock


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_submit_idea_insufficient_credits_returns_402(client: TestClient) -> None:
    mock_pb = _make_mock_pb_client(credits=0)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new",
            json={
                "description": "Test idea",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]
        mock_pb.deduct_user_credits.assert_not_called()
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


def test_submit_idea_advanced_insufficient_credits_returns_402(client: TestClient) -> None:
    mock_pb = _make_mock_pb_client(credits=2)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new/advanced",
            json={
                "description": "Test idea",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]
        assert "4" in response.json()["detail"]
        mock_pb.deduct_user_credits.assert_not_called()
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


@patch("src.routers.ideas.process_features_task")
@patch("src.routers.ideas.process_idea_task")
@patch("src.routers.ideas.process_title_task")
def test_submit_idea_deducts_1_credit_after_success(
    mock_title_task: MagicMock,
    mock_idea_task: MagicMock,
    mock_features_task: MagicMock,
    client: TestClient,
) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client(credits=10, deduct_called=deduct_called)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new",
            json={
                "description": "Test idea",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 200
        assert deduct_called == [1]
        mock_features_task.delay.assert_not_called()
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


@patch("src.routers.ideas.process_features_task")
@patch("src.routers.ideas.process_idea_task")
@patch("src.routers.ideas.process_title_task")
def test_submit_idea_advanced_deducts_4_credits_after_success(
    mock_title_task: MagicMock,
    mock_idea_task: MagicMock,
    mock_features_task: MagicMock,
    client: TestClient,
) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client(credits=10, deduct_called=deduct_called)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new/advanced",
            json={
                "description": "Test idea",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 200
        assert deduct_called == [4]
        mock_features_task.delay.assert_called_once_with("idea-1", "token")
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


@patch("src.routers.ideas.process_idea_task")
@patch("src.routers.ideas.process_title_task")
def test_submit_idea_does_not_deduct_credits_when_description_is_test(
    mock_title_task: MagicMock,
    mock_idea_task: MagicMock,
    client: TestClient,
) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client(credits=0, deduct_called=deduct_called)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new",
            json={
                "description": "test",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 200
        assert deduct_called == []
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


@patch("src.routers.ideas.process_features_task")
@patch("src.routers.ideas.process_idea_task")
@patch("src.routers.ideas.process_title_task")
def test_submit_idea_advanced_does_not_deduct_credits_when_description_is_test(
    mock_title_task: MagicMock,
    mock_idea_task: MagicMock,
    mock_features_task: MagicMock,
    client: TestClient,
) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client(credits=0, deduct_called=deduct_called)
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new/advanced",
            json={
                "description": "test",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 200
        assert deduct_called == []
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


@patch("src.routers.ideas.process_idea_task")
@patch("src.routers.ideas.process_title_task")
def test_submit_idea_does_not_deduct_on_create_failure(
    mock_title_task: MagicMock,
    mock_idea_task: MagicMock,
    client: TestClient,
) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client(credits=10, deduct_called=deduct_called)
    call_count = [0]

    def create_raise_on_idea(data: dict) -> MagicMock:
        call_count[0] += 1
        if "analyses" in data:
            raise Exception("PocketBase error")
        return MagicMock(id=f"analysis-{call_count[0]}")

    mock_pb.client.collection.return_value.create.side_effect = create_raise_on_idea
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/ideas/new",
            json={
                "description": "Test idea",
                "problem": "",
                "customer": "",
                "founder_specific": "",
            },
        )
        assert response.status_code == 500
        assert deduct_called == []
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)
