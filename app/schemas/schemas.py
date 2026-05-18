from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from app.models.models import UserRole, TaskPeriod, TaskPriority, TaskStatus


# ─── Department ───────────────────────────────────────────────
class DepartmentOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── User ─────────────────────────────────────────────────────
class UserShort(BaseModel):
    id: int
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: UserRole
    department: Optional[DepartmentOut] = None
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Task ─────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    department_id: Optional[int] = None
    period: TaskPeriod
    deadline: Optional[date] = None
    priority: TaskPriority = TaskPriority.medium
    status: TaskStatus = TaskStatus.new
    parent_task_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    department_id: Optional[int] = None
    period: Optional[TaskPeriod] = None
    deadline: Optional[date] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    parent_task_id: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    assignee: Optional[UserShort] = None
    department: Optional[DepartmentOut] = None
    period: TaskPeriod
    deadline: Optional[date] = None
    priority: TaskPriority
    status: TaskStatus
    parent_task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskWithChildren(TaskOut):
    children: List["TaskWithChildren"] = []

TaskWithChildren.model_rebuild()


# ─── Comment ──────────────────────────────────────────────────
class CommentCreate(BaseModel):
    body: str
    author_id: Optional[int] = None


class CommentOut(BaseModel):
    id: int
    body: str
    author: Optional[UserShort] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Dashboard ────────────────────────────────────────────────
class StatusCount(BaseModel):
    status: str
    count: int


class DepartmentStats(BaseModel):
    department: str
    total: int
    done: int
    overdue: int
    in_progress: int


class EmployeeLoad(BaseModel):
    user_id: int
    full_name: str
    department: Optional[str]
    active_tasks: int
    overdue_tasks: int


class DashboardOut(BaseModel):
    total_tasks: int
    by_status: List[StatusCount]
    by_department: List[DepartmentStats]
    overdue_count: int
    high_priority_count: int
    employee_load: List[EmployeeLoad]
