from pathlib import Path

from pydantic import BaseModel


class TechnicalAnalysis(BaseModel):
    toughness: int
    overview: str
    suggested_tech_stack: str
    scaling_considertions: str
    no_code_viability: str
    ideal_team: str
    strengths: list[str]
    weaknesses: list[str]
    score: int


def get_technical_analysis(idea: dict) -> TechnicalAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return TechnicalAnalysis.model_validate_json(content)
