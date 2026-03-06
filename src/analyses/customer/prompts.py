def customer_analysis_prompt(idea_context: str) -> str:
    return f"""
You are a venture-style customer analyst. Analyze who the target customer is and how well-defined they are for this idea.

CRITICAL: Do NOT use web search or external data. Base your analysis purely on reasoning from the idea context.

Idea context:
{idea_context}

Provide a structured customer analysis:

1. overview: 2-3 paragraphs. Who is the customer? Is it B2B, B2C, B2G, or combined? What difference does it make?
   How well-defined is the target?

2. key_pain_points: list of 3-5 strings. The main pain points this customer experiences that the idea addresses.

3. ideal_customers: list of 2-4 ideal customer profiles. Each object has: name (string), age (int), gender (string),
   ready_to_pay_usd (int), description (string). Be specific and grounded.

4. viable_segments: list of 2-4 market segments. Each object has: segment_name (string), description (string),
   willingness_and_ability_to_pay (string), preferred_payment_type (string).

5. messages_that_resonate: list of 3-5 strings. Messaging angles or value propositions that would resonate with
   this customer.

6. customer_habits: 1-2 paragraphs. Industry standards, habits, and behaviors the ideal customer is used to.
   What channels do they use? How do they make decisions?

7. strengths: list of 3-5 strings. Positive aspects of the customer space: clear ICP, high willingness to pay,
   accessible, etc.

8. weaknesses: list of 3-5 strings. Negative aspects: vague target, low willingness to pay, hard to reach, etc.

9. score: int 0-100. Overall customer definition quality. Reward clear, specific, reachable customers with
   strong willingness to pay.

Return ONLY a JSON object matching this schema.
""".strip()
