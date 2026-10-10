# TaskFlow

TaskFlow is a distributed task queue. You submit a job from a web dashboard, it is stored in PostgreSQL, queued in Redis, executed by one of several containerized workers, and its status is pushed to the browser in real time over WebSockets.

## Features

- **Redis task queue:** Submitted tasks are pushed to a Redis list (`task_queue`) and consumed with blocking pops (`BLPOP`).
- **Multiple workers:** Three Dockerized workers compete for queued tasks.
- **Persistent state:** PostgreSQL stores each task's type, payload, status, worker, retry count, and result.
- **Failure detection:** Workers send heartbeats. A worker whose heartbeat goes stale (about 2s) is marked `DEAD`.
- **Automatic retries:** Tasks left `RUNNING` by a dead worker are requeued, up to 3 retries, then marked `FAILED`.
- **Live dashboard:** A React UI shows stats, a task submission form, and Workers and Tasks tables, updated over WebSockets.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI, uvicorn |
| Queue | Redis 7 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 |
| Workers | Python 3.12 |
| Frontend | React 19, Vite, axios |
| Orchestration | Docker Compose |

## Architecture

TaskFlow separates task submission, job execution, and failure monitoring into independent components. Submitted tasks flow from the React dashboard to the FastAPI backend, which saves them in PostgreSQL and pushes their IDs to Redis. Workers pop IDs from Redis, execute them, and write results back to PostgreSQL. A separate monitor process watches worker heartbeats, requeues tasks from dead workers, and notifies the backend, which broadcasts updates to connected browsers over WebSockets.

### System Architecture

```mermaid
flowchart LR
    User([User]) --> UI[React Dashboard]
    UI -->|REST| API[FastAPI Backend]
    API -->|save task| PG[(PostgreSQL)]
    API -->|enqueue task id| RQ[[Redis task_queue]]
    RQ -->|BLPOP| W[Workers x3]
    W -->|claim, update result| PG
    W -->|heartbeat| PG
    MON[Monitor] -->|detect dead workers, requeue| PG
    MON -->|requeue| RQ
    MON -->|events| API
    API -.->|WebSocket updates| UI
```

### Task Execution and Recovery Flow

```mermaid
flowchart TD
    A[Submit task via POST /tasks] --> B[Save task as QUEUED in PostgreSQL]
    B --> C[Push task id to Redis task_queue]
    C --> D[Worker BLPOP pops task id]
    D --> E{Conditional claim QUEUED to RUNNING}
    E -- claimed --> F[Execute task]
    E -- not claimed --> D
    F --> G{Execution succeeded?}
    G -- yes --> H[Save SUCCESS and result]
    G -- no --> I[Save FAILED]
    K[Monitor scans worker heartbeats] --> L{Heartbeat older than 2s?}
    L -- yes --> M[Mark worker DEAD]
    M --> N{Task still RUNNING on dead worker?}
    N -- yes --> O{Retries left?}
    O -- yes --> P[Increment retry, set QUEUED, push to Redis]
    P -->|requeued task id| D
    O -- no --> Q[Mark task FAILED]
```

## Project Structure

```text
TaskFlow/
├── docker-compose.yml
├── backend/      # FastAPI app: routes, WebSocket, models, config
├── worker/       # worker.py, executor.py, monitor.py, Dockerfile
└── frontend/     # React dashboard (src/App.jsx, src/api.js)
```

## Getting Started

**Prerequisites:** Docker, Python 3.12+, Node.js 18+

**1. Clone the repository**

```bash
git clone https://github.com/Aavi-7582/TaskFlow.git
cd TaskFlow
```

**2. Start PostgreSQL and Redis, then build and start the workers**

```bash
docker compose up -d postgres redis
docker compose build worker1 worker2 worker3
docker compose up -d worker1 worker2 worker3
```

**3. Start the backend** (in a new terminal)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**4. Start the monitor** (in a new terminal, not part of Docker Compose)

```bash
cd worker
source ../backend/venv/bin/activate        # Windows: ..\backend\venv\Scripts\activate
python monitor.py
```

**5. Start the frontend** (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 for the dashboard. The API docs are at http://127.0.0.1:8000/docs.

## Configuration

Set these as environment variables. The defaults work for the local setup.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://taskflow:taskflow@127.0.0.1:5432/taskflow` | PostgreSQL connection |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis connection |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Where the monitor sends broadcast events |
| `HEARTBEAT_INTERVAL` | `1` | Seconds between worker heartbeats |
| `WORKER_TIMEOUT` | `2` | Heartbeat age (seconds) before a worker is `DEAD` |
| `MONITOR_INTERVAL` | `0.5` | Seconds between monitor scans |

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/tasks` | Submit a task |
| `GET` | `/tasks` | List tasks, newest first |
| `GET` | `/workers` | List workers |
| `GET` | `/stats` | Count of tasks by status |
| `WS` | `/ws` | Live event stream |

**Supported task types**

- `fibonacci`: payload `{"n": 30}`, returns the n-th Fibonacci number
- `sleep`: payload `{"seconds": 10}`, waits, then returns a message

**Example**

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type": "fibonacci", "payload": {"n": 30}}'
```
