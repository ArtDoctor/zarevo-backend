import uuid
from pathlib import Path

import langsmith
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.analyses.problem.prompts import idea_context_for_prompt
from src.analyses.technical.prompts import technical_analysis_prompt
from src.config import IdeaRequest


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
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Technical Analysis",
        metadata={"thread_id": thread_id},
        tags=["technical-analysis"],
    ):
        validated = IdeaRequest.model_validate(idea)
        idea_context = idea_context_for_prompt(validated)
        prompt = technical_analysis_prompt(idea_context)
        result = get_openai_structured(
            prompt,
            TechnicalAnalysis,
            smartness=SmartnessLevel.MEDIUM,
            config=run_config,
        )
        if isinstance(result, TechnicalAnalysis):
            return result
        return TechnicalAnalysis.model_validate(result)
