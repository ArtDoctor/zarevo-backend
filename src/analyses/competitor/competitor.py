from pathlib import Path

from pydantic import BaseModel


class CompetitorEntry(BaseModel):
    name: str
    description: str
    revenue: str
    features: str
    strengths: str
    weaknesses: str
    online_presence: str


class CompetitorAnalysis(BaseModel):
    competitors: list[CompetitorEntry]
    overview: str
    score: int


def get_example_competitor_analysis() -> CompetitorAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return CompetitorAnalysis.model_validate_json(path.read_text())


def get_competitor_analysis(idea: dict) -> CompetitorAnalysis:
    return get_example_competitor_analysis()
