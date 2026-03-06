import json
import random
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.config import IdeaRequest
from worker.worker import ANALYSIS_EXAMPLE_LOADERS, ANALYSIS_HANDLERS


router = APIRouter(prefix="/api/admin", tags=["admin"])

_security = HTTPBasic()

# Hard-coded basic auth credentials for admin/debug usage.
_ADMIN_USERNAME = "admin"
_ADMIN_PASSWORD = "admin"

_MIN_DESCRIPTION_LENGTH = 10


class AdminGetAnalysisRequest(IdeaRequest):
    analysis_type: str


def _require_admin_basic_auth(
    credentials: HTTPBasicCredentials = Depends(_security),
) -> None:
    username_ok = secrets.compare_digest(credentials.username, _ADMIN_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, _ADMIN_PASSWORD)
    if username_ok and password_ok:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid basic auth credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def _save_analysis(analysis_type: str, request: dict[str, Any], result: dict[str, Any]) -> None:
    analyses_dir = Path("analyses_admin")
    analyses_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{analysis_type}.json"
    path = analyses_dir / filename
    payload = {"request": request, "result": result}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@router.post("/analysis")
def admin_get_analysis(
    request: AdminGetAnalysisRequest,
    _: None = Depends(_require_admin_basic_auth),
) -> dict[str, Any]:
    analysis_type = request.analysis_type
    handler = ANALYSIS_HANDLERS.get(analysis_type)
    if handler is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown analysis type: {analysis_type}",
        )

    if request.description.strip().lower() == "test":
        loader = ANALYSIS_EXAMPLE_LOADERS.get(analysis_type)
        if loader is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown analysis type: {analysis_type}",
            )
        result = loader()
        time.sleep(random.uniform(1, 3))
    else:
        if len(request.description.strip()) < _MIN_DESCRIPTION_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Description must be at least {_MIN_DESCRIPTION_LENGTH} characters",
            )
        result = handler(request.model_dump(exclude={"analysis_type"}))

    result_dict = result.model_dump()
    response = {"type": analysis_type, "result": result_dict}

    request_dict = request.model_dump()
    if request.description.strip().lower() != "test":
        _save_analysis(analysis_type, request_dict, result_dict)

    return response
