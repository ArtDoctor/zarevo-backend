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
  <link rel="stylesheet" href="styles.css">
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
  <script src="script.js"></script>
</body>
</html>
"""

_TEST_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; padding: 2rem; }
header { text-align: center; margin-bottom: 2rem; }
h1 { font-size: 2rem; color: #333; }
.cta { text-align: center; }
button { padding: 1rem 2rem; font-size: 1rem; cursor: pointer; }
"""

_TEST_JS = """document.getElementById('signup-btn').addEventListener('click', () => {
  alert('Thanks for signing up!');
});
"""


class StoreFileInput(BaseModel):
    file_type: str = Field(
        ...,
        description="One of 'html', 'css', or 'js'. Call this tool exactly three times: once for each file type.",
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

You must produce exactly 3 files: index.html, styles.css, script.js. Use the store_file tool for each one.

How to use store_file:
1. Call store_file with file_type="html" and content=<full HTML string>. The HTML should link to styles.css and script.js.
2. Call store_file with file_type="css" and content=<full CSS string>.
3. Call store_file with file_type="js" and content=<full JS string>.

Make it look cool: modern typography, appealing colors, smooth interactions. The page should convert visitors into signups.
"""


def generate_landing_page(smoke_input: SmokeInput) -> SmokeCode:
    if smoke_input.idea_description.strip().lower() == "test":
        return SmokeCode(html=_TEST_HTML, css=_TEST_CSS, js=_TEST_JS)

    model = ChatOpenRouter(
        model="anthropic/claude-sonnet-4.6",
        api_key=settings.openrouter_api_key,
        temperature=0.3,
        max_tokens=8192,
    )
    store_file_tool = StructuredTool.from_function(
        name="store_file",
        description="Store a file. Call exactly 3 times: file_type='html', 'css', 'js' with full content.",
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
            if file_type in ("html", "css", "js"):
                stored[file_type] = content
            messages.append(
                ToolMessage(
                    content=f"Stored {file_type} file ({len(content)} chars)",
                    tool_call_id=_get_tool_call_id(tc),
                )
            )

    html = stored.get("html", "")
    css = stored.get("css", "")
    js = stored.get("js", "")
    if not html or not css or not js:
        return SmokeCode(html=_TEST_HTML, css=_TEST_CSS, js=_TEST_JS)

    return SmokeCode(html=html, css=css, js=js)
