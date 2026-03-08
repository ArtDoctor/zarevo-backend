## Zarevo backend

FastAPI backend + Celery worker for idea analysis and smoke page generation. Uses PocketBase for data, Redis for Celery broker/backend, and LLMs (OpenAI, OpenRouter, Vertex AI) for analyses.

To see frontend, visit [https://github.com/ArtDoctor/zarevo](https://github.com/ArtDoctor/zarevo).

### How analyses work

Each analysis type (market, customer, problem, competitor, technical, legal, financial) runs as a Celery task. The idea description plus optional fields (problem, customer, geography, founder_specific) are turned into prompts; LLMs return structured outputs (Pydantic models). Market analysis uses ChromaDB to match the idea to industries before sizing. Advanced runs all 7 analyses, then derive features from customer/competitor/problem for smoke pages.

**Note:** The analysis pipeline is a starting baseline. We will improve prompts, models, and structure over time.

### Security

- **Auth:** Ideas and smokes endpoints require a valid PocketBase Bearer token (`Authorization: Bearer <token>`).
- **Credits:** Basic analysis costs 1 credit, advanced 4; users must have enough credits (stored in PocketBase).
- **Admin:** `/api/admin` uses HTTP Basic auth (admin/admin) — will be changed in production.
- **CORS:** Temporarily allows everything, will be fixed after we finish DNS setups.

### Setup

1. Create venv and install deps:
  ```bash
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
  ```
2. Create `.env` with required vars (see `src/config.py`):
  - `REDIS_URL`, `POCKETBASE_URL`, `POCKETBASE_USER`, `POCKETBASE_PASSWORD`
  - `OPENAI_API_KEY`, `VERTEX_AI_API_KEY`, `OPENROUTER_API_KEY`
  - LangSmith: `LANGSMITH_TRACING`, `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`
  - `API_BASE_URL` (optional)
3. Run Redis and PocketBase (or use existing instances).

### Run

- **Dev**: `./start.sh` — starts Celery worker + uvicorn on port 26769
- **Prod**: `./prod_run.sh` — starts both (port 9076 by default, overridable via `PORT`)

### Tests

```bash
./run_tests.sh
```

### API

- `GET /health` — healthcheck
- `POST /api/ideas/new` — submit idea (basic: market, customer, problem)
- `POST /api/ideas/new/advanced` — full analysis (legal, technical, financial, competitor, etc.) + features
- Admin endpoints under `/api/admin` (basic auth: admin/admin)

