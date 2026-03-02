from pathlib import Path

from pydantic import BaseModel


class FinancialAnalysis(BaseModel):
    start_capital_needed: str
    costs_overview: str
    investor_requirements: str
    investor_concerns: str
    overview: str


def get_financial_analysis() -> FinancialAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return FinancialAnalysis.model_validate_json(content)
