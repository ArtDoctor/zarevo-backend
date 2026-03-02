from fastapi import APIRouter

from src.config import IdeaRequest
from src.pocketbase_client import get_client
from worker.worker import ANALYSIS_HANDLERS, process_idea_task, process_title_task, Status


router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.post("/new")
def submit_idea(idea: IdeaRequest) -> dict:
    client = get_client()

    task_ids = []
    for task_type in ANALYSIS_HANDLERS:
        task_record = client.collection("analyses").create(
            {"status": Status.PENDING.value, "type": task_type}
        )

        task_id = task_record.id
        task_ids.append(task_id)
        process_idea_task.delay(task_id, idea.model_dump(), task_type)

    idea_record = client.collection("ideas").create(
        {
            "description": idea.description,
            "author": idea.user_id,
            "title": "",
            "problem": idea.problem,
            "customer": idea.customer,
            "founder_specific": idea.founder_specific,
            "analyses": task_ids
        }
    )

    process_title_task.delay(idea_record.id, idea.description)

    return {
        "message": "Processing started",
        "idea_id": idea_record.id,
    }
