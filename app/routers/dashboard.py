from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import Task, User, Department, TaskStatus, TaskPriority
from app.schemas.schemas import DashboardOut, StatusCount, DepartmentStats, EmployeeLoad

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_model=DashboardOut)
async def get_dashboard(db: AsyncSession = Depends(get_db)):

    # 1. Общее кол-во задач
    total = await db.scalar(select(func.count()).select_from(Task))

    # 2. По статусам
    status_rows = await db.execute(
        select(Task.status, func.count().label("cnt"))
        .group_by(Task.status)
    )
    by_status = [
        StatusCount(status=r.status.value, count=r.cnt)
        for r in status_rows
    ]

    # 3. Просроченные и высокий приоритет
    overdue_count = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.overdue)
    )
    high_priority_count = await db.scalar(
        select(func.count()).select_from(Task).where(Task.priority == TaskPriority.high)
    )

    # 4. Статистика по отделам
    dept_rows = await db.execute(
        select(
            Department.name,
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == TaskStatus.done, 1), else_=0)).label("done"),
            func.sum(case((Task.status == TaskStatus.overdue, 1), else_=0)).label("overdue"),
            func.sum(case((Task.status == TaskStatus.in_progress, 1), else_=0)).label("in_progress"),
        )
        .join(Task, Task.department_id == Department.id, isouter=True)
        .group_by(Department.name)
        .order_by(func.count(Task.id).desc())
    )
    by_department = [
        DepartmentStats(
            department=r.name,
            total=r.total or 0,
            done=r.done or 0,
            overdue=r.overdue or 0,
            in_progress=r.in_progress or 0,
        )
        for r in dept_rows
    ]

    # 5. Загрузка сотрудников
    load_rows = await db.execute(
        select(
            User.id,
            User.full_name,
            Department.name.label("dept_name"),
            func.count(Task.id).label("active_tasks"),
            func.sum(case((Task.status == TaskStatus.overdue, 1), else_=0)).label("overdue_tasks"),
        )
        .join(Task, Task.assignee_id == User.id, isouter=True)
        .join(Department, User.department_id == Department.id, isouter=True)
        .where(Task.status.notin_([TaskStatus.done]))
        .group_by(User.id, User.full_name, Department.name)
        .order_by(func.count(Task.id).desc())
    )
    employee_load = [
        EmployeeLoad(
            user_id=r.id,
            full_name=r.full_name,
            department=r.dept_name,
            active_tasks=r.active_tasks or 0,
            overdue_tasks=r.overdue_tasks or 0,
        )
        for r in load_rows
    ]

    return DashboardOut(
        total_tasks=total or 0,
        by_status=by_status,
        by_department=by_department,
        overdue_count=overdue_count or 0,
        high_priority_count=high_priority_count or 0,
        employee_load=employee_load,
    )
