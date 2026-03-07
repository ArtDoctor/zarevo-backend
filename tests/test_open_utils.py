import pytest

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
    assert "styles.css" in result.html
    assert "script.js" in result.html
    assert "signup-btn" in result.css or "button" in result.css
    assert "addEventListener" in result.js
