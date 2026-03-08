from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.retry import run_with_retry
from src.config import settings


def _get_openai_model(smartness: SmartnessLevel) -> ChatOpenAI:
    if smartness == SmartnessLevel.LOW:
        return ChatOpenAI(model="gpt-5-nano", api_key=settings.openai_api_key)
    if smartness == SmartnessLevel.MEDIUM:
        return ChatOpenAI(model="gpt-5-mini", api_key=settings.openai_api_key)
    return ChatOpenAI(model="gpt-5.4", api_key=settings.openai_api_key)


def get_openai_response(prompt: str, smartness: SmartnessLevel = SmartnessLevel.LOW) -> str:
    model = _get_openai_model(smartness)

    def _invoke() -> str:
        response = model.invoke(prompt)
        return response.content

    return run_with_retry(_invoke)


def _extract_json_from_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        start = text.find("\n") + 1
        end = text.rfind("```")
        if end > start:
            return text[start:end].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def get_openai_structured(
    prompt: str,
    response_model: type[BaseModel],
    smartness: SmartnessLevel = SmartnessLevel.LOW,
    config: dict[str, Any] | None = None,
) -> BaseModel:
    model = _get_openai_model(smartness)
    structured_model = model.with_structured_output(response_model)

    def _invoke() -> BaseModel:
        result = structured_model.invoke(prompt, config=config or {})
        if isinstance(result, response_model):
            return result
        if isinstance(result, dict):
            return response_model.model_validate(result)
        text = str(result) if result is not None else ""
        json_str = _extract_json_from_text(text)
        return response_model.model_validate_json(json_str)

    return run_with_retry(_invoke)
