from langchain_openai import ChatOpenAI
from src.ai_utils.ai_utils import SmartnessLevel
from src.config import settings


def get_openai_response(prompt: str, smartness: SmartnessLevel = SmartnessLevel.LOW) -> str:
    if smartness == SmartnessLevel.LOW:
        model = ChatOpenAI(model="gpt-5-nano", api_key=settings.openai_api_key)
    elif smartness == SmartnessLevel.MEDIUM:
        model = ChatOpenAI(model="gpt-5-mini", api_key=settings.openai_api_key)
    elif smartness == SmartnessLevel.HIGH:
        model = ChatOpenAI(model="gpt-5.2", api_key=settings.openai_api_key)
    response = model.invoke(prompt)
    return response.content
