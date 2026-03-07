from src.analyses.competitor.models import CompetitorEntry


def competitor_discovery_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style competitive intelligence analyst.

Task: Use web search to find 3-6 direct and indirect competitors for this idea. For each competitor, fill out all fields with real, researched data. You don't have to be extremely extensive and precise; if info is hard to get, skip it.

You MUST use Google search / web research to ground your findings. Find actual companies, products, or solutions. Include revenue estimates, feature comparisons, and real strengths/weaknesses where available.

Idea context:
{idea_context}

For each competitor, provide:
- name: Company or product name
- description: 1-2 sentences on what they do, size, growth, market position
- revenue: Revenue estimate (e.g. "~$50M ARR", "Series B, ~$20M", "Unknown")
- features: Key features and capabilities
- strengths: What they do well
- weaknesses: Gaps, limitations, or downsides
- online_presence: Social media, website, community presence

Return a JSON object with a single key "competitors" containing the list. Be specific and use real data from your research.
""".strip()


def competitor_overview_prompt(
    idea_context: str,
    competitors: list[CompetitorEntry],
) -> str:
    payload = [
        {
            "name": c.name,
            "description": c.description,
            "revenue": c.revenue,
            "features": c.features,
            "strengths": c.strengths,
            "weaknesses": c.weaknesses,
            "online_presence": c.online_presence,
        }
        for c in competitors
    ]
    return f"""
You are a venture-style competitive analyst. Write an EXTENSIVE competitive landscape overview.

Use web search if needed to add context, market dynamics, or recent developments.

Idea context:
{idea_context}

Competitors (researched data):
{payload}

Write 2-3 paragraphs covering:
1. Competitive landscape summary: who competes, how crowded, key differentiators
2. Market positioning: how competitors segment, pricing, target customers
3. Gaps and opportunities: where the idea could differentiate or win

Write as plain text. No JSON.
""".strip()


def competitor_synthesis_prompt(
    idea_context: str,
    competitors: list[CompetitorEntry],
    overview: str,
) -> str:
    payload = [
        {
            "name": c.name,
            "description": c.description,
            "revenue": c.revenue,
            "features": c.features,
            "strengths": c.strengths,
            "weaknesses": c.weaknesses,
        }
        for c in competitors
    ]
    return f"""
You are a venture-style competitive analyst. Score the competitive landscape.

Base your analysis on the overview and competitor data. Do NOT use web search.

Idea context:
{idea_context}

Competitors:
{payload}

Overview:
{overview}

Provide a score 0-100 for the competitive landscape:
- Higher: clear differentiation possible, underserved gaps, weak incumbents, room for new entrant
- Lower: crowded space, strong incumbents, commoditized, hard to differentiate

Return ONLY a JSON object with a single key "score" (int).
""".strip()
