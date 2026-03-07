from datetime import date

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
    idea_id: str
    cta: str = Field(alias="CTA")
    features: list[SmokeFeature]
    images: list[str]
    user_input: str = ""

    model_config = {"populate_by_name": True}


class SmokeCode(BaseModel):
    html: str
    css: str
    js: str


class SmokeInput(BaseModel):
    idea_description: str
    cta: str
    features: list[SmokeFeature]
    images: list[str]
    user_input: str = ""
    idea_title: str = ""
    idea_customer: str = ""
    idea_geography: str = ""


class AdChannel(BaseModel):
    channel: str
    advertised: str


class PublishSmokeRequest(BaseModel):
    smoke_id: str
    duration: int
    subdomain: str
    start_date: date
    ads_channels: list[AdChannel]


class SmokeSignupRequest(BaseModel):
    subdomain: str
    email: str
    text: str
