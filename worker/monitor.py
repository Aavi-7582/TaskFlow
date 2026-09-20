import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)


from models import Worker, Task
from redis_client import redis_client
import time
from datetime import datetime, timezone, timedelta

from database import SessionLocal

TIMEOUT = 10
MAX_RETRIES = 3

def monitor_workers():
    while True:
        db = SessionLocal()

        workers = db.query(Worker).all()

        for worker in workers:
            if datetime.utcnow() - worker.last_heartbeat > timedelta(seconds=TIMEOUT):
                if worker.status != "DEAD":
                    worker.status = "DEAD"
                    print(f"Worker {worker.worker_id} marked DEAD")

                    tasks = db.query(Task).filter(
                        Task.worker_id == worker.worker_id,
                        Task.status == "RUNNING"
                    ).all()

                    for task in tasks:
                        if task.retry_count < MAX_RETRIES:
                            task.retry_count += 1
                            task.status = "QUEUED"
                            task.worker_id = None

                            redis_client.rpush(
                                "task_queue",
                                task.id
                            )

                            print(
                                f"Requeued task {task.id} "
                                f"(retry {task.retry_count}/{MAX_RETRIES})"
                            )

                        else:
                            task.status = "FAILED"

                            print(
                                f"Task {task.id} permanently failed"
                            )

        db.commit()
        db.close()

        time.sleep(5)


if __name__ == "__main__":
    monitor_workers()