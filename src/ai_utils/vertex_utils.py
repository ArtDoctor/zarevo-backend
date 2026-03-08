from typing import Any, Iterable
from urllib.parse import urlparse

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.retry import run_with_retry
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

    def _invoke():
        return model.invoke(prompt, config=config or {})

    message = run_with_retry(_invoke)
    content = message.content

    response_metadata: object = {}
    if hasattr(message, "response_metadata"):
        response_metadata = message.response_metadata

    return VertexResponse(
        text=_extract_text(content),
        links=_extract_links(response_metadata),
    )


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


def get_vertex_structured(
    prompt: str,
    response_model: type[BaseModel],
    smartness: SmartnessLevel = SmartnessLevel.LOW,
    use_internet: bool = False,
    config: dict[str, Any] | None = None,
) -> BaseModel | tuple[BaseModel, list[str]]:
    model = _get_vertex_model(smartness)
    if use_internet:
        model = model.bind_tools([{"google_search": {}}])

        def _invoke_internet():
            return model.invoke(prompt, config=config or {})

        message = run_with_retry(_invoke_internet)
        response_metadata: object = {}
        if hasattr(message, "response_metadata"):
            response_metadata = message.response_metadata
        links = _extract_links(response_metadata)
        text = _extract_text(message.content)
        json_str = _extract_json_from_text(text)
        result = response_model.model_validate_json(json_str)
        return (result, links)
    structured_model = model.with_structured_output(response_model)

    def _invoke_structured():
        return structured_model.invoke(prompt, config=config or {})

    result = run_with_retry(_invoke_structured)
    if isinstance(result, response_model):
        return result
    return response_model.model_validate(result)
