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


def get_example_technical_analysis() -> TechnicalAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return TechnicalAnalysis.model_validate_json(path.read_text())


def get_technical_analysis(idea: dict) -> TechnicalAnalysis:
    return get_example_technical_analysis()
