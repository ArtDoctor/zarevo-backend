from celery import Celery
from collections.abc import Callable
import requests
from pydantic import BaseModel

from src.config import settings
from src.analyses.legal.legal import get_legal_analysis
from src.analyses.technical.technical import get_technical_analysis
from src.analyses.financial.financial import get_financial_analysis
from src.analyses.competitor.competitor import get_competitor_analysis
from src.analyses.customer.customer import get_customer_analysis
from src.analyses.problem.problem import get_problem_analysis
from src.analyses.market.market import get_market_analysis


class TaskError(BaseModel):
    error: str


celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)


ANALYSIS_HANDLERS: dict[str, Callable[[], BaseModel]] = {
    "legal": get_legal_analysis,
    "technical": get_technical_analysis,
    "financial": get_financial_analysis,
    "competitor": get_competitor_analysis,
    "customer": get_customer_analysis,
    "problem": get_problem_analysis,
    "market": get_market_analysis,
}


@celery_app.task
def process_idea_task(task_id: str, idea_description: str, task_type: str = "market"):
    pb_task_url = f"{settings.pocketbase_url}/api/collections/tasks/records/{task_id}"

    requests.patch(pb_task_url, json={"status": "processing"})

    try:
        handler = ANALYSIS_HANDLERS.get(task_type)
        if handler is None:
            raise ValueError(f"Unknown task_type: {task_type}")

        result = handler()

        requests.patch(pb_task_url, json={
            "status": "completed",
            "result": result.model_dump()
        })

    except Exception as e:
        requests.patch(pb_task_url, json={
            "status": "failed",
            "result": TaskError(error=str(e)).model_dump()
        })
