import sys
import os
import uuid

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

from redis_client import redis_client
from database import SessionLocal
from models import Task
from executor import execute_task

WORKER_ID = str(uuid.uuid4())[:8]

def run_worker():

    print(f"Worker {WORKER_ID} started...")

    while True:

        # Wait for a task
        result = redis_client.blpop("task_queue", timeout=10)

        if result is None:
            print("No tasks. Waiting...")
            continue

        _, task_id = result

        print(f"Worker {WORKER_ID} received task: {task_id}")

        db = SessionLocal()

        try:
            task = db.get(Task, int(task_id))

            if not task:
                print("Task not found")
                continue

            task.status = "RUNNING"
            db.commit()

            result = execute_task(
                task.task_type,
                task.payload
            )

            task.status = "SUCCESS"
            task.result = str(result)

            db.commit()

            print(
                f"Worker {WORKER_ID} completed task {task.id}: {result}"
            )

        except Exception as e:

            print(f"Worker {WORKER_ID} failed to complete task {task.id}: {e}")

            task.status = "FAILED"
            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    run_worker()