def legal_analysis_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style legal analyst. Analyze the legal and regulatory considerations for this idea.

CRITICAL: Do NOT use web search or external data. Base your analysis purely on reasoning from the idea context.

Idea context:
{idea_context}

Provide a structured legal analysis:

1. overview: 2-3 paragraphs. Is this legal? Main challenges? Regulatory risks? Licenses or permits?

2. GDPR_compliance: 1-2 paragraphs. Is this compliant with GDPR? If yes, how?

If no, what are the gaps? Consider data collection, storage, processing, user rights, consent.

3. EU_AI_compliance: 1-2 paragraphs. EU AI Act compliant? Gaps? Consider risk class, transparency, oversight.

4. score: int 0-100. Legal compliance and risk. Reward low complexity. Penalize high regulatory risk.

Return ONLY a JSON object matching this schema.
""".strip()
