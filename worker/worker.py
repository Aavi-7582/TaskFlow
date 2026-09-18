import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

from redis_client import redis_client
from database import SessionLocal
from models import Task
from executor import execute_task


def run_worker():

    print("Worker started...")

    while True:

        # Wait for a task
        result = redis_client.blpop("task_queue", timeout=10)

        if result is None:
            print("No tasks. Waiting...")
            continue

        _, task_id = result

        print(f"Received task: {task_id}")

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

            print(f"Task {task.id} completed: {result}")

        except Exception as e:

            print(f"Task failed: {e}")

            task.status = "FAILED"
            db.commit()

        finally:
            db.close()


if __name__ == "__main__":
    run_worker()