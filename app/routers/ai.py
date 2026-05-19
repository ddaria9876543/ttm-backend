from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Task, User, TaskStatus
from app.database import get_db

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/insights")
def get_ai_insights(role: str = "manager", db: Session = Depends(get_db)):
    # 1. Сводка (общее количество, просроченные, в работе, на неделю)
    total_tasks = db.query(Task).count()
    overdue_count = db.query(Task).filter(Task.status == "overdue").count()
    in_progress_count = db.query(Task).filter(Task.status == "in_progress").count()
    week_tasks = db.query(Task).filter(Task.period == "week").count()

    summary = (
        f"Всего задач: {total_tasks}. Просрочено: {overdue_count}, "
        f"в работе: {in_progress_count}. На неделю запланировано: {week_tasks}."
    )

    # 2. Риски просрочки (дедлайн <=2 дня и статус не done)
    soon = datetime.now() + timedelta(days=2)
    risky_tasks = db.query(Task).filter(
        Task.deadline <= soon,
        Task.status != "done"
    ).all()
    risk_text = []
    for t in risky_tasks:
        risk_text.append(f"«{t.title}» (дедлайн {t.deadline.date()}) – не выполнена.")

    # 3. Перегрузка сотрудников (активные задачи, статус не done)
    users = db.query(User).all()
    overload = []
    for user in users:
        active_count = db.query(Task).filter(
            Task.assignee_id == user.id,
            Task.status != "done"
        ).count()
        if active_count > 5:  # порог можно настроить
            overload.append(f"{user.full_name} — {active_count} активных задач (выше нормы).")

    # 4. Советы руководителю
    high_priority_not_started = db.query(Task).filter(
        Task.priority == "high",
        Task.status == "new"
    ).all()
    advice = []
    if risky_tasks:
        advice.append(f"Срочно проверьте задачи: {', '.join([t.title for t in risky_tasks[:3]])}.")
    if overload:
        advice.append(f"Перегрузка сотрудников: {' '.join(overload[:2])}")
    if high_priority_not_started:
        advice.append(
            f"Высокоприоритетные задачи не начаты: {', '.join([t.title for t in high_priority_not_started[:2]])}."
        )

    # Если роль не manager — не показываем советы
    result = {
        "summary": summary,
        "risks": risk_text,
        "overload": overload,
        "advice_for_manager": advice if role == "manager" else []
    }
    return result
