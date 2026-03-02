from fastapi import FastAPI

from src.routers import ideas

app = FastAPI()
app.include_router(ideas.router)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}
