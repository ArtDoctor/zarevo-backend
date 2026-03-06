from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import admin, ideas

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ideas.router)
app.include_router(admin.router)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}
