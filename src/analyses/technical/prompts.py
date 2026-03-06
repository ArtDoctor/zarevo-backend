def technical_analysis_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style technical analyst. Analyze the technical feasibility and complexity of this idea.

CRITICAL: Do NOT use web search or external data. Base your analysis purely on reasoning from the idea context.

Idea context:
{idea_context}

Provide a structured technical analysis:

1. toughness: int 1-10. How technically challenging? 10 = very complex (ML, real-time). 1 = simple (CRUD, static).

2. overview: 2-3 paragraphs. How technically challenging? Main challenges? What expertise is needed?

3. suggested_tech_stack: 1-2 paragraphs. Tech stack for simplest viable version (e.g. Python, React). Be specific.

4. scaling_considertions: 1-2 paragraphs. How to scale. Main challenges. Bottlenecks. Use "scaling_considertions" in JSON.

5. no_code_viability: 1-2 paragraphs. Is this product viable without code? If yes, how (e.g. Zapier, Airtable, Bubble)? If no, why not?

6. ideal_team: 1-2 paragraphs. Ideal team composition (e.g. developer, designer, DevOps). What roles are essential?

7. strengths: list of 3-5 strings. Technical strengths: well-understood stack, proven patterns, low complexity, etc.

8. weaknesses: list of 3-5 strings. Technical weaknesses: novel tech, high complexity, scaling challenges, etc.

9. score: int 0-100. Technical feasibility. Reward clear paths, low complexity. Penalize unclear scope.

Return ONLY a JSON object. Use "scaling_considertions" for the scaling field.
""".strip()
