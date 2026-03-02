from langchain_google_genai import ChatGoogleGenerativeAI
from src.ai_utils.ai_utils import SmartnessLevel
from src.config import settings


def get_vertex_response(prompt: str, smartness: SmartnessLevel = SmartnessLevel.LOW) -> str:
    if smartness == SmartnessLevel.LOW:
        model = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            api_key=settings.vertex_ai_api_key,
            vertexai=True,
        )
    elif smartness == SmartnessLevel.MEDIUM:
        model = ChatGoogleGenerativeAI(
            model="gemini-3.1-pro-preview",
            api_key=settings.vertex_ai_api_key,
            vertexai=True,
        )
    elif smartness == SmartnessLevel.HIGH:
        model = ChatGoogleGenerativeAI(
            model="gemini-3.1-pro-preview",
            api_key=settings.vertex_ai_api_key,
            vertexai=True,
        )
    response = model.invoke(prompt).content

    return response[0]['text']
