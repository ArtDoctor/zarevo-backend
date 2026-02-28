import pytest
from pydantic import ValidationError

from src.config import IdeaRequest


def test_idea_request_valid() -> None:
    data = IdeaRequest(
        title="Test Idea",
        description="A test description",
        user_id="user-123"
    )
    assert data.title == "Test Idea"
    assert data.description == "A test description"
    assert data.user_id == "user-123"


def test_idea_request_missing_field() -> None:
    with pytest.raises(ValidationError):
        IdeaRequest(
            title="Test",
            description="A test description"
        )
