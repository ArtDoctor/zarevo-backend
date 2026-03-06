from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import chromadb
from pydantic import BaseModel

from typing import TYPE_CHECKING

from src.ai_utils.ai_utils import SmartnessLevel
from src.ai_utils.vertex_utils import (
    VertexResponse,
    get_vertex_response,
    get_vertex_structured,
    resolve_links,
)

if TYPE_CHECKING:
    from src.config import IdeaRequest


class IndustryRaw(BaseModel):
    sector: str
    name: str
    sizes: list[int]


class MarketEntry(BaseModel):
    name: str
    sector: str
    growth_rate: str
    sizes_2023_2026_in_millions: list[int]


class MarketAnalysis(BaseModel):
    overview: str
    trends_analysis: str
    sources: list[str]
    markets: list[MarketEntry]
    sectors: list[str]
    average_growth_rate: str
    theoretical_market_share_pct: str
    strengths: list[str]
    weaknesses: list[str]
    gaps_and_opportunities: list[str]
    threats: list[str]
    new_market_potential: str
    why_now: str
    score: int


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


class AdditionalMarketCandidate(BaseModel):
    name: str
    sector: str
    why_relevant: str
    suggested_search_queries: list[str]


class AdditionalMarketCandidatesResponse(BaseModel):
    candidates: list[AdditionalMarketCandidate]


class MarketSizing(BaseModel):
    name: str
    sector: str
    sizes_2023_2026_in_millions: list[int]
    sources: list[str]


class MarketSizingResponse(BaseModel):
    items: list[MarketSizing]


class StrengthsResponse(BaseModel):
    strengths: list[str]


class WeaknessesResponse(BaseModel):
    weaknesses: list[str]


class MarketSynthesisRemaining(BaseModel):
    gaps_and_opportunities: list[str]
    threats: list[str]
    theoretical_market_share_pct: str
    new_market_potential: str
    why_now: str
    score: int


def _idea_context_for_prompt(validated: "IdeaRequest") -> str:
    parts: list[str] = [f"Description: {validated.description}"]
    if validated.problem:
        parts.append(f"Problem: {validated.problem}")
    if validated.customer:
        parts.append(f"Customer: {validated.customer}")
    if validated.geography:
        parts.append(f"Geography: {validated.geography}")
    if validated.founder_specific:
        parts.append(f"Founder-specific context: {validated.founder_specific}")
    return "\n".join(parts).strip()


def _discover_additional_markets_prompt(
    idea_context: str, base_markets: list[MarketEntry], max_new: int
) -> str:
    base = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in base_markets
    ]
    return f"""
You are a market research analyst.

Task: propose up to {max_new} additional market categories that fit the idea but are NOT already present in the provided "base_markets".
These should be realistic markets/segments (not vague like "technology").
Focus on market definitions and size, not customers or competitors.

You are allowed to use Google search / web research to ground suggestions.

Idea context:
{idea_context}

Base markets (already identified):
{base}

Return your answer as a JSON object with a single key "candidates" containing the list of candidates.
""".strip()


def _market_sizing_prompt(
    idea_context: str, candidates: list[AdditionalMarketCandidate]
) -> str:
    payload = [
        {
            "name": c.name,
            "sector": c.sector,
            "why_relevant": c.why_relevant,
            "suggested_search_queries": c.suggested_search_queries,
        }
        for c in candidates
    ]
    return f"""
You are doing market sizing research. Focus on market size data only (no customer or competitor analysis).

Use web research to estimate the market size in USD millions for each market for 2023, 2024, 2025, 2026.
If you find a source that only provides a single year or a CAGR and a base year, extrapolate reasonably.
If you cannot find exact numbers, provide conservative estimates and include a source string explaining it is an estimate.

Idea context:
{idea_context}

Markets to size:
{payload}

Return your answer as a JSON object with a single key "items" containing the list of sized markets.
""".strip()


def _market_overview_prompt(
    idea_context: str,
    markets: list[MarketEntry],
    sectors: list[str],
    average_growth_rate: str,
) -> str:
    payload = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in markets
    ]
    return f"""
You are a venture-style market analyst. Write an EXTENSIVE, detailed market overview.

CRITICAL: This must be PURELY about the market. Do NOT mention customers, competitors, or specific buyer personas.
Focus ONLY on:
1. Market size data (TAM, SAM) and the numbers provided
2. Data quality: how reliable are these estimates? What are the sources? What confidence level?
3. Market maturity and structure
4. What percentage of the market could a founder theoretically address (realistic TAM/SAM/SOM range)?

 Write 2-3 paragraphs. Use concrete numbers. Be specific and grounded.

Idea context:
{idea_context}

Markets (with size trajectories in USD millions):
{payload}

Sectors: {sectors}
Average growth rate: {average_growth_rate}

Write your extensive market overview as plain text. No JSON.
""".strip()


