import uuid
from pathlib import Path

import langsmith
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.analyses.financial.prompts import financial_analysis_prompt
from src.analyses.problem.prompts import idea_context_for_prompt
from src.config import IdeaRequest


class FinancialAnalysis(BaseModel):
    start_capital_needed: str
    costs_overview: str
    investor_requirements: str
    investor_concerns: str
    overview: str


def get_example_financial_analysis() -> FinancialAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return FinancialAnalysis.model_validate_json(path.read_text())


def get_financial_analysis(idea: dict) -> FinancialAnalysis:
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Financial Analysis",
        metadata={"thread_id": thread_id},
        tags=["financial-analysis"],
    ):
        validated = IdeaRequest.model_validate(idea)
        idea_context = idea_context_for_prompt(validated)
        prompt = financial_analysis_prompt(idea_context)
        result = get_openai_structured(
            prompt,
            FinancialAnalysis,
            smartness=SmartnessLevel.MEDIUM,
            config=run_config,
        )
        if isinstance(result, FinancialAnalysis):
            return result
        return FinancialAnalysis.model_validate(result)
