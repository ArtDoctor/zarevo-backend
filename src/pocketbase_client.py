import time
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from pocketbase import PocketBase
from pocketbase.models.record import Record

from src.config import settings


def _create_admin_client() -> PocketBase:
    client = PocketBase(settings.pocketbase_url)
    client.admins.auth_with_password(
        settings.pocketbase_user,
        settings.pocketbase_password,
    )
    return client


class PocketBaseClient:
    def __init__(self, admin_only: bool = False) -> None:
        self.base_url = settings.pocketbase_url
        self._user_client = PocketBase(settings.pocketbase_url)
        self._admin_client: PocketBase = _create_admin_client()
        self._auth_valid_until: float = 0.0
        self._admin_only = admin_only

    @property
    def client(self) -> PocketBase:
        return self._admin_client

    @classmethod
    def for_admin(cls) -> "PocketBaseClient":
        return cls(admin_only=True)

    def authenticate_with_token(self, token: str) -> bool:
        if self._admin_only:
            return True
        try:
            current_time = time.time()
            if (
                self._user_client.auth_store.token == token
                and current_time < self._auth_valid_until
            ):
                return True

            self._user_client.auth_store.save(token, None)
            res = self._user_client.collection("users").auth_refresh()
            if res.is_valid:
                self._auth_valid_until = current_time + 900
                return True
            return False
        except Exception:
            return False

    def get_current_user(self) -> Optional[Record]:
        if self._admin_only or not self._user_client.auth_store:
            return None
        model = self._user_client.auth_store.model
        if isinstance(model, Record):
            return model
        return None

    def get_current_user_id(self) -> Optional[str]:
        user = self.get_current_user()
        if user is None:
            return None
        return user.id

    def get_auth_token(self) -> Optional[str]:
        if (
            self._admin_only
            or not self._user_client.auth_store
            or not self._user_client.auth_store.token
        ):
            return None
        return self._user_client.auth_store.token

    def get_user_credits(self, user_id: str) -> int:
        user = self._admin_client.collection("users").get_one(user_id)
        try:
            return int(user.credits)
        except (AttributeError, TypeError, ValueError):
            return 0

    def deduct_user_credits(self, user_id: str, amount: int) -> None:
        credits = self.get_user_credits(user_id)
        new_credits = max(0, credits - amount)
        self._admin_client.collection("users").update(user_id, {"credits": new_credits})

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
        return self._admin_client.collection("ideas").create(idea_data)


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
