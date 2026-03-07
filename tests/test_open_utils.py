import pytest
from unittest.mock import MagicMock, patch

from src.ai_utils.open_utils import generate_landing_page
from src.smokes.models import SmokeFeature, SmokeInput


def test_generate_landing_page_returns_predefined_when_idea_is_test() -> None:
    smoke_input = SmokeInput(
        idea_description="test",
        cta="Sign up",
        features=[
            SmokeFeature(
                feature="X",
                description="Y",
                expected_signup_increase_pct=10.0,
            ),
        ],
        images=[],
    )
    result = generate_landing_page(smoke_input)
    assert "Test Product" in result.html
    assert "signup-btn" in result.html
    assert "addEventListener" in result.html
    assert result.css == ""
    assert result.js == ""


@patch("src.ai_utils.open_utils.ChatOpenRouter")
def test_generate_landing_page_returns_html_from_model(mock_router: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.content = """<!DOCTYPE html>
<html><head><title>My Product</title></head>
<body><h1>Sign up</h1></body></html>"""
    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response
    mock_router.return_value = mock_model

    smoke_input = SmokeInput(
        idea_description="AI tool for X",
        cta="Get started",
        features=[
            SmokeFeature(
                feature="Fast",
                description="Very fast",
                expected_signup_increase_pct=5.0,
            ),
        ],
        images=[],
    )
    result = generate_landing_page(smoke_input)
    assert "<!DOCTYPE html>" in result.html
    assert "My Product" in result.html
    assert result.css == ""
    assert result.js == ""


@patch("src.ai_utils.open_utils.ChatOpenRouter")
def test_generate_landing_page_extracts_html_from_markdown_code_block(
    mock_router: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.content = """```html
<!DOCTYPE html>
<html><head><title>Wrapped</title></head>
<body><p>Content</p></body></html>
```"""
    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response
    mock_router.return_value = mock_model

    smoke_input = SmokeInput(
        idea_description="AI tool",
        cta="Sign up",
        features=[],
        images=[],
    )
    result = generate_landing_page(smoke_input)
    assert "<!DOCTYPE html>" in result.html
    assert "Wrapped" in result.html


@patch("src.ai_utils.open_utils.ChatOpenRouter")
def test_generate_landing_page_raises_when_model_returns_invalid_html(
    mock_router: MagicMock,
) -> None:
    mock_response = MagicMock()
    mock_response.content = "Here is some text but no HTML."
    mock_model = MagicMock()
    mock_model.invoke.return_value = mock_response
    mock_router.return_value = mock_model

    smoke_input = SmokeInput(
        idea_description="AI tool for X",
        cta="Get started",
        features=[],
        images=[],
    )
    with pytest.raises(ValueError, match="did not return valid HTML"):
        generate_landing_page(smoke_input)
