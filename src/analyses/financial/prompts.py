def financial_analysis_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style financial analyst. Analyze the financial feasibility and capital requirements of this idea.

CRITICAL: Do NOT use web search or external data. Base your analysis purely on reasoning from the idea context.

Idea context:
{idea_context}

Provide a structured financial analysis:

1. start_capital_needed: string. Capital to reach first revenue or MVP (e.g. "50,000 USD"). Be specific.

2. costs_overview: 2-3 paragraphs. Dev, marketing, ops costs. Main cost drivers? What can be bootstrapped?

3. investor_requirements: 2-3 paragraphs. Need investor? Type (angel, seed, VC)? Ideal for this stage?

4. investor_concerns: 1-2 paragraphs. What would concern investors? Market size, competition, execution risk, team, etc.

5. overview: 2-3 paragraphs. Overall financial picture. What are the risks and opportunities? What is the path to profitability?

Return ONLY a JSON object matching this schema.
""".strip()
