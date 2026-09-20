import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

import uuid
import threading
import time
from datetime import datetime
from models import Task, Worker



from redis_client import redis_client
from database import SessionLocal
from models import Task
from executor import execute_task

WORKER_ID = str(uuid.uuid4())[:8]

db = SessionLocal()

worker = Worker(
    worker_id=WORKER_ID,
    status="ACTIVE"
)

db.add(worker)
db.commit()
db.close()

def run_worker():

    print(f"Worker {WORKER_ID} started...")
    heartbeat_db = SessionLocal()

    threading.Thread(
        target=heartbeat,
        args=(heartbeat_db, WORKER_ID),
        daemon=True
    ).start()

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
            task.worker_id = WORKER_ID
            task.status = "RUNNING"
            db.commit()

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

def heartbeat(db, worker_id):
    while True:
        worker = db.query(Worker).filter(
            Worker.worker_id == worker_id
        ).first()

        if worker:
            worker.last_heartbeat = datetime.utcnow()
            worker.status = "ACTIVE"
            db.commit()

        time.sleep(5)

if __name__ == "__main__":
    run_worker()