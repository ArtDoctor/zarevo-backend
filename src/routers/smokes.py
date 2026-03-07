import math

from fastapi import APIRouter, Depends, HTTPException, status
from pocketbase.errors import ClientResponseError

from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token
from src.smokes.models import CreateSmokeRequest, PublishSmokeRequest, SmokeFeature
from worker.worker import process_smoke_generation_task


router = APIRouter(prefix="/api/smokes", tags=["smokes"])


@router.post("/create")
def create_smoke(
    body: CreateSmokeRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict[str, str]:
    client = pb_client.client
    features_data = [f.model_dump() for f in body.features]
    record_data = {
        "idea": body.idea_id,
        "cta": body.cta,
        "features": features_data,
        "images": body.images,
        "state": "in_progress",
    }
    try:
        record = client.collection("smokes").create(record_data)
        auth_token = pb_client.get_auth_token()
        process_smoke_generation_task.delay(record.id, auth_token)
        return {"id": record.id}
    except ClientResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create smoke record: {e}",
        ) from e


def _compute_publish_credit_cost(duration: int, ads_channels: list) -> int:
    duration_credits = math.ceil(duration / 3)
    advertiser_count = sum(1 for ch in ads_channels if ch.advertised.lower() == "yes")
    return duration_credits + advertiser_count


@router.post("/publish")
def publish_smoke(
    body: PublishSmokeRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict[str, str]:
    user_id = pb_client.get_current_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    client = pb_client.client
    try:
        smoke = client.collection("smokes").get_one(body.smoke_id)
    except ClientResponseError as e:
        raise HTTPException(status_code=404, detail="Smoke not found") from e

    idea_ref = smoke.idea if hasattr(smoke, "idea") else None
    idea_id = idea_ref.id if hasattr(idea_ref, "id") else (
        idea_ref if isinstance(idea_ref, str) else None
    )
    if not idea_id:
        raise HTTPException(status_code=404, detail="Smoke has no linked idea")

    idea = client.collection("ideas").get_one(idea_id)
    idea_author = idea.author if hasattr(idea, "author") else None
    author_id = idea_author.id if hasattr(idea_author, "id") else (
        idea_author if isinstance(idea_author, str) else None
    )
    if author_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this smoke")

    credit_cost = _compute_publish_credit_cost(body.duration, body.ads_channels)
    credits = pb_client.get_user_credits(user_id)
    if credits < credit_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {credit_cost}, available: {credits}",
        )

    pb_client.deduct_user_credits(user_id, credit_cost)
    ads_channels_data = [ch.model_dump() for ch in body.ads_channels]
    client.collection("smokes").update(
        body.smoke_id,
        {
            "domain": body.subdomain,
            "duration": body.duration,
            "start_date": body.start_date.isoformat(),
            "ad_channels": ads_channels_data,
        },
    )
    return {"message": "Smoke published"}
