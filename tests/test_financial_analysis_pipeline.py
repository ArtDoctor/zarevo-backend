from unittest.mock import patch

from src.analyses.financial.financial import FinancialAnalysis, get_financial_analysis


def test_financial_analysis_pipeline_returns_valid_schema() -> None:
    def fake_structured(prompt: str, response_model, *args, **kwargs):
        if response_model is FinancialAnalysis:
            return FinancialAnalysis(
                start_capital_needed="80,000 USD",
                costs_overview="Development and initial marketing costs.",
                investor_requirements="Seed stage suitable; angel or pre-seed.",
                investor_concerns="Market size and competition.",
                overview="Moderate capital needs with clear path to revenue.",
            )
        raise AssertionError("Unexpected response_model")

    with patch(
        "src.analyses.financial.financial.get_openai_structured",
        side_effect=fake_structured,
    ):
        result = get_financial_analysis(
            {
                "description": "AI tool to optimize warehouse picking routes",
                "problem": "Inefficient picking",
                "customer": "Warehouse ops",
                "geography": "",
                "founder_specific": "",
            }
        )

    assert isinstance(result, FinancialAnalysis)
    assert result.start_capital_needed
    assert result.costs_overview
    assert result.investor_requirements
    assert result.investor_concerns
    assert result.overview
