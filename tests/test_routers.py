from fastapi.testclient import TestClient


def test_test_api_submit_idea(client: TestClient) -> None:
    response = client.post(
        "/test-api/ideas",
        json={
            "title": "Test Idea",
            "description": "Test description",
            "user_id": "user-123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Processing started"
    assert data["idea_id"] == 1
    assert data["task_id"] == 1


def test_test_api_check_result(client: TestClient) -> None:
    response = client.get("/test-api/ideas/123/result")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "123"
    assert data["status"] == "completed"
    assert data["result"]["analysis"] == "Market looks favorable."
