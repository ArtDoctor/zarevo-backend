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


def get_competitor_analysis(idea: dict) -> CompetitorAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return CompetitorAnalysis.model_validate_json(content)
