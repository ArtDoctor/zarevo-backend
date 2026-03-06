from unittest.mock import patch

from src.analyses.legal.legal import LegalAnalysis, get_legal_analysis


def test_legal_analysis_pipeline_returns_valid_schema() -> None:
    def fake_structured(prompt: str, response_model, *args, **kwargs):
        if response_model is LegalAnalysis:
            return LegalAnalysis(
                overview="Standard B2B SaaS with moderate regulatory exposure.",
                GDPR_compliance="Requires consent and data processing agreements.",
                EU_AI_compliance="Likely limited risk under EU AI Act.",
                score=72,
            )
        raise AssertionError("Unexpected response_model")

    with patch(
        "src.analyses.legal.legal.get_openai_structured",
        side_effect=fake_structured,
    ):
        result = get_legal_analysis(
            {
                "description": "AI tool to optimize warehouse picking routes",
                "problem": "Inefficient picking",
                "customer": "Warehouse ops",
                "geography": "EU",
                "founder_specific": "",
            }
        )

    assert isinstance(result, LegalAnalysis)
    assert result.overview
    assert result.GDPR_compliance
    assert result.EU_AI_compliance
    assert 0 <= result.score <= 100
