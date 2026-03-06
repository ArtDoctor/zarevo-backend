from typing import TYPE_CHECKING

from src.analyses.market.models import AdditionalMarketCandidate, MarketEntry

if TYPE_CHECKING:
    from src.config import IdeaRequest


def idea_context_for_prompt(validated: "IdeaRequest") -> str:
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


def discover_additional_markets_prompt(
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


def market_sizing_prompt(
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


def market_overview_prompt(
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


def market_trends_prompt(
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


def market_strengths_prompt(
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


def market_weaknesses_prompt(
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


def market_synthesis_remaining_prompt(
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
