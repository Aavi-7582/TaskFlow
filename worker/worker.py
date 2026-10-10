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
from sqlalchemy import update
from models import Task, Worker



from redis_client import redis_client
from database import SessionLocal
from models import Task
from executor import execute_task

# How often this worker refreshes its heartbeat. Kept short so the monitor
# (worker/monitor.py) can notice a dead worker within ~2s.
# Override with the HEARTBEAT_INTERVAL env var if a slower beat is wanted.
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL", "1"))

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

            if not task:
                print(f"Worker {WORKER_ID}: task {task_id} not found")
                continue

            # Conditional claim: only take ownership if the task is still
            # QUEUED. This prevents two workers from both claiming the same
            # task and stops us from resurrecting a task we no longer own.
            claim = db.execute(
                update(Task)
                .where(
                    Task.id == task.id,
                    Task.status == "QUEUED",
                )
                .values(worker_id=WORKER_ID, status="RUNNING")
            )
            db.commit()

            if claim.rowcount == 0:
                # Already claimed by another worker, or already finished.
                print(
                    f"Worker {WORKER_ID} skipping task {task.id}: "
                    f"not QUEUED (already claimed or finished)"
                )
                continue

            result = execute_task(
                task.task_type,
                task.payload
            )

            # Conditional completion: only write SUCCESS if we STILL own the
            # task and it is STILL RUNNING. If the monitor requeued/reassigned
            # it in the meantime, this matches 0 rows and we do NOT clobber the
            # newer state (prevents the lost-update race).
            done = db.execute(
                update(Task)
                .where(
                    Task.id == task.id,
                    Task.worker_id == WORKER_ID,
                    Task.status == "RUNNING",
                )
                .values(status="SUCCESS", result=str(result))
            )
            db.commit()

            if done.rowcount == 0:
                print(
                    f"Worker {WORKER_ID}: task {task.id} was requeued/"
                    f"reassigned before completion; not overwriting"
                )
            else:
                print(
                    f"Worker {WORKER_ID} completed task {task.id}: {result}"
                )

        except Exception as e:

            print(f"Worker {WORKER_ID} failed to complete task {task_id}: {e}")

            # Only mark FAILED if we still own it and it is still RUNNING;
            # otherwise leave any requeued/reassigned state untouched.
            try:
                db.execute(
                    update(Task)
                    .where(
                        Task.id == int(task_id),
                        Task.worker_id == WORKER_ID,
                        Task.status == "RUNNING",
                    )
                    .values(status="FAILED")
                )
                db.commit()
            except Exception as inner:
                print(
                    f"Worker {WORKER_ID}: failed to mark task "
                    f"{task_id} FAILED: {inner}"
                )

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

        time.sleep(HEARTBEAT_INTERVAL)

if __name__ == "__main__":
    run_worker()