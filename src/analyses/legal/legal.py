import uuid
from pathlib import Path

import langsmith
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.analyses.legal.prompts import legal_analysis_prompt
from src.analyses.problem.prompts import idea_context_for_prompt
from src.config import IdeaRequest


class LegalAnalysis(BaseModel):
    overview: str
    GDPR_compliance: str
    EU_AI_compliance: str
    score: int


def get_example_legal_analysis() -> LegalAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return LegalAnalysis.model_validate_json(path.read_text())


def get_legal_analysis(idea: dict) -> LegalAnalysis:
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Legal Analysis",
        metadata={"thread_id": thread_id},
        tags=["legal-analysis"],
    ):
        validated = IdeaRequest.model_validate(idea)
        idea_context = idea_context_for_prompt(validated)
        prompt = legal_analysis_prompt(idea_context)
        result = get_openai_structured(
            prompt,
            LegalAnalysis,
            smartness=SmartnessLevel.MEDIUM,
            config=run_config,
        )
        if isinstance(result, LegalAnalysis):
            return result
        return LegalAnalysis.model_validate(result)
