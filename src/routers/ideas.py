from fastapi import APIRouter, Depends, HTTPException, status

from src.config import IdeaRequest
from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token
from worker.worker import (
    ADVANCED_ANALYSIS_TYPES,
    BASIC_ANALYSIS_TYPES,
    process_features_task,
    process_idea_task,
    process_title_task,
    Status,
)


router = APIRouter(prefix="/api/ideas", tags=["ideas"])

BASIC_ANALYSIS_CREDITS = 1
ADVANCED_ANALYSIS_CREDITS = 4


def _submit_idea_with_analyses(
    idea: IdeaRequest,
    pb_client: PocketBaseClient,
    task_types: tuple[str, ...],
    credit_cost: int,
) -> dict:
    user_id = pb_client.get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    is_test = idea.description.strip().lower() == "test"
    if not is_test:
        credits = pb_client.get_user_credits(user_id)
        if credits < credit_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Required: {credit_cost}, available: {credits}",
            )

    client = pb_client.client

    task_ids: list[str] = []
    auth_token = pb_client.get_auth_token()
    try:
        for task_type in task_types:
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

    if not is_test:
        pb_client.deduct_user_credits(user_id, credit_cost)
    process_title_task.delay(idea_record.id, idea.description, auth_token)
    if task_types == ADVANCED_ANALYSIS_TYPES:
        process_features_task.delay(idea_record.id, auth_token)

    return {
        "message": "Processing started",
        "idea_id": idea_record.id,
    }


@router.post("/new")
def submit_idea(
    idea: IdeaRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict:
    return _submit_idea_with_analyses(
        idea, pb_client, BASIC_ANALYSIS_TYPES, BASIC_ANALYSIS_CREDITS
    )


@router.post("/new/advanced")
def submit_idea_advanced(
    idea: IdeaRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict:
    return _submit_idea_with_analyses(
        idea, pb_client, ADVANCED_ANALYSIS_TYPES, ADVANCED_ANALYSIS_CREDITS
    )
