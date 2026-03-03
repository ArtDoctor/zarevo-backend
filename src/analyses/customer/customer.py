from pathlib import Path

from pydantic import BaseModel


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
    customer_habbits: str
    strengths: list[str]
    weaknesses: list[str]
    score: int


def get_example_customer_analysis() -> CustomerAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return CustomerAnalysis.model_validate_json(path.read_text())


def get_customer_analysis(idea: dict) -> CustomerAnalysis:
    return get_example_customer_analysis()
