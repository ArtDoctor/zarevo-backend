from fastapi import APIRouter, HTTPException
import requests

from src.config import settings, IdeaRequest
from worker.worker import process_idea_task


router = APIRouter(prefix="/api/ideas", tags=["ideas"])


@router.post("")
def submit_idea(idea: IdeaRequest) -> dict:
    idea_resp = requests.post(
        f"{settings.pocketbase_url}/api/collections/ideas/records",
        json={"title": idea.title, "description": idea.description, "user": idea.user_id}
    )
    if not idea_resp.ok:
        raise HTTPException(status_code=500, detail="Failed to create idea in PocketBase")

    idea_id = idea_resp.json()["id"]

    task_resp = requests.post(
        f"{settings.pocketbase_url}/api/collections/tasks/records",
        json={"idea_id": idea_id, "status": "pending", "task_type": "openai_validation"}
    )
    if not task_resp.ok:
        raise HTTPException(status_code=500, detail="Failed to create task in PocketBase")

    task_id = task_resp.json()["id"]

    process_idea_task.delay(task_id, idea.description)

    return {
        "message": "Processing started",
        "idea_id": idea_id,
        "task_id": task_id
    }


@router.get("/{task_id}/result")
def check_result(task_id: str) -> dict:
    resp = requests.get(
        f"{settings.pocketbase_url}/api/collections/tasks/records/{task_id}"
    )
    if not resp.ok:
        raise HTTPException(status_code=404, detail="Task not found")

    data = resp.json()
    return {
        "task_id": task_id,
        "status": data.get("status"),
        "result": data.get("result")
    }
