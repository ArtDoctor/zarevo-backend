from fastapi import APIRouter, Depends, HTTPException

from src.config import IdeaRequest
from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token
from worker.worker import ANALYSIS_HANDLERS, process_idea_task, process_title_task, Status


router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.post("/new")
def submit_idea(
    idea: IdeaRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict:
    user_id = pb_client.get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    client = pb_client.client

    task_ids: list[str] = []
    auth_token = pb_client.get_auth_token()
    try:
        for task_type in ANALYSIS_HANDLERS:
            task_record = client.collection("analyses").create(
                {"status": Status.PENDING.value, "type": task_type}
            )

            task_id = task_record.id
            task_ids.append(task_id)
            process_idea_task.delay(task_id, idea.model_dump(), task_type, auth_token)

        idea_record = client.collection("ideas").create(
            {
                "description": idea.description,
                "author": user_id,
                "title": "",
                "problem": idea.problem,
                "customer": idea.customer,
                "founder_specific": idea.founder_specific,
                "analyses": task_ids
            }
        )
    except Exception:
        for task_id in task_ids:
            try:
                client.collection("analyses").delete(task_id)
            except Exception:
                pass
        raise

    process_title_task.delay(idea_record.id, idea.description, auth_token)

    return {
        "message": "Processing started",
        "idea_id": idea_record.id,
    }
