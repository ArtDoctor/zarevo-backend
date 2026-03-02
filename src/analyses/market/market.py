from pathlib import Path

from pydantic import BaseModel


class MarketEntry(BaseModel):
    name: str
    growth_rate: str
    sizes_2023_2026_in_millions: list[int]


class MarketAnalysis(BaseModel):
    overview: str
    trends_analysis: str
    markets: list[MarketEntry]
    strengths: list[str]
    weaknesses: list[str]
    gaps_and_opportunities: list[str]
    threats: list[str]
    new_market_potential: str
    why_now: str
    score: int


def get_market_analysis() -> MarketAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return MarketAnalysis.model_validate_json(content)
