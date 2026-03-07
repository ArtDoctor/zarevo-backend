import uuid
from pathlib import Path

import langsmith
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.analyses.customer.prompts import customer_analysis_prompt
from src.analyses.problem.prompts import idea_context_for_prompt
from src.config import IdeaRequest


class IdealCustomer(BaseModel):
    name: str
    age: int
    gender: str
    ready_to_pay_usd: int
    description: str


class ViableSegment(BaseModel):
    segment_name: str
    description: str
    willingness_and_ability_to_pay: str
    preferred_payment_type: str


class CustomerAnalysis(BaseModel):
    overview: str
    key_pain_points: list[str]
    ideal_customers: list[IdealCustomer]
    viable_segments: list[ViableSegment]
    messages_that_resonate: list[str]
    customer_habits: str
    strengths: list[str]
    weaknesses: list[str]
    score: int


def get_example_customer_analysis() -> CustomerAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return CustomerAnalysis.model_validate_json(path.read_text())


def get_customer_analysis(idea: dict) -> CustomerAnalysis:
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Customer Analysis",
        metadata={"thread_id": thread_id},
        tags=["customer-analysis"],
    ):
        validated = IdeaRequest.model_validate(idea)
        idea_context = idea_context_for_prompt(validated)
        prompt = customer_analysis_prompt(idea_context)
        result = get_openai_structured(
            prompt,
            CustomerAnalysis,
            smartness=SmartnessLevel.MEDIUM,
            config=run_config,
        )
        if isinstance(result, CustomerAnalysis):
            return result
        return CustomerAnalysis.model_validate(result)
