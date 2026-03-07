from pydantic import BaseModel, Field


class SmokeFeature(BaseModel):
    feature: str
    description: str
    expected_signup_increase_pct: float


class IdeaFeature(BaseModel):
    title: str
    description: str
    expected_signup_increase_pct: float


class CreateSmokeRequest(BaseModel):
    cta: str = Field(alias="CTA")
    features: list[SmokeFeature]
    images: list[str]

    model_config = {"populate_by_name": True}
