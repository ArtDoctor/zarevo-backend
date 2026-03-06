import os

import pytest
from fastapi.testclient import TestClient

from src.main import app


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("POCKETBASE_URL", "http://localhost:8090")
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("VERTEX_AI_API_KEY", "test-key")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
