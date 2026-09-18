from pydantic import BaseModel


class TaskCreate(BaseModel):
    task_type: str
    payload: dict


class TaskResponse(BaseModel):
    id: int
    task_type: str
    payload: dict
    status: str

    class Config:
        from_attributes = True