import time
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from pocketbase import PocketBase
from pocketbase.models.record import Record

from src.config import settings


class PocketBaseClient:
    def __init__(self) -> None:
        self.base_url = settings.pocketbase_url
        self.client = PocketBase(self.base_url)
        self._auth_valid_until: float = 0.0

    def authenticate_with_token(self, token: str) -> bool:
        try:
            current_time = time.time()
            if self.client.auth_store.token == token and current_time < self._auth_valid_until:
                return True

            self.client.auth_store.save(token, None)
            res = self.client.collection("users").auth_refresh()
            if res.is_valid:
                self._auth_valid_until = current_time + 900
                return True
            return False
        except Exception:
            return False

    def get_current_user(self) -> Optional[Record]:
        if not self.client.auth_store:
            return None
        model = self.client.auth_store.model
        if isinstance(model, Record):
            return model
        return None

    def get_current_user_id(self) -> Optional[str]:
        user = self.get_current_user()
        if user is None:
            return None
        return user.id

    def get_auth_token(self) -> Optional[str]:
        if not self.client.auth_store or not self.client.auth_store.token:
            return None
        return self.client.auth_store.token

    def create_idea(
        self, prompt: str, task_id: str, user_id: str, **extra_fields: Any
    ) -> Record:
        idea_data: dict[str, str | None] = {
            "name": prompt,
            "description": prompt,
            "market_analysis": None,
            "author": user_id,
            "task_id": task_id,
        }
        idea_data.update(extra_fields)
        return self.client.collection("ideas").create(idea_data)


async def verify_pocketbase_token(request: Request) -> PocketBaseClient:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    pb_client = PocketBaseClient()

    if not pb_client.authenticate_with_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return pb_client
