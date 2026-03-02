from pocketbase import PocketBase

from src.config import settings


def get_client() -> PocketBase:
    return PocketBase(settings.pocketbase_url)
