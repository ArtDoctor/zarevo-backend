from unittest.mock import patch

from src.ai_utils.vertex_utils import VertexResponse
from src.analyses.competitor.competitor import (
    CompetitorDiscoveryResponse,
    CompetitorEntry,
    CompetitorScoreResponse,
    get_competitor_analysis,
)


def test_competitor_analysis_pipeline_orders_steps_and_matches_schema() -> None:
    calls: list[str] = []

    def fake_structured(prompt: str, response_model, *args, **kwargs):
        if response_model is CompetitorDiscoveryResponse:
            calls.append("discovery")
            return CompetitorDiscoveryResponse(
                competitors=[
                    CompetitorEntry(
                        name="Competitor A",
                        description="Leading SaaS in the space.",
                        revenue="~$30M ARR",
                        features="Core features X, Y, Z",
                        strengths="Strong brand, enterprise focus",
                        weaknesses="High price, complex setup",
                        online_presence="LinkedIn, Twitter, website",
                    ),
                    CompetitorEntry(
                        name="Competitor B",
                        description="Emerging alternative.",
                        revenue="Series A, ~$5M",
                        features="Features A, B",
                        strengths="Modern UX, fast deployment",
                        weaknesses="Limited integrations",
                        online_presence="Website, Product Hunt",
                    ),
                ]
            )
        if response_model is CompetitorScoreResponse:
            calls.append("synthesis")
            return CompetitorScoreResponse(score=72)
        raise AssertionError("Unexpected response_model")

    def fake_response(prompt: str, *args, **kwargs) -> VertexResponse:
        if "overview" in prompt.lower() or "competitive landscape" in prompt.lower():
            calls.append("overview")
            return VertexResponse(
                text="The competitive landscape is moderately crowded with clear leaders and room for differentiation.",
                links=["https://example.com/competitor-source"],
            )
        raise AssertionError("Unexpected prompt for fake_response")

    with (
        patch(
            "src.analyses.competitor.competitor.get_vertex_structured",
            side_effect=fake_structured,
        ),
        patch(
            "src.analyses.competitor.competitor.get_vertex_response",
            side_effect=fake_response,
        ),
    ):
        result = get_competitor_analysis(
            {
                "description": "AI tool to optimize warehouse picking routes",
                "problem": "Inefficient picking increases labor cost",
                "customer": "Warehouse ops teams",
                "geography": "US/EU",
                "founder_specific": "",
            }
        )

    assert "discovery" in calls
    assert "overview" in calls
    assert "synthesis" in calls
    assert len(result.competitors) == 2
    assert result.competitors[0].name == "Competitor A"
    assert result.overview
    assert result.sources
    assert 0 <= result.score <= 100
