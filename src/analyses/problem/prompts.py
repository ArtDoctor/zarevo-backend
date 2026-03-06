from typing import TYPE_CHECKING

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


def problem_analysis_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style problem analyst. Analyze whether this idea solves a real, meaningful problem.

CRITICAL: Do NOT use web search or external data. Base your analysis purely on reasoning from the idea context.

Idea context:
{idea_context}

Provide a structured problem analysis:

1. overview: 2-3 paragraphs. Are they solving an actual problem? If yes, list the problems this idea solves and formulate one primary problem. If no, reason why this is not an actual problem (and decrease the score significantly). Be specific and grounded.

2. vitamin_or_painkiller: int 1-10. 10 = must-have painkiller (people actively suffer without it). 1 = nice-to-have vitamin (convenience only).

3. problem_statement: One strong, clear sentence stating the core problem being solved.

4. problem_frequency: int 1-10. How often do target users encounter this problem? 10 = daily/multiple times per day. 1 = rarely.

5. problem_size: int 1-10. How big is the problem in terms of impact (time, money, frustration)? 10 = severe. 1 = minor.

6. alternative_solutions: 2-4 paragraphs. List and briefly evaluate existing alternatives (competitors, workarounds, doing nothing). How well do they address the problem?

7. related_problems: 1-2 paragraphs. What adjacent or related problems exist? Could solving this unlock solutions to others?

8. strengths: list of 3-5 strings. Positive aspects of the problem space: urgency, frequency, severity, underserved, etc.

9. weaknesses: list of 3-5 strings. Negative aspects: small TAM, well-served, low urgency, etc.

10. score: int 0-100. Overall problem quality. Penalize heavily if not a real problem. Reward clear, frequent, severe, underserved problems.

Return ONLY a JSON object matching this schema.
""".strip()
