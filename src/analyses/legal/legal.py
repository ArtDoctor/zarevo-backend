from pathlib import Path

from pydantic import BaseModel


class LegalAnalysis(BaseModel):
    overview: str
    GDPR_compliance: str
    EU_AI_compliance: str
    score: int


def get_legal_analysis() -> LegalAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return LegalAnalysis.model_validate_json(content)
