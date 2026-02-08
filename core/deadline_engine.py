"""
Deadline Engine - Critical path, at-risk tasks, and deadline change logic.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.models import Task, ScheduledTask, Resource


def get_tasks_at_risk(
    tasks: List[Task],
    schedule: List[ScheduledTask],
    deadline: str,
) -> List[Task]:
    """Tasks that end after the deadline (critical path at risk)."""
    if not deadline or not schedule:
        return []
    try:
        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
    except ValueError:
        return []
    end_by_task = {s.task_id: s.end_datetime for s in schedule}
    at_risk = []
    for t in tasks:
        end_str = end_by_task.get(t.id)
        if not end_str:
            continue
        try:
            end_dt = datetime.strptime(end_str[:16], "%Y-%m-%d %H:%M")
            if end_dt > deadline_dt:
                at_risk.append(t)
        except ValueError:
            continue
    return at_risk


def suggest_priority_compression(
    at_risk_tasks: List[Task],
    resources: List[Resource],
    schedule: List[ScheduledTask],
) -> List[Dict[str, Any]]:
    """Suggest re-assigning low-priority at-risk tasks to other resources."""
    suggestions = []
    assigned = {t.id: t.assigned_to for t in at_risk_tasks if t.assigned_to}
    resource_ids = [r.id for r in resources]
    for t in at_risk_tasks:
        if t.priority > 2 and t.assigned_to:  # Low priority and assigned
            others = [r for r in resource_ids if r != t.assigned_to]
            if others:
                suggestions.append({
                    "task_id": t.id,
                    "task_name": t.name,
                    "current_resource": t.assigned_to,
                    "suggestion": "Re-assign to another resource to compress timeline",
                    "alternative_resources": others[:3],
                })
    return suggestions


def get_critical_path_tasks(tasks: List[Task], schedule: List[ScheduledTask]) -> List[Task]:
    """Tasks on the critical path (latest end times, no slack)."""
    if not tasks or not schedule:
        return []
    end_by_id = {s.task_id: s.end_datetime for s in schedule}
    sorted_tasks = sorted(
        [t for t in tasks if t.id in end_by_id],
        key=lambda t: end_by_id[t.id],
        reverse=True,
    )
    if not sorted_tasks:
        return []
    max_end = end_by_id[sorted_tasks[0].id]
    return [t for t in sorted_tasks if end_by_id[t.id] == max_end]
