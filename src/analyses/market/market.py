from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import chromadb

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.vertex_utils import (
    VertexResponse,
    get_vertex_response,
    get_vertex_structured,
    resolve_links,
)
from src.analyses.market.models import (
    AdditionalMarketCandidate,
    AdditionalMarketCandidatesResponse,
    IndustryRaw,
    MarketAnalysis,
    MarketEntry,
    MarketSizing,
    MarketSynthesisRemaining,
    MarketSizingResponse,
    StrengthsResponse,
    WeaknessesResponse,
)
from src.analyses.market.prompts import (
    discover_additional_markets_prompt,
    idea_context_for_prompt,
    market_overview_prompt,
    market_sizing_prompt,
    market_strengths_prompt,
    market_synthesis_remaining_prompt,
    market_trends_prompt,
    market_weaknesses_prompt,
)


def _growth_rate_from_sizes(sizes: list[int]) -> str:
    if not sizes or sizes[0] == 0:
        return "0%"
    rate = ((sizes[-1] - sizes[0]) / sizes[0]) * 100
    return f"{rate:.1f}%"


def _get_collection() -> chromadb.Collection:
    data_dir = Path(__file__).parent / ".chroma_data"
    data_dir.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(data_dir))
    return client.get_or_create_collection("industries", metadata={"hnsw:space": "cosine"})


def _ensure_industries_indexed(collection: chromadb.Collection) -> list[IndustryRaw]:
    industries_path = Path(__file__).parent / "industries.json"
    industries: list[IndustryRaw] = [
        IndustryRaw.model_validate(item) for item in _load_json(industries_path)
    ]
    if collection.count() > 0:
        return industries
    documents = [f"{ind.sector} {ind.name}" for ind in industries]
    metadatas = [{"idx": i} for i in range(len(industries))]
    ids = [str(i) for i in range(len(industries))]
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return industries


def _load_json(path: Path) -> list[dict]:
    import json

    return json.loads(path.read_text())


def _search_markets(description: str, top_k: int = 5) -> list[MarketEntry]:
    collection = _get_collection()
    industries = _ensure_industries_indexed(collection)
    results = collection.query(query_texts=[description], n_results=min(top_k, len(industries)))
    if not results or not results["ids"] or not results["ids"][0]:
        return []
    indices = [int(idx) for idx in results["ids"][0]]
    entries: list[MarketEntry] = []
    for idx in indices:
        ind = industries[idx]
        growth = _growth_rate_from_sizes(ind.sizes)
        entries.append(
            MarketEntry(
                name=ind.name,
                sector=ind.sector,
                growth_rate=growth,
                sizes_2023_2026_in_millions=ind.sizes,
            )
        )
    return entries


