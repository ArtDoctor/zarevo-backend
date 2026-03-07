from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token


def _make_mock_pb_client() -> MagicMock:
    mock = MagicMock(spec=PocketBaseClient)
    mock.get_current_user_id.return_value = "user-123"
    mock.client = MagicMock()
    return mock


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_create_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/smokes/create",
        json={
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


def test_create_success_returns_id(client: TestClient) -> None:
    mock_pb = _make_mock_pb_client()
    mock_record = MagicMock()
    mock_record.id = "smoke-123"
    mock_pb.client.collection.return_value.create.return_value = mock_record
    app.dependency_overrides[verify_pocketbase_token] = lambda: mock_pb

    try:
        response = client.post(
            "/api/smokes/create",
            json={
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
        assert passed_data["cta"] == "Get early access"
        assert passed_data["state"] == "queued"
        assert len(passed_data["features"]) == 1
        assert passed_data["images"] == ["https://example.com/img1.png"]
    finally:
        app.dependency_overrides.pop(verify_pocketbase_token, None)
