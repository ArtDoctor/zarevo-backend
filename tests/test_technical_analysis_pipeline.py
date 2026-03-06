from unittest.mock import patch

from src.analyses.technical.technical import TechnicalAnalysis, get_technical_analysis


def test_technical_analysis_pipeline_returns_valid_schema() -> None:
    def fake_structured(prompt: str, response_model, *args, **kwargs):
        if response_model is TechnicalAnalysis:
            return TechnicalAnalysis(
                toughness=4,
                overview="Moderate technical complexity with standard web stack.",
                suggested_tech_stack="Python/FastAPI backend, React frontend, PostgreSQL.",
                scaling_considertions="Horizontal scaling via load balancers; consider caching.",
                no_code_viability="Not viable without code; requires custom logic.",
                ideal_team="1 full-stack developer, 1 designer.",
                strengths=["Proven stack", "Clear architecture"],
                weaknesses=["Scaling at high load"],
                score=75,
            )
        raise AssertionError("Unexpected response_model")

    with patch(
        "src.analyses.technical.technical.get_openai_structured",
        side_effect=fake_structured,
    ):
        result = get_technical_analysis(
            {
                "description": "AI tool to optimize warehouse picking routes",
                "problem": "Inefficient picking",
                "customer": "Warehouse ops",
                "geography": "",
                "founder_specific": "",
            }
        )

    assert isinstance(result, TechnicalAnalysis)
    assert result.toughness == 4
    assert result.overview
    assert result.suggested_tech_stack
    assert result.scaling_considertions
    assert result.no_code_viability
    assert result.ideal_team
    assert result.strengths
    assert result.weaknesses
    assert 0 <= result.score <= 100
