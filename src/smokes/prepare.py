from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.smokes.models import SmokeFeature


def get_test_smoke_features() -> list[SmokeFeature]:
    return [
        SmokeFeature(
            feature="Automated ad campaigns in under 2 minutes",
            description="Set up targeted Facebook and Google ads without touching ad platforms. We handle targeting, creatives, and tracking so you can focus on the idea.",
            expected_signup_increase_pct=18.0,
        ),
        SmokeFeature(
            feature="Real conversion data, not AI guesses",
            description="Get actual sign-ups from real people who clicked your ad. No simulated feedback—see genuine interest before you build.",
            expected_signup_increase_pct=22.0,
        ),
        SmokeFeature(
            feature="One landing page, zero code",
            description="We generate a conversion-optimized landing page from your idea. No design or dev work—just describe it and we ship.",
            expected_signup_increase_pct=14.0,
        ),
        SmokeFeature(
            feature="Full report in 48 hours",
            description="From idea to validated data in two days. Know whether to build or pivot before you invest months of development.",
            expected_signup_increase_pct=12.0,
        ),
    ]


class SmokeFeaturesResponse(BaseModel):
    features: list[SmokeFeature]


def _smoke_prepare_prompt(customer_summary: str, competitor_summary: str, problem_summary: str) -> str:
    return f"""Analyse the following customer, competitor, and problem analysis for a business idea.
Propose 3-6 features to advertise on a smoke test landing page. Each feature should be compelling for the target audience and likely to increase sign-up rate when highlighted.

Customer analysis:
{customer_summary}

Competitor analysis:
{competitor_summary}

Problem analysis:
{problem_summary}

For each proposed feature, provide:
1. feature: short headline (e.g. "Automated ad campaigns in 2 minutes")
2. description: brief what/why explanation (1-2 sentences)
3. expected_signup_increase_pct: float 0-100, estimated percentage increase in sign-up rate if this feature is advertised vs baseline (be realistic, typical range 0.1%-15%), total of sign up shouldn't add up to more than 20%.

Return a JSON object with key "features" containing a list of these objects."""


def prepare_smoke_features_from_analyses(
    customer_result: dict,
    competitor_result: dict,
    problem_result: dict,
) -> list[SmokeFeature]:
    customer_summary = _summarise_for_prompt(customer_result, "overview", "key_pain_points", "ideal_customers")
    competitor_summary = _summarise_for_prompt(competitor_result, "overview", "competitors")
    problem_summary = _summarise_for_prompt(
        problem_result, "overview", "problem_statement", "strengths", "weaknesses"
    )

    prompt = _smoke_prepare_prompt(customer_summary, competitor_summary, problem_summary)
    result = get_openai_structured(
        prompt,
        SmokeFeaturesResponse,
        smartness=SmartnessLevel.MEDIUM,
    )
    return result.features


def _summarise_for_prompt(data: dict, *keys: str) -> str:
    parts: list[str] = []
    for key in keys:
        val = data.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            parts.append(f"{key}: {val}")
        else:
            parts.append(f"{key}: {val}")
    return "\n".join(parts) if parts else "No data available"
