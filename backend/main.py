from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import Task
from schemas import TaskCreate, TaskResponse
from redis_client import redis_client


app = FastAPI(
    title="TaskFlow API",
    version="1.0.0"
)


Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "message": "TaskFlow API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/tasks", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):

    # 1. Create task in PostgreSQL
    task = Task(
        task_type=task_data.task_type,
        payload=task_data.payload,
        status="QUEUED"
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # 2. Push task ID into Redis queue
    redis_client.rpush(
        "task_queue",
        task.id
    )

    return task