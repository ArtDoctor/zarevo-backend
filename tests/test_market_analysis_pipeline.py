from unittest.mock import patch

from src.analyses.market.market import (
    AdditionalMarketCandidate,
    AdditionalMarketCandidatesResponse,
    MarketAnalysis,
    MarketSizing,
    MarketSizingResponse,
    MarketTextSynthesis,
    get_market_analysis,
)


def test_market_analysis_pipeline_orders_steps_and_matches_schema() -> None:
    calls: list[str] = []

    def fake_structured(prompt: str, response_model, *args, **kwargs):
        if response_model is AdditionalMarketCandidatesResponse:
            calls.append("discover")
            return AdditionalMarketCandidatesResponse(
                candidates=[
                    AdditionalMarketCandidate(
                        name="Warehouse automation software",
                        sector="Logistics",
                        why_relevant="Automation improves throughput and reduces labor costs in warehouses.",
                        suggested_search_queries=[
                            "warehouse automation software market size 2023",
                            "warehouse automation CAGR 2024 2026",
                        ],
                    )
                ]
            )

        if response_model is MarketSizingResponse:
            calls.append("size")
            return MarketSizingResponse(
                items=[
                    MarketSizing(
                        name="Warehouse automation software",
                        sector="Logistics",
                        sizes_2023_2026_in_millions=[1200, 1350, 1520, 1710],
                        sources=["https://example.com/report"],
                    )
                ]
            )

        if response_model is MarketTextSynthesis:
            calls.append("synthesize")
            return MarketTextSynthesis(
                overview="The market is growing with clear buyer budgets and increasing automation adoption.",
                trends_analysis="Warehouses are investing in automation due to labor shortages and e-commerce expectations.",
                strengths=["Large and growing budgets", "Clear ROI-driven purchasing"],
                weaknesses=["Long enterprise sales cycles", "Integration complexity"],
                gaps_and_opportunities=[
                    "Mid-market solutions with fast deployment",
                    "Better analytics for warehouse ops",
                ],
                threats=["Incumbent WMS vendors expanding", "Economic slowdowns delaying capex"],
                new_market_potential="Low; this is an existing category, but a wedge can exist in underserved segments.",
                why_now="Labor constraints and e-commerce SLAs are pushing automation adoption.",
                score=78,
            )

        raise AssertionError("Unexpected response_model")

    with patch("src.analyses.market.market.get_vertex_structured", side_effect=fake_structured):
        result = get_market_analysis(
            {
                "description": "AI tool to optimize warehouse picking routes",
                "problem": "Inefficient picking increases labor cost",
                "customer": "Warehouse ops teams",
                "geography": "US/EU",
                "founder_specific": "",
            }
        )

    assert isinstance(result, MarketAnalysis)
    assert calls == ["discover", "size", "synthesize"]
    assert result.overview
    assert result.trends_analysis
    assert result.strengths
    assert result.weaknesses
    assert result.gaps_and_opportunities
    assert result.threats
    assert result.why_now
    assert 0 <= result.score <= 100
    assert result.markets

