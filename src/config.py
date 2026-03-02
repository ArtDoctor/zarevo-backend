from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    redis_url: str
    pocketbase_url: str
    openai_api_key: str
    vertex_ai_api_key: str

    pocketbase_user: str
    pocketbase_password: str


settings = Settings()


class IdeaRequest(BaseModel):
    user_id: str
    description: str
    problem: str = ""
    customer: str = ""
    geography: str = ""
    founder_specific: str = ""
