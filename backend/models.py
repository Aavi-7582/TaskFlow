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