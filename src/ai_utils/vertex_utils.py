from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from src.ai_utils.ai_utils import SmartnessLevel
from src.config import settings


def _get_vertex_model(smartness: SmartnessLevel) -> ChatGoogleGenerativeAI:
    if smartness == SmartnessLevel.LOW:
        return ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            api_key=settings.vertex_ai_api_key,
            vertexai=True,
        )
    if smartness == SmartnessLevel.MEDIUM:
        return ChatGoogleGenerativeAI(
            model="gemini-3.1-pro-preview",
            api_key=settings.vertex_ai_api_key,
            vertexai=True,
            thinking_level="low"
        )
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-pro-preview",
        api_key=settings.vertex_ai_api_key,
        vertexai=True,
        thinking_level="medium"
    )


def get_vertex_response(prompt: str, smartness: SmartnessLevel = SmartnessLevel.LOW) -> str:
    model = _get_vertex_model(smartness)
    message = model.invoke(prompt)
    content = message.content

    if isinstance(content, str):
        return content

    # LangChain may represent Gemini content as a list of parts.
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part and isinstance(part["text"], str):
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p.strip())

    return str(content)


def get_vertex_structured(
    prompt: str, response_model: type[BaseModel], smartness: SmartnessLevel = SmartnessLevel.LOW
) -> BaseModel:
    """
    Returns a Pydantic model using LangChain structured output parsing.
    """
    model = _get_vertex_model(smartness)

    structured_model = model.with_structured_output(response_model)
    result = structured_model.invoke(prompt)
    if isinstance(result, response_model):
        return result
    return response_model.model_validate(result)
