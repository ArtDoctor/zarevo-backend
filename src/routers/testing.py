from fastapi import APIRouter

from src.config import IdeaRequest


router = APIRouter(prefix="/test-api/ideas", tags=["ideas"])


@router.post("")
def submit_idea(idea: IdeaRequest) -> dict:
    return {
        "message": "Processing started",
        "idea_id": 1,
        "task_id": 1
    }


@router.get("/{task_id}/result")
def check_result(task_id: str) -> dict:

    return {
        "task_id": task_id,
        "status": "completed",
        "result": {
            "analysis": "Market looks favorable."
        }
    }
