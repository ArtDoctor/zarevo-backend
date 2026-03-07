from fastapi import APIRouter, Depends, HTTPException, status
from pocketbase.errors import ClientResponseError

from src.pocketbase_client import PocketBaseClient, verify_pocketbase_token
from src.smokes.models import CreateSmokeRequest, SmokeFeature


router = APIRouter(prefix="/api/smokes", tags=["smokes"])


@router.post("/create")
def create_smoke(
    body: CreateSmokeRequest,
    pb_client: PocketBaseClient = Depends(verify_pocketbase_token),
) -> dict[str, str]:
    client = pb_client.client
    features_data = [f.model_dump() for f in body.features]
    record_data = {
        "cta": body.cta,
        "features": features_data,
        "images": body.images,
        "state": "queued",
    }
    try:
        record = client.collection("smokes").create(record_data)
        return {"id": record.id}
    except ClientResponseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create smoke record: {e}",
        ) from e
