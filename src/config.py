from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str
    pocketbase_url: str
    openai_api_key: str
    vertex_ai_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()


class IdeaRequest(BaseModel):
    title: str
    description: str
    user_id: str