def _dedupe_markets(markets: list[MarketEntry]) -> list[MarketEntry]:
    seen: set[tuple[str, str]] = set()
    out: list[MarketEntry] = []
    for m in markets:
        key = (m.name.strip().lower(), m.sector.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _average_growth_rate(markets: list[MarketEntry]) -> str:
    rates: list[float] = []
    for m in markets:
        s = m.sizes_2023_2026_in_millions
        if s and len(s) >= 2 and s[0] != 0:
            rates.append(((s[-1] - s[0]) / s[0]) * 100)
    return f"{sum(rates) / len(rates):.1f}%" if rates else "0%"


def get_example_market_analysis() -> MarketAnalysis:
    path = Path(__file__).parent / "example_response.json"
    return MarketAnalysis.model_validate_json(path.read_text())


def get_market_analysis(idea: dict) -> MarketAnalysis:
    from src.config import IdeaRequest

    validated = IdeaRequest.model_validate(idea)
    description = validated.description
    if validated.problem:
        description = f"{description} {validated.problem}"
    if validated.customer:
        description = f"{description} {validated.customer}"

    # Step 1: get markets via local DB/vector index.
    base_markets = _search_markets(description, top_k=5)

    idea_context = idea_context_for_prompt(validated)

    # Step 2: ask Gemini for additional markets (web-grounded).
    additional_candidates: list[AdditionalMarketCandidate] = []
    try:
        discovery_prompt = discover_additional_markets_prompt(
            idea_context=idea_context, base_markets=base_markets, max_new=5
        )
        discovery = get_vertex_structured(
            discovery_prompt, AdditionalMarketCandidatesResponse, smartness=SmartnessLevel.LOW
        )
        if isinstance(discovery, AdditionalMarketCandidatesResponse):
            additional_candidates = discovery.candidates
    except Exception:
        additional_candidates = []

    additional_sized: list[MarketSizing] = []
    try:
        if additional_candidates:
            sizing_prompt = market_sizing_prompt(
                idea_context=idea_context, candidates=additional_candidates
            )
            sizing = get_vertex_structured(
                sizing_prompt, MarketSizingResponse, smartness=SmartnessLevel.HIGH
            )
            if isinstance(sizing, MarketSizingResponse):
                additional_sized = sizing.items
    except Exception:
        additional_sized = []

    additional_entries: list[MarketEntry] = []
    for s in additional_sized:
        growth = _growth_rate_from_sizes(s.sizes_2023_2026_in_millions)
        additional_entries.append(
            MarketEntry(
                name=s.name,
                sector=s.sector,
                growth_rate=growth,
                sizes_2023_2026_in_millions=s.sizes_2023_2026_in_millions,
            )
        )

    markets = _dedupe_markets(base_markets + additional_entries)
    sectors = list(dict.fromkeys(m.sector for m in markets))
    avg_growth = _average_growth_rate(markets)

    overview_response = VertexResponse(text="", links=[])
    trends_response = VertexResponse(text="", links=[])
    strengths: list[str] = []
    weaknesses: list[str] = []
    remaining = MarketSynthesisRemaining(
        gaps_and_opportunities=[],
        threats=[],
        theoretical_market_share_pct="",
        new_market_potential="",
        why_now="",
        score=0,
    )

    overview_prompt = market_overview_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
    )
    trends_prompt = market_trends_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
    )

    def _get_overview() -> VertexResponse:
        try:
            return get_vertex_response(
                overview_prompt,
                smartness=SmartnessLevel.MEDIUM,
                use_internet=True,
            )
        except Exception:
            return VertexResponse(text="", links=[])

    def _get_trends() -> VertexResponse:
        try:
            return get_vertex_response(
                trends_prompt,
                smartness=SmartnessLevel.MEDIUM,
                use_internet=True,
            )
        except Exception:
            return VertexResponse(text="", links=[])

    with ThreadPoolExecutor(max_workers=2) as executor:
        f_overview = executor.submit(_get_overview)
        f_trends = executor.submit(_get_trends)
        overview_response = f_overview.result()
        trends_response = f_trends.result()

    strengths_prompt = market_strengths_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        overview=overview_response.text,
        trends_analysis=trends_response.text,
    )
    weaknesses_prompt = market_weaknesses_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        overview=overview_response.text,
        trends_analysis=trends_response.text,
    )
    remaining_prompt = market_synthesis_remaining_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        overview=overview_response.text,
        trends_analysis=trends_response.text,
    )

    def _get_strengths() -> list[str]:
        try:
            r = get_vertex_structured(
                strengths_prompt, StrengthsResponse, smartness=SmartnessLevel.MEDIUM
            )
            return r.strengths if isinstance(r, StrengthsResponse) else []
        except Exception:
            return []

    def _get_weaknesses() -> list[str]:
        try:
            r = get_vertex_structured(
                weaknesses_prompt, WeaknessesResponse, smartness=SmartnessLevel.MEDIUM
            )
            return r.weaknesses if isinstance(r, WeaknessesResponse) else []
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=3) as executor:
        f_strengths = executor.submit(_get_strengths)
        f_weaknesses = executor.submit(_get_weaknesses)
        f_remaining = executor.submit(
            lambda: get_vertex_structured(
                remaining_prompt, MarketSynthesisRemaining, smartness=SmartnessLevel.MEDIUM
            )
        )
        strengths = f_strengths.result()
        weaknesses = f_weaknesses.result()
        try:
            remaining = f_remaining.result()
        except Exception:
            pass

    sizing_sources: list[str] = []
    for sized in additional_sized:
        sizing_sources.extend(sized.sources)

    raw_sources = [*overview_response.links, *trends_response.links, *sizing_sources]
    sources = resolve_links(raw_sources)

    return MarketAnalysis(
        overview=overview_response.text,
        trends_analysis=trends_response.text,
        sources=sources,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        theoretical_market_share_pct=remaining.theoretical_market_share_pct,
        strengths=strengths,
        weaknesses=weaknesses,
        gaps_and_opportunities=remaining.gaps_and_opportunities,
        threats=remaining.threats,
        new_market_potential=remaining.new_market_potential,
        why_now=remaining.why_now,
        score=remaining.score,
    )
