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
  <title>Test Landing Page</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; padding: 2rem; }
    header { text-align: center; margin-bottom: 2rem; }
    h1 { font-size: 2rem; color: #333; }
    .cta { text-align: center; }
    button { padding: 1rem 2rem; font-size: 1rem; cursor: pointer; }
  </style>
</head>
<body>
  <header>
    <h1>Test Product</h1>
    <p>Your idea, validated.</p>
  </header>
  <main>
    <section class="cta">
      <button id="signup-btn">Sign up now</button>
    </section>
  </main>
  <script>
    document.getElementById('signup-btn').addEventListener('click', () => {
      alert('Thanks for signing up!');
    });
  </script>
</body>
</html>
"""


def _build_prompt(smoke_input: SmokeInput) -> str:
    features_text = "\n".join(
        f"- {f.feature}: {f.description}" for f in smoke_input.features
    )
    images_text = ", ".join(smoke_input.images) if smoke_input.images else "None"
    return f"""Create a landing page for this smoke test. The idea: {smoke_input.idea_description}

CTA (call-to-action): {smoke_input.cta}

Features to highlight:
{features_text}

Image URLs (use as needed): {images_text}

Produce a single self-contained HTML file. The HTML must be fully self-contained: put all CSS inside a <style> tag and all JavaScript inside a <script> tag. No external links to .css or .js files.

Make it look cool: modern typography, appealing colors. The page should convert visitors into signups.

IMPORTANT: Return ONLY the raw HTML. No markdown code fences, no explanations, no text before or after. Start directly with <!DOCTYPE html> or <html> and end with </html>."""


def generate_landing_page(smoke_input: SmokeInput) -> SmokeCode:
    if smoke_input.idea_description.strip().lower() == "test":
        return SmokeCode(html=_TEST_HTML, css="", js="")

    model = ChatOpenRouter(
        model="anthropic/claude-sonnet-4.6",
        api_key=settings.openrouter_api_key,
        temperature=0.3,
        max_tokens=8192,
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
