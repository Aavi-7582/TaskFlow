import sys
import os
import json
import urllib.request

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "backend")
    )
)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


def notify_frontend(message: dict):
    # Push an event to all connected WebSocket clients via the backend,
    # so the dashboard updates without a manual page refresh
    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/internal/broadcast",
            data=json.dumps(message).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Failed to notify frontend: {e}")



from models import Worker, Task
from redis_client import redis_client
import time
from datetime import datetime, timezone, timedelta

from database import SessionLocal, engine
from sqlalchemy import func

# Detection tuning (env-overridable so latency can be changed without
# touching code):
#   WORKER_TIMEOUT   - heartbeat age after which a worker is called DEAD
#   MONITOR_INTERVAL - how often the monitor re-checks the database
# Defaults are tuned so a worker that stops heartbeating (heartbeat
# interval is 1s, see worker/worker.py) shows up as DEAD ~2s later
TIMEOUT = float(os.environ.get("WORKER_TIMEOUT", "2"))
MONITOR_INTERVAL = float(os.environ.get("MONITOR_INTERVAL", "0.5"))
MAX_RETRIES = 3

# Task states the dashboard can still see change (terminal states never move)
ACTIVE_STATUSES = ("QUEUED", "RUNNING")


def dashboard_signature(db):
    # Cheap fingerprint of everything the dashboard displays. It only
    # changes when a worker or a task changes status, so a single
    # comparison tells us whether connected browsers need fresh data
    worker_states = sorted(
        (worker.worker_id, worker.status)
        for worker in db.query(Worker.worker_id, Worker.status).all()
    )

    # Per-status totals: this is what makes changes visible even when a
    # task runs entirely between two checks (e.g. a quick task going
    # QUEUED -> SUCCESS in a few ms, which is never seen as RUNNING)
    status_counts = sorted(
        (status, total)
        for status, total in db.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )

    active_tasks = sorted(
        (task.id, task.status)
        for task in db.query(Task.id, Task.status)
        .filter(Task.status.in_(ACTIVE_STATUSES))
        .all()
    )

    return (tuple(worker_states), tuple(status_counts), tuple(active_tasks))

def monitor_workers():
    last_signature = None

    while True:
        db = SessionLocal()

        # Every cycle is guarded: a transient database problem (Postgres
        # restarting, a pooled connection going stale) must never kill the
        # monitor, because a dead monitor silently stops sending updates
        # until someone restarts it by hand.
        try:
            workers = db.query(Worker).all()

            for worker in workers:
                if datetime.utcnow() - worker.last_heartbeat > timedelta(seconds=TIMEOUT):
                    if worker.status != "DEAD":
                        worker.status = "DEAD"
                        print(f"Worker {worker.worker_id} marked DEAD")

                        notify_frontend({
                            "type": "worker_update",
                            "worker_id": worker.worker_id,
                            "status": "DEAD",
                        })

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

                            notify_frontend({
                                "type": "task_update",
                                "task_id": task.id,
                                "status": task.status,
                                "worker_id": task.worker_id,
                            })

            db.commit()

            signature = dashboard_signature(db)

        except Exception as e:
            # Do not die: roll back the dirty cycle, drop the dead pooled
            # connection and try again on the next tick. Without this the
            # dashboard stops updating until the monitor is restarted.
            db.rollback()
            print(f"Monitor cycle failed (will retry): {e}")
            engine.dispose()

            # Treat the failed cycle as "no change" so clients aren't spammed
            signature = last_signature

        finally:
            db.close()

        # Whenever any worker or active task changed status, tell connected
        # browsers to reload so the dashboard stays live without a manual
        # refresh. Nothing is sent while the system is idle.
        if signature != last_signature:
            last_signature = signature
            notify_frontend({"type": "dashboard_update"})

        time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    monitor_workers()