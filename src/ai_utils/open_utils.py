import logging
import re

from langchain_core.messages import HumanMessage
from langchain_openrouter import ChatOpenRouter

from src.config import settings
from src.smokes.models import SmokeCode, SmokeInput


_log = logging.getLogger(__name__)


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part and isinstance(part["text"], str):
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "\n".join(p for p in parts if p.strip())
    return str(content)


def _extract_html_from_response(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None

    match = re.search(
        r"```(?:html)?\s*([\s\S]*?)\s*```",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    if "<!DOCTYPE" in text.upper() or text.lstrip().startswith("<html"):
        return text

    return None


_TEST_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Test Product - Your idea, validated</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #1a1a2e;
      background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
      min-height: 100vh;
      padding: 2rem;
    }
    .container {
      max-width: 640px;
      margin: 0 auto;
    }
    header {
      text-align: center;
      margin-bottom: 3rem;
      padding: 2rem 0;
    }
    h1 {
      font-size: 2.5rem;
      font-weight: 700;
      color: #1a1a2e;
      margin-bottom: 0.5rem;
    }
    .tagline {
      font-size: 1.2rem;
      color: #4a5568;
    }
    .features {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .features h2 {
      font-size: 1.25rem;
      color: #2d3748;
      margin-bottom: 1rem;
    }
    .features ul {
      list-style: none;
    }
    .features li {
      padding: 0.5rem 0;
      padding-left: 1.5rem;
      position: relative;
      color: #4a5568;
    }
    .features li::before {
      content: "✓";
      position: absolute;
      left: 0;
      color: #48bb78;
      font-weight: bold;
    }
    .signup-section {
      background: white;
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .signup-section h2 {
      font-size: 1.25rem;
      color: #2d3748;
      margin-bottom: 1rem;
    }
    .form-group {
      margin-bottom: 1rem;
    }
    .form-group label {
      display: block;
      font-weight: 500;
      color: #2d3748;
      margin-bottom: 0.375rem;
    }
    .form-group input,
    .form-group textarea {
      width: 100%;
      padding: 0.75rem 1rem;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 1rem;
      font-family: inherit;
    }
    .form-group textarea {
      min-height: 100px;
      resize: vertical;
    }
    .form-group input:focus,
    .form-group textarea:focus {
      outline: none;
      border-color: #4299e1;
      box-shadow: 0 0 0 3px rgba(66,153,225,0.2);
    }
    button[type="submit"] {
      width: 100%;
      padding: 1rem 1.5rem;
      font-size: 1rem;
      font-weight: 600;
      color: white;
      background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
      border: none;
      border-radius: 8px;
      cursor: pointer;
      margin-top: 0.5rem;
    }
    button[type="submit"]:hover {
      background: linear-gradient(135deg, #3182ce 0%, #2c5282 100%);
    }
    .message {
      margin-top: 1rem;
      padding: 1rem;
      border-radius: 8px;
      display: none;
    }
    .message.success {
      background: #c6f6d5;
      color: #22543d;
    }
    .message.error {
      background: #fed7d7;
      color: #742a2a;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Test Product</h1>
      <p class="tagline">Your idea, validated.</p>
    </header>
    <section class="features">
      <h2>Why join us</h2>
      <ul>
        <li>Get early access to innovative features</li>
        <li>Shape the product with your feedback</li>
        <li>Be the first to know when we launch</li>
      </ul>
    </section>
    <section class="signup-section">
      <h2>Join the waitlist</h2>
      <form id="signup-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input type="email" id="email" name="email" required placeholder="you@example.com">
        </div>
        <div class="form-group">
          <label for="text">Why do you want to join the waitlist?</label>
          <textarea id="text" name="text" placeholder="Tell us what you're looking for..."></textarea>
        </div>
        <button type="submit">Sign up now</button>
      </form>
      <div id="message" class="message"></div>
    </section>
  </div>
  <script>
    document.getElementById('signup-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const subdomain = window.location.hostname.split('.')[0] || 'test';
      const email = document.getElementById('email').value;
      const text = document.getElementById('text').value;
      const msgEl = document.getElementById('message');
      try {
        const res = await fetch('{{API_BASE_URL}}/api/smokes/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subdomain, email, text })
        });
        if (res.ok) {
          msgEl.textContent = 'Thanks for signing up!';
          msgEl.className = 'message success';
          msgEl.style.display = 'block';
          document.getElementById('signup-form').reset();
        } else {
          msgEl.textContent = 'Something went wrong. Please try again.';
          msgEl.className = 'message error';
          msgEl.style.display = 'block';
        }
      } catch (err) {
        msgEl.textContent = 'Something went wrong. Please try again.';
        msgEl.className = 'message error';
        msgEl.style.display = 'block';
      }
    });
  </script>
</body>
</html>
"""


def _build_idea_context(smoke_input: SmokeInput) -> str:
    parts: list[str] = [f"Description: {smoke_input.idea_description}"]
    if smoke_input.idea_title:
        parts.append(f"Title: {smoke_input.idea_title}")
    if smoke_input.idea_customer:
        parts.append(f"Target customer: {smoke_input.idea_customer}")
    if smoke_input.idea_geography:
        parts.append(f"Geography: {smoke_input.idea_geography}")
    return "\n".join(parts)


def _build_prompt(smoke_input: SmokeInput) -> str:
    features_text = "\n".join(
        f"- {f.feature}: {f.description}" for f in smoke_input.features
    )
    images_text = ", ".join(smoke_input.images) if smoke_input.images else "None"
    api_base = settings.api_base_url.rstrip("/")
    user_input_section = ""
    if smoke_input.user_input.strip():
        user_input_section = f"""

Additional instructions from the user (follow these): {smoke_input.user_input.strip()}
"""
    idea_context = _build_idea_context(smoke_input)
    return f"""Create a landing page for this smoke test.

Idea context:
{idea_context}

CTA (call-to-action): {smoke_input.cta}

Features to highlight:
{features_text}

Image URLs (use as needed): {images_text}
{user_input_section}

Produce a single self-contained HTML file. The HTML must be fully self-contained: put all CSS inside a <style> tag and all JavaScript inside a <script> tag.
No external links to .css or .js files.

Make it look cool: modern typography, appealing colors. The page should convert visitors into signups.

SIGNUP HANDLING: Use this API endpoint to manage sign ups. On form submit, POST to {api_base}/api/smokes/signup with JSON body:
{{"subdomain": "<subdomain>", "email": "<email>", "text": "<text>"}}. Extract subdomain from window.location.hostname (the part before the first dot, e.g. "my-app" from "my-app.example.com"). The endpoint requires no auth.

Add a text field for sign up so users can add additional info. Make the text field personalized to the idea: e.g. for a startup waitlist ask "Why do you want to join the waitlist?" or "What features are you most interested in?"; for a newsletter ask "What topics interest you most?"; for a product beta ask "What problem are you trying to solve?". Choose a prompt that fits the CTA and idea.

IMPORTANT: Return ONLY the raw HTML. No markdown code fences, no explanations, no text before or after. Start directly with <!DOCTYPE html> or <html> and end with </html>."""


def _get_test_html() -> str:
    api_base = settings.api_base_url.rstrip("/")
    return _TEST_HTML.replace("{{API_BASE_URL}}", api_base)


def generate_landing_page(smoke_input: SmokeInput) -> SmokeCode:
    if smoke_input.idea_description.strip().lower() == "test":
        return SmokeCode(html=_get_test_html(), css="", js="")

    model = ChatOpenRouter(
        model="anthropic/claude-sonnet-4.6",
        api_key=settings.openrouter_api_key,
        temperature=0.3,
        max_tokens=65536,
    )
    messages: list[HumanMessage] = [
        HumanMessage(content=_build_prompt(smoke_input)),
    ]

    try:
        response = model.invoke(messages)
        text = _extract_text(response.content)
        html = _extract_html_from_response(text)

        if not html or ("<html" not in html.lower() and "<!doctype" not in html.lower()):
            _log.error(
                "Claude did not return valid HTML. Response length=%d, preview=%s",
                len(text),
                repr(text[:500]) if text else "empty",
            )
            raise ValueError(
                "Landing page generation failed: model did not return valid HTML"
            )

        return SmokeCode(html=html, css="", js="")
    except ValueError:
        raise
    except Exception as e:
        _log.exception("Landing page generation failed: %s", e)
        raise
