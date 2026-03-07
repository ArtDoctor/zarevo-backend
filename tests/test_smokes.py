from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token


def _make_mock_pb_client() -> MagicMock:
    mock = MagicMock(spec=PocketBaseClient)
    mock.get_current_user_id.return_value = "user-123"
    mock.get_auth_token.return_value = "token"
    mock.client = MagicMock()
    return mock


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_create_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/smokes/create",
        json={
            "idea_id": "idea-1",
            "CTA": "Sign up now",
            "features": [
                {
                    "feature": "X",
                    "description": "Y",
                    "expected_signup_increase_pct": 10.0,
                },
            ],
            "images": [],
        },
    )
    assert response.status_code == 401


@patch("src.routers.smokes.process_smoke_generation_task")
def test_create_success_returns_id(mock_task: MagicMock, client: TestClient) -> None:
    mock_pb = _make_mock_pb_client()
    mock_record = MagicMock()
    mock_record.id = "smoke-123"
    mock_pb.client.collection.return_value.create.return_value = mock_record
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/smokes/create",
            json={
                "idea_id": "idea-456",
                "CTA": "Get early access",
                "features": [
                    {
                        "feature": "Automated ads",
                        "description": "Set up ads in minutes",
                        "expected_signup_increase_pct": 18.0,
                    },
                ],
                "images": ["https://example.com/img1.png"],
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200
        assert response.json() == {"id": "smoke-123"}
        create_call = mock_pb.client.collection.return_value.create.call_args
        assert create_call is not None
        passed_data = create_call[0][0] if create_call[0] else create_call[1]
        assert passed_data["idea"] == "idea-456"
        assert passed_data["cta"] == "Get early access"
        assert passed_data["state"] == "in_progress"
        assert len(passed_data["features"]) == 1
        assert passed_data["images"] == ["https://example.com/img1.png"]
        mock_task.delay.assert_called_once_with("smoke-123", "token")
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


def test_publish_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/smokes/publish",
        json={
            "smoke_id": "smoke-1",
            "duration": 6,
            "subdomain": "my-app",
            "start_date": "2025-03-10",
            "ads_channels": [
                {"channel": "google", "advertised": "yes"},
                {"channel": "meta", "advertised": "no"},
            ],
        },
    )
    assert response.status_code == 401


def test_publish_insufficient_credits_returns_402(client: TestClient) -> None:
    mock_pb = _make_mock_pb_client()
    mock_pb.get_user_credits.return_value = 1
    mock_smoke = MagicMock()
    mock_smoke.idea = "idea-1"
    mock_idea = MagicMock()
    mock_idea.author = "user-123"
    mock_pb.client.collection.return_value.get_one.side_effect = [mock_smoke, mock_idea]
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/smokes/publish",
            json={
                "smoke_id": "smoke-1",
                "duration": 6,
                "subdomain": "my-app",
                "start_date": "2025-03-10",
                "ads_channels": [
                    {"channel": "google", "advertised": "yes"},
                    {"channel": "meta", "advertised": "yes"},
                ],
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]
        mock_pb.deduct_user_credits.assert_not_called()
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


def test_publish_forbidden_when_not_owner(client: TestClient) -> None:
    mock_pb = _make_mock_pb_client()
    mock_pb.get_user_credits.return_value = 10
    mock_smoke = MagicMock()
    mock_smoke.idea = "idea-1"
    mock_idea = MagicMock()
    mock_idea.author = "other-user"
    mock_pb.client.collection.return_value.get_one.side_effect = [mock_smoke, mock_idea]
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/smokes/publish",
            json={
                "smoke_id": "smoke-1",
                "duration": 3,
                "subdomain": "my-app",
                "start_date": "2025-03-10",
                "ads_channels": [{"channel": "google", "advertised": "yes"}],
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]
        mock_pb.deduct_user_credits.assert_not_called()
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)


def test_publish_success_deducts_credits_and_updates_smoke(client: TestClient) -> None:
    deduct_called: list[int] = []
    mock_pb = _make_mock_pb_client()
    mock_pb.get_user_credits.return_value = 10

    def capture_deduct(uid: str, amount: int) -> None:
        deduct_called.append(amount)

    mock_pb.deduct_user_credits.side_effect = capture_deduct

    mock_smoke = MagicMock()
    mock_smoke.idea = "idea-1"
    mock_idea = MagicMock()
    mock_idea.author = "user-123"
    mock_pb.client.collection.return_value.get_one.side_effect = [mock_smoke, mock_idea]
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/smokes/publish",
            json={
                "smoke_id": "smoke-1",
                "duration": 6,
                "subdomain": "my-landing",
                "start_date": "2025-03-10",
                "ads_channels": [
                    {"channel": "google", "advertised": "yes"},
                    {"channel": "meta", "advertised": "yes"},
                ],
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200
        assert response.json() == {"message": "Smoke published"}
        assert deduct_called == [4]
        update_call = mock_pb.client.collection.return_value.update.call_args
        assert update_call[0][0] == "smoke-1"
        assert update_call[0][1]["domain"] == "my-landing"
        assert update_call[0][1]["duration"] == 6
        assert update_call[0][1]["start_date"] == "2025-03-10"
        assert update_call[0][1]["ad_channels"] == [
            {"channel": "google", "advertised": "yes"},
            {"channel": "meta", "advertised": "yes"},
        ]
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)