def _market_trends_prompt(
    idea_context: str,
    markets: list[MarketEntry],
    sectors: list[str],
    average_growth_rate: str,
) -> str:
    payload = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in markets
    ]
    return f"""
You are a venture-style market analyst. Write an EXTENSIVE, detailed trends analysis.

CRITICAL: This must be PURELY about market trends. Do NOT mention customers, competitors, or specific buyer personas.
Focus ONLY on:
1. Growth/decline trends in the market
2. Macro and industry-level drivers
3. Historical trajectory and projections
4. Regional or segment-level trends within the market
5. Regulatory or technological shifts affecting market size

Be thorough. Write 2-3 paragraphs. Use concrete data where available.

Idea context:
{idea_context}

Markets (with size trajectories in USD millions):
{payload}

Sectors: {sectors}
Average growth rate: {average_growth_rate}

Write your trends analysis as plain text.
""".strip()


def _market_strengths_prompt(
    idea_context: str,
    markets: list[MarketEntry],
    sectors: list[str],
    average_growth_rate: str,
    overview: str,
    trends_analysis: str,
) -> str:
    payload = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in markets
    ]
    return f"""
You are a venture-style market analyst. List 3-5 market STRENGTHS.

CRITICAL: PURELY market-focused. No customers, competitors, or buyer personas.
Strengths = positive aspects of the market itself: size, growth, structure, data quality, accessibility, etc.

Base your analysis on the following market overview and trends.

Market overview:
{overview}

Trends analysis:
{trends_analysis}

Idea context:
{idea_context}

Markets: {payload}
Sectors: {sectors}
Average growth rate: {average_growth_rate}

Return a JSON object with a single key "strengths" containing a list of 3-5 strings.
""".strip()


def _market_weaknesses_prompt(
    idea_context: str,
    markets: list[MarketEntry],
    sectors: list[str],
    average_growth_rate: str,
    overview: str,
    trends_analysis: str,
) -> str:
    payload = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in markets
    ]
    return f"""
You are a venture-style market analyst. List 3-5 market WEAKNESSES.

CRITICAL: PURELY market-focused. No customers, competitors, or buyer personas.
Weaknesses = negative aspects of the market itself: fragmentation, decline, poor data, saturation, etc.

Base your analysis on the following market overview and trends.

Market overview:
{overview}

Trends analysis:
{trends_analysis}

Idea context:
{idea_context}

Markets: {payload}
Sectors: {sectors}
Average growth rate: {average_growth_rate}

Return a JSON object with a single key "weaknesses" containing a list of 3-5 strings.
""".strip()


def _market_synthesis_remaining_prompt(
    idea_context: str,
    markets: list[MarketEntry],
    sectors: list[str],
    average_growth_rate: str,
    overview: str,
    trends_analysis: str,
) -> str:
    payload = [
        {
            "name": m.name,
            "sector": m.sector,
            "growth_rate": m.growth_rate,
            "sizes_2023_2026_in_millions": m.sizes_2023_2026_in_millions,
        }
        for m in markets
    ]
    return f"""
You are a venture-style market analyst.

CRITICAL: PURELY market-focused. No customers, competitors, or buyer personas.
Focus on: market data quality, gaps in the market, threats to market size, theoretical market share %, new market potential, why now.

Base your analysis on the following market overview and trends.

Market overview:
{overview}

Trends analysis:
{trends_analysis}

Idea context:
{idea_context}

Markets: {payload}
Sectors: {sectors}
Average growth rate: {average_growth_rate}

Provide:
- gaps_and_opportunities: list of 2-4 strings (market-level gaps)
- threats: list of 2-4 strings (market-level threats)
- theoretical_market_share_pct: string like "0.5-2%" or "5-10%" - what % of TAM could a founder realistically address?
- new_market_potential: brief text on 0-to-1 potential
- why_now: brief text on timing
- score: int 0-100

Return ONLY a JSON object matching the required schema.
""".strip()


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

    idea_context = _idea_context_for_prompt(validated)

    # Step 2: ask Gemini for additional markets (web-grounded).
    additional_candidates: list[AdditionalMarketCandidate] = []
    try:
        discovery_prompt = _discover_additional_markets_prompt(
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
            sizing_prompt = _market_sizing_prompt(
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

    overview_prompt = _market_overview_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
    )
    trends_prompt = _market_trends_prompt(
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

    strengths_prompt = _market_strengths_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        overview=overview_response.text,
        trends_analysis=trends_response.text,
    )
    weaknesses_prompt = _market_weaknesses_prompt(
        idea_context=idea_context,
        markets=markets,
        sectors=sectors,
        average_growth_rate=avg_growth,
        overview=overview_response.text,
        trends_analysis=trends_response.text,
    )
    remaining_prompt = _market_synthesis_remaining_prompt(
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
