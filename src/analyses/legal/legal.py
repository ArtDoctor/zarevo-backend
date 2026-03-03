from pathlib import Path

from pydantic import BaseModel


class LegalAnalysis(BaseModel):
    overview: str
    GDPR_compliance: str
    EU_AI_compliance: str
    score: int


def get_example_legal_analysis() -> LegalAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return LegalAnalysis.model_validate_json(path.read_text())


def get_legal_analysis(idea: dict) -> LegalAnalysis:
    return get_example_legal_analysis()
