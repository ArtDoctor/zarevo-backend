from pathlib import Path

from pydantic import BaseModel

from src.ai_utils.vertex_utils import resolve_links


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
    sources: list[str]
    score: int


def get_example_competitor_analysis() -> CompetitorAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return CompetitorAnalysis.model_validate_json(path.read_text())


def get_competitor_analysis(idea: dict) -> CompetitorAnalysis:
    result = get_example_competitor_analysis()
    return result.model_copy(update={"sources": resolve_links(result.sources)})
