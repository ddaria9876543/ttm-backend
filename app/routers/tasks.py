from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import Task, TaskHistory, TaskPeriod, TaskPriority, TaskStatus
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut, TaskWithChildren, CommentCreate, CommentOut

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _task_options():
    """Загружаем связанные объекты одним запросом (без N+1)."""
    return [
        selectinload(Task.assignee),
        selectinload(Task.department),
        selectinload(Task.children),
    ]


@router.get("/", response_model=List[TaskOut])
async def list_tasks(
    department_id: Optional[int] = Query(None, description="Фильтр по отделу"),
    assignee_id:   Optional[int] = Query(None, description="Фильтр по ответственному"),
    status:        Optional[TaskStatus]   = Query(None, description="Фильтр по статусу"),
    period:        Optional[TaskPeriod]   = Query(None, description="Фильтр по периоду"),
    priority:      Optional[TaskPriority] = Query(None, description="Фильтр по приоритету"),
    deadline_from: Optional[date] = Query(None, description="Дедлайн от"),
    deadline_to:   Optional[date] = Query(None, description="Дедлайн до"),
    search:        Optional[str]  = Query(None, description="Поиск по названию"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if department_id: filters.append(Task.department_id == department_id)
    if assignee_id:   filters.append(Task.assignee_id == assignee_id)
    if status:        filters.append(Task.status == status)
    if period:        filters.append(Task.period == period)
    if priority:      filters.append(Task.priority == priority)
    if deadline_from: filters.append(Task.deadline >= deadline_from)
    if deadline_to:   filters.append(Task.deadline <= deadline_to)
    if search:        filters.append(Task.title.ilike(f"%{search}%"))

    stmt = (
        select(Task)
        .options(*_task_options())
        .where(and_(*filters))
        .offset(skip)
        .limit(limit)
        .order_by(Task.deadline.asc().nulls_last(), Task.priority.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskWithChildren)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).options(*_task_options()).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    # Перезагружаем со связями
    stmt = select(Task).options(*_task_options()).where(Task.id == task.id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).options(*_task_options()).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    changes = payload.model_dump(exclude_unset=True)
    for field, new_val in changes.items():
        old_val = getattr(task, field)
        if old_val != new_val:
            # Пишем историю изменений
            db.add(TaskHistory(
                task_id=task_id,
                field_name=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
            ))
        setattr(task, field, new_val)

    await db.commit()
    await db.refresh(task)
    stmt = select(Task).options(*_task_options()).where(Task.id == task_id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    await db.delete(task)
    await db.commit()


# ─── Иерархия задач ───────────────────────────────────────────
@router.get("/{task_id}/tree", response_model=TaskWithChildren)
async def get_task_tree(task_id: int, db: AsyncSession = Depends(get_db)):
    """Возвращает задачу со всей цепочкой дочерних: год→квартал→месяц→неделя."""

    # Загружаем все задачи дерева рекурсивно
    async def load_with_children(tid: int) -> Task:
        stmt = (
            select(Task)
            .options(
                selectinload(Task.assignee),
                selectinload(Task.department),
            )
            .where(Task.id == tid)
        )
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        if not task:
            return None

        # Загружаем прямых детей
        children_stmt = select(Task).where(Task.parent_task_id == tid)
        children_result = await db.execute(children_stmt)
        children = children_result.scalars().all()

        # Рекурсивно загружаем детей каждого ребёнка
        task.children = []
        for child in children:
            loaded_child = await load_with_children(child.id)
            if loaded_child:
                task.children.append(loaded_child)

        return task

    task = await load_with_children(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


# ─── Автопометка просроченных ─────────────────────────────────
@router.post("/mark-overdue", tags=["Tasks"])
async def mark_overdue(db: AsyncSession = Depends(get_db)):
    """Помечает как overdue все задачи у которых прошёл дедлайн.
    Вызывай периодически (например раз в час) или перед загрузкой дашборда."""
    today = date.today()

    # Находим задачи которые нужно пометить
    stmt = select(Task).where(
        and_(
            Task.deadline < today,
            Task.status.notin_([TaskStatus.done, TaskStatus.overdue])
        )
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    count = 0
    for task in tasks:
        db.add(TaskHistory(
            task_id=task.id,
            field_name="status",
            old_value=task.status.value,
            new_value=TaskStatus.overdue.value,
        ))
        task.status = TaskStatus.overdue
        count += 1

    await db.commit()
    return {"marked_overdue": count, "updated_at": datetime.utcnow()}


# ─── Комментарии ──────────────────────────────────────────────
@router.get("/{task_id}/comments", response_model=List[CommentOut])
async def get_comments(task_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload
    from app.models.models import Comment
    stmt = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{task_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(task_id: int, payload: CommentCreate, db: AsyncSession = Depends(get_db)):
    from app.models.models import Comment
    comment = Comment(task_id=task_id, **payload.model_dump())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment
