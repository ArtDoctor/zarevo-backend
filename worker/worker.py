import random
import time

from celery import Celery
from collections.abc import Callable

from pydantic import BaseModel

from pocketbase.errors import ClientResponseError

from enum import Enum
from src.config import settings
from src.pocketbase_client import PocketBaseClient
from src.analyses.legal.legal import get_legal_analysis, get_example_legal_analysis
from src.analyses.technical.technical import get_technical_analysis, get_example_technical_analysis
from src.analyses.financial.financial import get_financial_analysis, get_example_financial_analysis
from src.analyses.competitor.competitor import get_competitor_analysis, get_example_competitor_analysis
from src.analyses.customer.customer import get_customer_analysis, get_example_customer_analysis
from src.analyses.problem.problem import get_problem_analysis, get_example_problem_analysis
from src.analyses.market.market import get_market_analysis, get_example_market_analysis
from src.ai_utils.open_utils import generate_landing_page
from src.ai_utils.vertex_utils import get_vertex_response
from src.config import IdeaRequest
from src.smokes.models import IdeaFeature, SmokeFeature, SmokeInput
from src.smokes.prepare import get_test_smoke_features, prepare_smoke_features_from_analyses


class TaskError(BaseModel):
    error: str


celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)

_redis_transport_opts = {
    "socket_keepalive": True,
    "health_check_interval": 30,
}
celery_app.conf.broker_transport_options = _redis_transport_opts
celery_app.conf.result_backend_transport_options = _redis_transport_opts

celery_app.conf.worker_cancel_long_running_tasks_on_connection_loss = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.broker_connection_retry = True


ANALYSIS_HANDLERS: dict[str, Callable[[dict], BaseModel]] = {
    "legal": get_legal_analysis,
    "technical": get_technical_analysis,
    "financial": get_financial_analysis,
    "competitor": get_competitor_analysis,
    "customer": get_customer_analysis,
    "problem": get_problem_analysis,
    "market": get_market_analysis,
}

BASIC_ANALYSIS_TYPES: tuple[str, ...] = ("market", "customer", "problem")
ADVANCED_ANALYSIS_TYPES: tuple[str, ...] = tuple(ANALYSIS_HANDLERS.keys())

FEATURES_ANALYSIS_TYPES_NEEDED = frozenset({"customer", "competitor", "problem"})
FEATURES_POLL_INTERVAL_SEC = 5
FEATURES_MAX_POLLS = 220

ANALYSIS_EXAMPLE_LOADERS: dict[str, Callable[[], BaseModel]] = {
    "legal": get_example_legal_analysis,
    "technical": get_example_technical_analysis,
    "financial": get_example_financial_analysis,
    "competitor": get_example_competitor_analysis,
    "customer": get_example_customer_analysis,
    "problem": get_example_problem_analysis,
    "market": get_example_market_analysis,
}


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ERROR = "error"


def _get_pocketbase_client(pocketbase_token: str | None) -> PocketBaseClient | None:
    if not pocketbase_token:
        return PocketBaseClient.for_admin()
    pb_client = PocketBaseClient()
    if not pb_client.authenticate_with_token(pocketbase_token):
        return None
    return pb_client


def _update_task_status(
    pb_client: PocketBaseClient | None,
    task_id: str,
    status: Status,
    result: dict | None = None,
) -> None:
    if pb_client is None:
        print("Cannot update task status: no PocketBase client")
        return
    body: dict[str, str | dict] = {"status": status.value}
    if result is not None:
        body["result"] = result

    try:
        pb_client.client.collection("analyses").update(task_id, body)
    except ClientResponseError as e:
        print(f"Error updating task status: {e}")


@celery_app.task
def process_idea_task(
    analysis_id: str,
    idea: dict,
    task_type: str = "market",
    pocketbase_token: str | None = None,
) -> None:
    pb_client = _get_pocketbase_client(pocketbase_token)
    _update_task_status(pb_client, analysis_id, Status.IN_PROGRESS)

    try:
        validated = IdeaRequest.model_validate(idea)
        if validated.description.lower() == "test":
            loader = ANALYSIS_EXAMPLE_LOADERS.get(task_type)
            if loader is None:
                raise ValueError(f"Unknown task_type: {task_type}")
            result = loader()
            time.sleep(random.uniform(1, 3))
        else:
            handler = ANALYSIS_HANDLERS.get(task_type)
            if handler is None:
                raise ValueError(f"Unknown task_type: {task_type}")
            result = handler(idea)

        _update_task_status(pb_client, analysis_id, Status.DONE, result.model_dump())

    except Exception as e:
        print(f"Error processing task: {e}")
        _update_task_status(
            pb_client, analysis_id, Status.ERROR, TaskError(error=str(e)).model_dump()
        )


def _generate_title_prompt(description: str) -> str:
    return (
        f"""Generate a short one-line title for this idea description:
        <description>
        {description}
        </description>
        Return only the title, no other text."""
    )


