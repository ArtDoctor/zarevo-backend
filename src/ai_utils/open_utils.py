from pydantic import BaseModel, Field

from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openrouter import ChatOpenRouter

from src.config import settings
from src.smokes.models import SmokeCode, SmokeInput


def _parse_tool_call(tc: object) -> tuple[str, dict]:
    if isinstance(tc, dict):
        return (tc.get("name", ""), tc.get("args", {}))
    name = tc.name if hasattr(tc, "name") else ""
    args = tc.args if hasattr(tc, "args") else {}
    return (name, args if isinstance(args, dict) else {})


def _get_tool_call_id(tc: object) -> str:
    if isinstance(tc, dict):
        return tc.get("id", "")
    return tc.id if hasattr(tc, "id") else ""


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


class StoreFileInput(BaseModel):
    file_type: str = Field(
        ...,
        description="Must be 'html'. Call this tool exactly once with the full self-contained HTML.",
    )
    content: str = Field(..., description="The full file content as a string.")


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

Produce a single self-contained HTML file. Use the store_file tool exactly once with file_type="html" and content=<full HTML string>.

The HTML must be fully self-contained: put all CSS inside a <style> tag and all JavaScript inside a <script> tag. No external links to .css or .js files.

Make it look cool: modern typography, appealing colors. The page should convert visitors into signups.
"""


def generate_landing_page(smoke_input: SmokeInput) -> SmokeCode:
    if smoke_input.idea_description.strip().lower() == "test":
        return SmokeCode(html=_TEST_HTML, css="", js="")

    model = ChatOpenRouter(
        model="anthropic/claude-sonnet-4.6",
        api_key=settings.openrouter_api_key,
        temperature=0.3,
        max_tokens=8192,
    )
    store_file_tool = StructuredTool.from_function(
        name="store_file",
        description="Store the HTML file. Call exactly once with file_type='html' and the full self-contained HTML content.",
        args_schema=StoreFileInput,
        func=lambda **kwargs: str(kwargs),
    )
    model_with_tools = model.bind_tools([store_file_tool])

    stored: dict[str, str] = {}
    messages: list[HumanMessage | AIMessage | ToolMessage] = [
        HumanMessage(content=_build_prompt(smoke_input)),
    ]

    max_iterations = 10
    for _ in range(max_iterations):
        response = model_with_tools.invoke(messages)
        if not isinstance(response, AIMessage):
            break

        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
        if not tool_calls:
            break

        messages.append(response)
        for tc in tool_calls:
            _, args = _parse_tool_call(tc)
            file_type = args.get("file_type", "").lower()
            content = args.get("content", "")
            if file_type == "html":
                stored["html"] = content
            messages.append(
                ToolMessage(
                    content=f"Stored {file_type} file ({len(content)} chars)",
                    tool_call_id=_get_tool_call_id(tc),
                )
            )

    html = stored.get("html", "")
    if not html:
        return SmokeCode(html=_TEST_HTML, css="", js="")

    return SmokeCode(html=html, css="", js="")
