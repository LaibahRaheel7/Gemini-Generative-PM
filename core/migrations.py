"""
Migration utilities to convert legacy ProjectState to MultiProjectState.
"""
import json
from typing import Dict, Any
from datetime import datetime
from core.models import (
    ProjectState, MultiProjectState, Project, Task, Resource,
    WorkWeekConfig, HolidayPreset, ScheduledTask
)


def generate_color_palette(index: int) -> str:
    """Generate distinct colors for projects."""
    colors = [
        "#3498db",  # Blue
        "#2ecc71",  # Green
        "#e74c3c",  # Red
        "#f39c12",  # Orange
        "#9b59b6",  # Purple
        "#1abc9c",  # Turquoise
        "#e67e22",  # Carrot
        "#34495e",  # Dark blue-gray
    ]
    return colors[index % len(colors)]


def migrate_project_state_to_multi(old_state: ProjectState) -> MultiProjectState:
    """
    Convert legacy ProjectState to new MultiProjectState format.
    
    Creates a single project from the legacy state with default settings.
    """
    # Create default project from legacy state
    project = Project(
        id="P1",
        name="Legacy Project",
        description="Migrated from single-project format",
        color_hex=generate_color_palette(0),
        start_date=old_state.project_start_date,
        end_date=None,
        work_week_config=WorkWeekConfig(working_days=[0, 1, 2, 3, 4]),  # Mon-Fri
        holiday_preset=HolidayPreset(
            country_code="US",
            year=datetime.now().year,
            holiday_dates=[]
        ),
        total_estimated_hours=sum(task.duration_hours for task in old_state.tasks),
        total_actual_hours=0,
        buffer_hours=0
    )
    
    # Update tasks with project_id and default complexity
    migrated_tasks = []
    for task in old_state.tasks:
        task_dict = task.model_dump()
        task_dict["project_id"] = "P1"
        if "complexity" not in task_dict:
            task_dict["complexity"] = "medium"
        migrated_tasks.append(Task(**task_dict))
    
    # Update resources with default email and color
    migrated_resources = []
    for i, resource in enumerate(old_state.resources):
        resource_dict = resource.model_dump()
        if "email" not in resource_dict:
            resource_dict["email"] = f"{resource.id.lower()}@company.com"
        if "color_hex" not in resource_dict:
            resource_dict["color_hex"] = generate_color_palette(i + 1)
        migrated_resources.append(Resource(**resource_dict))
    
    # Update scheduled tasks with project_id
    migrated_schedule = []
    for scheduled_task in old_state.schedule:
        task_dict = scheduled_task.model_dump()
        task_dict["project_id"] = "P1"
        migrated_schedule.append(ScheduledTask(**task_dict))
    
    # Create new multi-project state
    return MultiProjectState(
        projects=[project],
        tasks=migrated_tasks,
        resources=migrated_resources,
        schedule=migrated_schedule,
        leaves=[]
    )


def migrate_state_file(input_path: str, output_path: str) -> None:
    """
    Migrate a state.json file from old to new format.
    
    Args:
        input_path: Path to old state.json
        output_path: Path to save new state.json
    """
    with open(input_path, 'r') as f:
        old_data = json.load(f)
    
    # Try to determine if it's already the new format
    if "projects" in old_data:
        print("File is already in MultiProjectState format. No migration needed.")
        return
    
    # Parse old state
    old_state = ProjectState(**old_data)
    
    # Migrate to new format
    new_state = migrate_project_state_to_multi(old_state)
    
    # Save to new file
    with open(output_path, 'w') as f:
        json.dump(new_state.model_dump(), f, indent=2)
    
    print(f"Successfully migrated state from {input_path} to {output_path}")
    print(f"Created 1 project with {len(new_state.resources)} resources and {len(old_state.tasks)} tasks")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m core.migrations <input_state.json> [output_state.json]")
        print("Example: python -m core.migrations state.json state_new.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "state_migrated.json"
    
    migrate_state_file(input_file, output_file)