@celery_app.task
def process_title_task(
    idea_id: str,
    description: str,
    pocketbase_token: str | None = None,
) -> None:
    try:
        title = (
            "Example Idea Title"
            if description == "test"
            else get_vertex_response(_generate_title_prompt(description)).text
        )
        pb_client = _get_pocketbase_client(pocketbase_token)
        if pb_client is not None:
            pb_client.client.collection("ideas").update(idea_id, {"title": title})
    except Exception as e:
        print(f"Error generating title: {e}")


def _get_analysis_ids(idea: object) -> list[str]:
    try:
        val = idea.analyses
    except AttributeError:
        return []
    if not isinstance(val, list):
        return []
    return [x for x in val if isinstance(x, str)]


def _wait_for_features_analyses(
    pb_client: PocketBaseClient,
    idea: object,
) -> dict[str, dict] | None:
    analysis_ids = _get_analysis_ids(idea)
    for _ in range(FEATURES_MAX_POLLS):
        analyses_by_type: dict[str, dict] = {}
        for aid in analysis_ids:
            try:
                rec = pb_client.client.collection("analyses").get_one(aid)
            except ClientResponseError:
                continue
            try:
                atype = rec.type
                status_val = rec.status
                result = rec.result
            except AttributeError:
                continue
            if atype not in FEATURES_ANALYSIS_TYPES_NEEDED:
                continue
            if status_val != "done":
                break
            if result is None or not isinstance(result, dict):
                continue
            analyses_by_type[atype] = result
        else:
            if FEATURES_ANALYSIS_TYPES_NEEDED <= set(analyses_by_type.keys()):
                return analyses_by_type
        time.sleep(FEATURES_POLL_INTERVAL_SEC)
    return None


@celery_app.task
def process_features_task(
    idea_id: str,
    pocketbase_token: str | None = None,
) -> None:
    pb_client = _get_pocketbase_client(pocketbase_token)
    if pb_client is None:
        print("Cannot run features task: no PocketBase client")
        return

    try:
        idea = pb_client.client.collection("ideas").get_one(idea_id)
        try:
            description = idea.description or ""
        except AttributeError:
            description = ""
        is_test = str(description).strip().lower() == "test"

        if is_test:
            smoke_features = get_test_smoke_features()
        else:
            analyses_by_type = _wait_for_features_analyses(pb_client, idea)
            if analyses_by_type is None:
                print(f"Features task timed out waiting for analyses on idea {idea_id}")
                return
            smoke_features = prepare_smoke_features_from_analyses(
                analyses_by_type["customer"],
                analyses_by_type["competitor"],
                analyses_by_type["problem"],
            )

        idea_features = [
            IdeaFeature(
                title=f.feature,
                description=f.description,
                expected_signup_increase_pct=f.expected_signup_increase_pct,
            )
            for f in smoke_features
        ]
        features_data = {"features": [x.model_dump() for x in idea_features]}
        pb_client.client.collection("ideas").update(idea_id, features_data)
    except ClientResponseError as e:
        print(f"Error in features task: {e}")
    except Exception as e:
        print(f"Error processing features: {e}")


@celery_app.task
def process_smoke_generation_task(
    smoke_id: str,
    pocketbase_token: str | None = None,
) -> None:
    pb_client = _get_pocketbase_client(pocketbase_token)
    if pb_client is None:
        print("Cannot run smoke generation task: no PocketBase client")
        return

    try:
        smoke = pb_client.client.collection("smokes").get_one(smoke_id)
        idea_ref = smoke.idea if hasattr(smoke, "idea") else None
        idea_id = idea_ref.id if hasattr(idea_ref, "id") else (
            idea_ref if isinstance(idea_ref, str) else None
        )
        if not idea_id:
            print(f"Smoke {smoke_id} has no idea relation")
            return

        idea = pb_client.client.collection("ideas").get_one(idea_id)
        idea_description = idea.description if hasattr(idea, "description") else ""

        features_raw = smoke.features if hasattr(smoke, "features") else []
        features = [
            SmokeFeature(
                feature=f.get("feature", ""),
                description=f.get("description", ""),
                expected_signup_increase_pct=float(f.get("expected_signup_increase_pct", 0)),
            )
            for f in (features_raw if isinstance(features_raw, list) else [])
            if isinstance(f, dict)
        ]
        cta = smoke.cta if hasattr(smoke, "cta") else ""
        images_raw = smoke.images if hasattr(smoke, "images") else []
        images = list(images_raw) if isinstance(images_raw, list) else []

        smoke_input = SmokeInput(
            idea_description=idea_description,
            cta=cta,
            features=features,
            images=images,
        )
        code = generate_landing_page(smoke_input)

        pb_client.client.collection("smokes").update(
            smoke_id,
            {
                "html": code.html,
                "css": code.css,
                "js": code.js,
                "state": "done",
            },
        )
    except ClientResponseError as e:
        print(f"Error in smoke generation task: {e}")
        if pb_client is not None:
            try:
                pb_client.client.collection("smokes").update(
                    smoke_id,
                    {"state": "error"},
                )
            except Exception:
                pass
    except Exception as e:
        print(f"Error processing smoke generation: {e}")
        if pb_client is not None:
            try:
                pb_client.client.collection("smokes").update(
                    smoke_id,
                    {"state": "error"},
                )
            except Exception:
                pass
