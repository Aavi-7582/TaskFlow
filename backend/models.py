from sqlalchemy import String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    task_type: Mapped[str] = mapped_column(
        String(50)
    )

    payload: Mapped[dict] = mapped_column(
        JSON
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="QUEUED"
    )

    result: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    worker_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

from datetime import datetime
from sqlalchemy import DateTime


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    worker_id: Mapped[str] = mapped_column(
        String(50),
        unique=True
    )

    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE"
    )