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
from src.ai_utils.vertex_utils import get_vertex_response
from src.config import IdeaRequest


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
