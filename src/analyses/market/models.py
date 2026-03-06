from pydantic import BaseModel


class IndustryRaw(BaseModel):
    sector: str
    name: str
    sizes: list[int]


class MarketEntry(BaseModel):
    name: str
    sector: str
    growth_rate: str
    sizes_2023_2026_in_millions: list[int]


class MarketAnalysis(BaseModel):
    overview: str
    trends_analysis: str
    sources: list[str]
    markets: list[MarketEntry]
    sectors: list[str]
    average_growth_rate: str
    theoretical_market_share_pct: str
    strengths: list[str]
    weaknesses: list[str]
    gaps_and_opportunities: list[str]
    threats: list[str]
    new_market_potential: str
    why_now: str
    score: int


class MarketSizing(BaseModel):
    name: str
    sector: str
    sizes_2023_2026_in_millions: list[int]
    sources: list[str]


class MarketSizingResponse(BaseModel):
    items: list[MarketSizing]


class StrengthsResponse(BaseModel):
    strengths: list[str]


class WeaknessesResponse(BaseModel):
    weaknesses: list[str]


class MarketSynthesisRemaining(BaseModel):
    gaps_and_opportunities: list[str]
    threats: list[str]
    theoretical_market_share_pct: str
    new_market_potential: str
    why_now: str
    score: int
