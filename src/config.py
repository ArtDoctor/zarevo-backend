from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    redis_url: str
    pocketbase_url: str
    openai_api_key: str
    vertex_ai_api_key: str
    openrouter_api_key: str

    pocketbase_user: str
    pocketbase_password: str

    langsmith_tracing: bool
    langsmith_endpoint: str
    langsmith_api_key: str
    langsmith_project: str

    api_base_url: str = "https://jo4gokk8s40c4gg848wow4ks.yza.yazero.io"


settings = Settings()


class IdeaRequest(BaseModel):
    description: str
    problem: str = ""
    customer: str = ""
    geography: str = ""
    founder_specific: str = ""
