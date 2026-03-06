import uuid
from pathlib import Path

import langsmith
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.vertex_utils import get_vertex_structured
from src.analyses.problem.prompts import idea_context_for_prompt, problem_analysis_prompt
from src.config import IdeaRequest


class ProblemAnalysis(BaseModel):
    overview: str
    vitamin_or_painkiller: int
    problem_statement: str
    problem_frequency: int
    problem_size: int
    alternative_solutions: str
    related_problems: str
    strengths: list[str]
    weaknesses: list[str]
    score: int


def get_example_problem_analysis() -> ProblemAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return ProblemAnalysis.model_validate_json(path.read_text())


def get_problem_analysis(idea: dict) -> ProblemAnalysis:
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Problem Analysis",
        metadata={"thread_id": thread_id},
        tags=["problem-analysis"],
    ):
        validated = IdeaRequest.model_validate(idea)
        idea_context = idea_context_for_prompt(validated)
        prompt = problem_analysis_prompt(idea_context)
        result = get_vertex_structured(
            prompt,
            ProblemAnalysis,
            smartness=SmartnessLevel.MEDIUM,
            config=run_config,
        )
        if isinstance(result, ProblemAnalysis):
            return result
        return ProblemAnalysis.model_validate(result)
