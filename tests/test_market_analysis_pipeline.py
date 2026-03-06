from unittest.mock import patch

from src.ai_utils.vertex_utils import VertexResponse
from src.analyses.market.market import (
    AdditionalMarketCandidate,
    AdditionalMarketCandidatesResponse,
    MarketAnalysis,
    MarketSizing,
    MarketSizingResponse,
    MarketSynthesisRemaining,
    StrengthsResponse,
    WeaknessesResponse,
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

        if response_model is StrengthsResponse:
            calls.append("strengths")
            return StrengthsResponse(
                strengths=["Large and growing budgets", "Clear ROI-driven purchasing"],
            )

        if response_model is WeaknessesResponse:
            calls.append("weaknesses")
            return WeaknessesResponse(
                weaknesses=["Long enterprise sales cycles", "Integration complexity"],
            )

        if response_model is MarketSynthesisRemaining:
            calls.append("remaining")
            return MarketSynthesisRemaining(
                gaps_and_opportunities=[
                    "Mid-market solutions with fast deployment",
                    "Better analytics for warehouse ops",
                ],
                threats=["Incumbent WMS vendors expanding", "Economic slowdowns delaying capex"],
                theoretical_market_share_pct="1-2%",
                new_market_potential="Low; this is an existing category, but a wedge can exist in underserved segments.",
                why_now="Labor constraints and e-commerce SLAs are pushing automation adoption.",
                score=78,
            )

        raise AssertionError("Unexpected response_model")

    def fake_response(prompt: str, *args, **kwargs) -> VertexResponse:
        if "overview" in prompt.lower() or "market overview" in prompt.lower():
            calls.append("overview")
            return VertexResponse(
                text="The market is growing with clear buyer budgets and increasing automation adoption.",
                links=["https://example.com/overview-source"],
            )
        if "trends" in prompt.lower():
            calls.append("trends")
            return VertexResponse(
                text="Warehouses are investing in automation due to labor shortages and e-commerce expectations.",
                links=["https://example.com/trends-source"],
            )
        raise AssertionError("Unexpected prompt for fake_response")

    with (
        patch("src.analyses.market.market.get_vertex_structured", side_effect=fake_structured),
        patch("src.analyses.market.market.get_vertex_response", side_effect=fake_response),
    ):
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
    assert "discover" in calls
    assert "size" in calls
    assert "overview" in calls
    assert "trends" in calls
    assert "strengths" in calls
    assert "weaknesses" in calls
    assert "remaining" in calls
    assert result.overview
    assert result.trends_analysis
    assert result.sources
    assert result.theoretical_market_share_pct
    assert result.strengths
    assert result.weaknesses
    assert result.gaps_and_opportunities
    assert result.threats
    assert result.why_now
    assert 0 <= result.score <= 100
    assert result.markets

