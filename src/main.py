from fastapi import FastAPI

from src.routers import ideas
from src.routers import testing

app = FastAPI()
app.include_router(ideas.router)
app.include_router(testing.router)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}
