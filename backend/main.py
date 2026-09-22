from fastapi import FastAPI, Depends,WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from websocket_manager import manager
from sqlalchemy.orm import Session


from database import engine, Base, get_db
from models import Task,Worker
from schemas import TaskCreate, TaskResponse
from redis_client import redis_client


app = FastAPI(
    title="TaskFlow API",
    version="1.0.0"
)


Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # List of allowed origins
    allow_credentials=True,           # Support cookies/auth headers
    allow_methods=["*"],              # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],              # Allow all headers
)



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_task_update(task):
    await manager.broadcast({
        "type": "task_update",
        "task_id": task.id,
        "status": task.status,
        "worker_id": task.worker_id
    })

@app.post("/internal/broadcast")
async def internal_broadcast(message: dict):
    # Used by the worker monitor to push worker-death / task-requeue
    # events to all connected WebSocket clients
    await manager.broadcast(message)
    return {"status": "broadcast"}

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
async def create_task(
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

    await broadcast_task_update(task)

    return task

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()


@app.get("/workers")
def get_workers(db: Session = Depends(get_db)):
    return db.query(Worker).all()


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()

    return {
        "queued": sum(t.status == "QUEUED" for t in tasks),
        "running": sum(t.status == "RUNNING" for t in tasks),
        "success": sum(t.status == "SUCCESS" for t in tasks),
        "failed": sum(t.status == "FAILED" for t in tasks),
    }