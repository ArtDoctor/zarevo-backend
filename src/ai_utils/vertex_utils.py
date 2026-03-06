from typing import Any, Iterable
from urllib.parse import urlparse

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.config import settings


class VertexResponse(BaseModel):
    text: str
    links: list[str]


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


def _extract_text(content: object) -> str:
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


def _extract_links(response_metadata: object) -> list[str]:
    if not isinstance(response_metadata, dict):
        return []

    grounding_metadata = response_metadata.get("grounding_metadata")
    if not isinstance(grounding_metadata, dict):
        return []

    chunks = grounding_metadata.get("grounding_chunks")
    if not isinstance(chunks, list):
        return []

    links: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web")
        if not isinstance(web, dict):
            continue
        uri = web.get("uri")
        if isinstance(uri, str) and uri.strip():
            links.append(uri.strip())

    seen: set[str] = set()
    deduped: list[str] = []
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def _is_vertex_grounding_redirect(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc == "vertexaisearch.cloud.google.com"
        and parsed.path.startswith("/grounding-api-redirect/")
    )


def _resolve_url(url: str, client: httpx.Client) -> str:
    if not _is_vertex_grounding_redirect(url):
        return url

    try:
        first_hop = client.get(url, follow_redirects=False)
        location = first_hop.headers.get("location")
        if (
            first_hop.status_code in {301, 302, 303, 307, 308}
            and isinstance(location, str)
            and location.strip()
        ):
            return location.strip()
    except Exception:
        pass

    try:
        get = client.get(url, follow_redirects=True)
        return str(get.url)
    except Exception:
        pass

    return url


def resolve_links(links: Iterable[str]) -> list[str]:
    timeout = httpx.Timeout(10.0, connect=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resolved = [_resolve_url(link, client).strip() for link in links if link.strip()]

    seen: set[str] = set()
    deduped: list[str] = []
    for link in resolved:
        if link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def get_vertex_response(
    prompt: str,
    smartness: SmartnessLevel = SmartnessLevel.LOW,
    use_internet: bool = False,
    config: dict[str, Any] | None = None,
) -> VertexResponse:
    model = _get_vertex_model(smartness)
    if use_internet:
        model = model.bind_tools([{"google_search": {}}])
    message = model.invoke(prompt, config=config or {})
    content = message.content

    response_metadata: object = {}
    if hasattr(message, "response_metadata"):
        response_metadata = message.response_metadata

    return VertexResponse(
        text=_extract_text(content),
        links=_extract_links(response_metadata),
    )


def get_vertex_structured(
    prompt: str,
    response_model: type[BaseModel],
    smartness: SmartnessLevel = SmartnessLevel.LOW,
    config: dict[str, Any] | None = None,
) -> BaseModel:
    """
    Returns a Pydantic model using LangChain structured output parsing.
    """
    model = _get_vertex_model(smartness)

    structured_model = model.with_structured_output(response_model)
    result = structured_model.invoke(prompt, config=config or {})
    if isinstance(result, response_model):
        return result
    return response_model.model_validate(result)
