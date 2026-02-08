from typing import List, Optional, Literal
from datetime import date
from pydantic import BaseModel, Field

class WorkWeekConfig(BaseModel):
    """Configuration for working days of the week."""
    working_days: List[int] = Field(
        default=[0, 1, 2, 3, 4],
        description="List of working days where 0=Monday, 6=Sunday"
    )

class HolidayPreset(BaseModel):
    """Holiday configuration for a specific country and year."""
    country_code: str = Field(..., description="ISO country code (e.g., 'US', 'GB', 'AE')")
    year: int
    holiday_dates: List[str] = Field(default_factory=list, description="List of holiday dates in ISO format")

class Project(BaseModel):
    """Represents a project with its configuration and metadata."""
    id: str
    name: str
    description: str
    color_hex: str = Field(..., description="Hex color code for UI display (e.g., '#3498db')")
    start_date: str = Field(..., description="ISO format YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD")
    work_week_config: WorkWeekConfig = Field(default_factory=WorkWeekConfig)
    holiday_preset: HolidayPreset
    total_estimated_hours: int = Field(0, description="Sum of all task durations")
    total_actual_hours: int = Field(0, description="Actual hours spent")
    buffer_hours: int = Field(0, description="Available buffer from low-complexity tasks")

class Resource(BaseModel):
    """Represents a team member who can execute tasks."""
    id: str
    name: str
    role: str
    email: str = Field("", description="Email address for notifications")
    color_hex: str = Field("#666666", description="Hex color code for UI display")

class Task(BaseModel):
    """Represents a project task with dependencies."""
    id: str
    name: str
    duration_hours: int = Field(..., description="Estimated effort in hours")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must finish before this starts")
    assigned_to: Optional[str] = Field(None, description="Resource ID of the person executing the task")
    priority: int = Field(1, description="1=High, 2=Medium, 3=Low")
    project_id: str = Field("", description="ID of the project this task belongs to")
    complexity: Literal["low", "medium", "high"] = Field("medium", description="Task complexity for buffer management")
    required_skillset: Optional[str] = Field(None, description="Required skillset from brief (e.g. 'Backend', 'DevOps')")
    status_note: Optional[str] = Field(None, description="User suggestion/status (e.g. 'Dependency on client')")
    health: Literal["on_track", "at_risk", "blocked"] = Field("on_track", description="Visual indicator for timeline")

class ScheduledTask(BaseModel):
    """Represents a task with computed start and end times."""
    task_id: str
    task_name: str
    resource_id: str
    resource_name: str
    start_datetime: str
    end_datetime: str
    project_id: str = Field("", description="ID of the project this task belongs to")

class Leave(BaseModel):
    """Represents a leave period for a resource."""
    id: str
    resource_id: str
    start_date: str = Field(..., description="ISO format YYYY-MM-DD")
    end_date: str = Field(..., description="ISO format YYYY-MM-DD")
    leave_type: str = Field("vacation", description="Type of leave (vacation, sick, personal, etc.)")


class ReducedCapacity(BaseModel):
    """Intermittent constraint: reduced available hours on a date (e.g. demos)."""
    id: str
    date: str = Field(..., description="ISO format YYYY-MM-DD")
    resource_id: Optional[str] = Field(None, description="If set, only this resource; else applies to all")
    available_hours: int = Field(2, description="Hours available on this date (e.g. 2 for demo day)")
    reason: str = Field("reduced_capacity", description="e.g. 'Scheduled Demo'")

class ProjectState(BaseModel):
    """The complete state of a single project (legacy, kept for backward compatibility)."""
    tasks: List[Task]
    resources: List[Resource]
    project_start_date: str  # ISO Format YYYY-MM-DD
    schedule: List[ScheduledTask] = Field(default_factory=list)

class MultiProjectState(BaseModel):
    """The complete state of the multi-project system."""
    projects: List[Project] = Field(default_factory=list)
    tasks: List[Task] = Field(default_factory=list, description="All tasks across projects (use project_id to scope)")
    resources: List[Resource] = Field(default_factory=list)
    schedule: List[ScheduledTask] = Field(default_factory=list)
    leaves: List[Leave] = Field(default_factory=list)
    reduced_capacities: List[ReducedCapacity] = Field(default_factory=list, description="Demos / reduced hours per date")
