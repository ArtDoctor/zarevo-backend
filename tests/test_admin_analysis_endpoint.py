from fastapi.testclient import TestClient

from src.main import app


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    import base64

    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_admin_get_analysis_requires_basic_auth() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/admin/analysis",
        json={"analysis_type": "competitor", "description": "test"},
    )
    assert res.status_code == 401


def test_admin_get_analysis_rejects_wrong_basic_auth() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/admin/analysis",
        json={"analysis_type": "competitor", "description": "test"},
        headers=_basic_auth_header("admin", "wrong"),
    )
    assert res.status_code == 401


def test_admin_get_analysis_returns_competitor_analysis_with_auth() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/admin/analysis",
        json={
            "analysis_type": "competitor",
            "description": "test",
            "problem": "p",
            "customer": "c",
            "geography": "g",
            "founder_specific": "f",
        },
        headers=_basic_auth_header("admin", "admin"),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "competitor"
    assert "result" in body
    assert "overview" in body["result"]
    assert "competitors" in body["result"]
    assert "score" in body["result"]


def test_admin_get_analysis_unknown_type_returns_404() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/admin/analysis",
        json={"analysis_type": "not-a-real-type", "description": "test"},
        headers=_basic_auth_header("admin", "admin"),
    )
    assert res.status_code == 404


def test_admin_get_analysis_rejects_short_description() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/admin/analysis",
        json={
            "analysis_type": "market",
            "description": "ab",
            "problem": "",
            "customer": "",
            "geography": "",
            "founder_specific": "",
        },
        headers=_basic_auth_header("admin", "admin"),
    )
    assert res.status_code == 400
    assert "at least" in res.json()["detail"].lower()

