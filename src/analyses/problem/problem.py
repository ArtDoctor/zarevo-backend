from pathlib import Path

from pydantic import BaseModel


class ProblemAnalysis(BaseModel):
    overview: str
    vitamin_or_painkiller: int
    problem_stateement: str
    problem_frequency: int
    problem_size: int
    alternative_solutions: str
    related_problems: str
    strengths: list[str]
    weaknesses: list[str]
    score: int


def get_problem_analysis() -> ProblemAnalysis:
    path = Path(__file__).parent / "example_response.json"
    content = path.read_text()
    return ProblemAnalysis.model_validate_json(content)
