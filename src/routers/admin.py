import secrets
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
    else:
        result = handler(request.model_dump(exclude={"analysis_type"}))

    return {"type": analysis_type, "result": result.model_dump()}

