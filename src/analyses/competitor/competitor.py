import logging
import uuid
from pathlib import Path

import langsmith

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.openai_utils import get_openai_structured
from src.ai_utils.vertex_utils import (
    VertexResponse,
    get_vertex_response,
    get_vertex_structured,
    resolve_links,
)
from src.analyses.competitor.models import (
    CompetitorAnalysis,
    CompetitorDiscoveryResponse,
    CompetitorEntry,
    CompetitorScoreResponse,
)
from src.analyses.competitor.prompts import (
    competitor_discovery_prompt,
    competitor_overview_prompt,
    competitor_synthesis_prompt,
)
from src.analyses.problem.prompts import idea_context_for_prompt
from src.config import IdeaRequest

_log = logging.getLogger(__name__)


def get_example_competitor_analysis() -> CompetitorAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return CompetitorAnalysis.model_validate_json(path.read_text())


def get_competitor_analysis(idea: dict) -> CompetitorAnalysis:
    thread_id = str(uuid.uuid4())
    run_config: dict[str, object] = {"metadata": {"thread_id": thread_id}}

    with langsmith.trace(
        name="Competitor Analysis",
        metadata={"thread_id": thread_id},
        tags=["competitor-analysis"],
    ):
        return _run_competitor_analysis(idea, run_config)


def _run_competitor_analysis(
    idea: dict,
    run_config: dict[str, object],
) -> CompetitorAnalysis:
    validated = IdeaRequest.model_validate(idea)
    idea_context = idea_context_for_prompt(validated)

    competitors: list[CompetitorEntry] = []
    discovery_links: list[str] = []

    discovery_prompt = competitor_discovery_prompt(idea_context)
    for attempt in range(2):
        try:
            discovery_result = get_vertex_structured(
                discovery_prompt,
                CompetitorDiscoveryResponse,
                smartness=SmartnessLevel.MEDIUM,
                use_internet=True,
                config=run_config,
            )
            if isinstance(discovery_result, tuple):
                discovery, discovery_links = discovery_result
            else:
                discovery = discovery_result
            if isinstance(discovery, CompetitorDiscoveryResponse):
                competitors = discovery.competitors
            break
        except Exception:
            _log.exception(
                "Competitor discovery failed (attempt %d/2)", attempt + 1
            )

    if not competitors:
        return CompetitorAnalysis(
            competitors=[],
            overview="No competitors identified.",
            sources=[],
            score=0,
        )

    overview_response = VertexResponse(text="", links=[])

    def _get_overview() -> VertexResponse:
        try:
            return get_vertex_response(
                competitor_overview_prompt(idea_context, competitors),
                smartness=SmartnessLevel.MEDIUM,
                use_internet=True,
                config=run_config,
            )
        except Exception:
            return VertexResponse(text="", links=[])

    overview_response = _get_overview()

    score = 0
    try:
        synthesis_result = get_openai_structured(
            competitor_synthesis_prompt(
                idea_context, competitors, overview_response.text
            ),
            CompetitorScoreResponse,
            smartness=SmartnessLevel.LOW,
            config=run_config,
        )
        if isinstance(synthesis_result, CompetitorScoreResponse):
            score = synthesis_result.score
    except Exception:
        pass

    raw_sources = [*overview_response.links, *discovery_links]
    sources = resolve_links(raw_sources)

    return CompetitorAnalysis(
        competitors=competitors,
        overview=overview_response.text or "Competitive landscape overview unavailable.",
        sources=sources,
        score=score,
    )
