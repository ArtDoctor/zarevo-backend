from celery import Celery
import requests
import time
from src.config import settings

# Initialize Celery
celery_app = Celery(
    "worker",
    broker=settings.redis_url,
    backend=settings.redis_url
)


@celery_app.task
def process_idea_task(task_id: str, idea_description: str):
    pb_task_url = f"{settings.pocketbase_url}/api/collections/tasks/records/{task_id}"

    # 1. Mark task as processing
    requests.patch(pb_task_url, json={"status": "processing"})

    try:
        # 2. Call OpenAI (Simulated here)
        # client = OpenAI(api_key=settings.openai_api_key)
        # response = client.chat.completions.create(...)
        time.sleep(3)
        result_data = {"analysis": "Market looks favorable."}  # Replace with actual OpenAI JSON response

        # 3. Mark task as completed with results
        requests.patch(pb_task_url, json={
            "status": "completed",
            "result": result_data
        })

    except Exception as e:
        # 4. Handle failures
        requests.patch(pb_task_url, json={
            "status": "failed",
            "result": {"error": str(e)}
        })
