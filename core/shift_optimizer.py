"""
Shift Optimizer - Handles dynamic task shifting when resources are on leave.
Implements resource leveling and buffer compression strategies.
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, date
from core.models import ScheduledTask, Leave, Project, Task
from core.leave_manager import LeaveManager
from core.holiday_manager import get_holiday_manager


class ShiftOptimizer:
    """
    Optimizes task schedules by handling leave conflicts and managing project buffers.
    """
    
    def __init__(
        self,
        leave_manager: LeaveManager,
        projects: List[Project],
        tasks: List[Task]
    ):
        """
        Initialize the shift optimizer.
        
        Args:
            leave_manager: Manager for resource leave data
            projects: List of projects with buffer configuration
            tasks: Original task list for reference
        """
        self.leave_manager = leave_manager
        self.projects = projects
        self.tasks = tasks
        self.holiday_manager = get_holiday_manager()
        
        # Create lookup maps
        self.project_map = {p.id: p for p in projects}
        self.task_map = {t.id: t for t in tasks}
    
    def apply_leave_shifts(self, schedule: List[ScheduledTask]) -> List[ScheduledTask]:
        """
        Apply leave-based task shifting to the schedule.
        
        When a resource is on leave during their scheduled task:
        1. Try to compress low-complexity tasks to create buffer
        2. If buffer insufficient, shift the task to next available date
        3. Cascade shifts to dependent tasks
        
        Args:
            schedule: Original schedule from OR-Tools solver
            
        Returns:
            Optimized schedule with leave conflicts resolved
        """
        # Create a working copy of the schedule
        working_schedule = [
            ScheduledTask(**task.model_dump()) for task in schedule
        ]
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(working_schedule)
        
        # Track which tasks have been shifted
        shifted_tasks = set()
        
        # Iterate through tasks in chronological order
        working_schedule.sort(key=lambda x: x.start_datetime)
        
        for i, scheduled_task in enumerate(working_schedule):
            # Check if resource is available for this task
            task_start = datetime.fromisoformat(scheduled_task.start_datetime)
            task_end = datetime.fromisoformat(scheduled_task.end_datetime)
            
            conflict_days = self._get_leave_conflict_days(
                scheduled_task.resource_id,
                task_start.date(),
                task_end.date()
            )
            
            if conflict_days:
                # Resource is on leave during this task
                print(f"Leave conflict detected for task {scheduled_task.task_id}: {len(conflict_days)} days")
                
                # Try to compress buffer first
                if self._can_compress_buffer(scheduled_task.project_id, len(conflict_days)):
                    print(f"Compressing buffer for project {scheduled_task.project_id}")
                    self._compress_low_complexity_tasks(
                        working_schedule,
                        scheduled_task.project_id,
                        len(conflict_days)
                    )
                else:
                    # Need to shift the task
                    print(f"Shifting task {scheduled_task.task_id}")
                    next_available = self._find_next_available_day(
                        scheduled_task.resource_id,
                        task_end.date(),
                        scheduled_task.project_id
                    )
                    
                    # Calculate new start/end based on duration
                    duration_hours = (task_end - task_start).total_seconds() / 3600
                    new_start = datetime.combine(next_available, task_start.time())
                    new_end = new_start + timedelta(hours=duration_hours)
                    
                    # Update the task
                    scheduled_task.start_datetime = new_start.strftime("%Y-%m-%d %H:%M")
                    scheduled_task.end_datetime = new_end.strftime("%Y-%m-%d %H:%M")
                    shifted_tasks.add(scheduled_task.task_id)
                    
                    # Cascade shifts to dependent tasks
                    self._cascade_shifts(
                        working_schedule,
                        scheduled_task,
                        dependency_graph,
                        shifted_tasks
                    )
        
        return working_schedule
    
    def _get_leave_conflict_days(
        self,
        resource_id: str,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        Get list of days when resource is on leave within a date range.
        
        Args:
            resource_id: ID of the resource
            start_date: Start of the range
            end_date: End of the range
            
        Returns:
            List of dates when resource is on leave
        """
        conflict_days = []
        current = start_date
        
        while current <= end_date:
            if not self.leave_manager.is_resource_available(resource_id, current):
                conflict_days.append(current)
            current += timedelta(days=1)
        
        return conflict_days
    
    def _find_next_available_day(
        self,
        resource_id: str,
        after_date: date,
        project_id: str
    ) -> date:
        """
        Find the next working day when resource is available.
        
        Args:
            resource_id: ID of the resource
            after_date: Start searching after this date
            project_id: Project ID for work week config
            
        Returns:
            Next available date
        """
        project = self.project_map.get(project_id)
        working_days = [0, 1, 2, 3, 4]  # Default Mon-Fri
        
        if project and project.work_week_config:
            working_days = project.work_week_config.working_days
        
        current = after_date + timedelta(days=1)
        max_search = 365  # Safety limit
        
        for _ in range(max_search):
            # Check if it's a working day
            if current.weekday() in working_days:
                # Check if it's not a holiday
                is_holiday = False
                if project and project.holiday_preset:
                    is_holiday = self.holiday_manager.is_holiday(current, project.holiday_preset)
                
                if not is_holiday:
                    # Check if resource is available
                    if self.leave_manager.is_resource_available(resource_id, current):
                        return current
            
            current += timedelta(days=1)
        
        # Fallback: return a date far in the future
        return after_date + timedelta(days=max_search)
    
    def _can_compress_buffer(self, project_id: str, hours_needed: int) -> bool:
        """
        Check if project has enough buffer to compress.
        
        Args:
            project_id: ID of the project
            hours_needed: Hours needed to absorb the shift
            
        Returns:
            True if compression is possible
        """
        project = self.project_map.get(project_id)
        if not project:
            return False
        
        return project.buffer_hours >= hours_needed
    
    def _compress_low_complexity_tasks(
        self,
        schedule: List[ScheduledTask],
        project_id: str,
        hours_to_save: int
    ):
        """
        Compress low-complexity tasks to create buffer.
        
        Reduces duration of low-complexity tasks by up to 20%.
        
        Args:
            schedule: Working schedule to modify
            project_id: Project to compress tasks for
            hours_to_save: Target hours to save
        """
        hours_saved = 0
        
        for scheduled_task in schedule:
            if scheduled_task.project_id != project_id:
                continue
            
            # Get original task for complexity info
            task = self.task_map.get(scheduled_task.task_id)
            if not task or task.complexity != "low":
                continue
            
            # Calculate potential savings (max 20% reduction)
            start = datetime.fromisoformat(scheduled_task.start_datetime)
            end = datetime.fromisoformat(scheduled_task.end_datetime)
            duration_hours = (end - start).total_seconds() / 3600
            
            max_reduction = duration_hours * 0.2  # 20% max
            reduction = min(max_reduction, hours_to_save - hours_saved)
            
            if reduction > 0:
                # Apply the compression
                new_end = end - timedelta(hours=reduction)
                scheduled_task.end_datetime = new_end.strftime("%Y-%m-%d %H:%M")
                hours_saved += reduction
                
                if hours_saved >= hours_to_save:
                    break
    
    def _build_dependency_graph(
        self,
        schedule: List[ScheduledTask]
    ) -> Dict[str, List[str]]:
        """
        Build a dependency graph from scheduled tasks.
        
        Args:
            schedule: List of scheduled tasks
            
        Returns:
            Dictionary mapping task_id to list of dependent task_ids
        """
        graph = {task.task_id: [] for task in schedule}
        
        for task in self.tasks:
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[dep_id].append(task.id)
        
        return graph
    
    def _cascade_shifts(
        self,
        schedule: List[ScheduledTask],
        shifted_task: ScheduledTask,
        dependency_graph: Dict[str, List[str]],
        shifted_tasks: set
    ):
        """
        Cascade task shifts to dependent tasks.
        
        When a task is shifted, all tasks depending on it must also be shifted
        if they now start before the shifted task ends.
        
        Args:
            schedule: Working schedule
            shifted_task: Task that was just shifted
            dependency_graph: Dependency relationships
            shifted_tasks: Set of already shifted task IDs
        """
        shifted_end = datetime.fromisoformat(shifted_task.end_datetime)
        dependent_ids = dependency_graph.get(shifted_task.task_id, [])
        
        for dep_id in dependent_ids:
            # Find the dependent task in schedule
            for scheduled_task in schedule:
                if scheduled_task.task_id == dep_id:
                    task_start = datetime.fromisoformat(scheduled_task.start_datetime)
                    task_end = datetime.fromisoformat(scheduled_task.end_datetime)
                    
                    # Check if dependent task needs to be shifted
                    if task_start < shifted_end:
                        duration = task_end - task_start
                        new_start = shifted_end
                        new_end = new_start + duration
                        
                        scheduled_task.start_datetime = new_start.strftime("%Y-%m-%d %H:%M")
                        scheduled_task.end_datetime = new_end.strftime("%Y-%m-%d %H:%M")
                        shifted_tasks.add(dep_id)
                        
                        # Recursively cascade to further dependents
                        self._cascade_shifts(
                            schedule,
                            scheduled_task,
                            dependency_graph,
                            shifted_tasks
                        )
                    break
    
    def calculate_project_buffer(self, project_id: str) -> int:
        """
        Calculate available buffer hours for a project based on low-complexity tasks.
        
        Args:
            project_id: Project ID
            
        Returns:
            Available buffer hours (20% of low-complexity task durations)
        """
        buffer_hours = 0
        
        for task in self.tasks:
            if task.project_id == project_id and task.complexity == "low":
                buffer_hours += task.duration_hours * 0.2
        
        return int(buffer_hours)
    
    def validate_deadline_constraint(
        self,
        schedule: List[ScheduledTask],
        project_id: str,
        original_end: datetime,
        max_overrun_percent: float = 0.10
    ) -> bool:
        """
        Validate that project doesn't exceed deadline by more than allowed percentage.
        
        Args:
            schedule: Current schedule
            project_id: Project to check
            original_end: Original projected end date
            max_overrun_percent: Maximum allowed overrun (default 10%)
            
        Returns:
            True if deadline constraint is satisfied
        """
        # Find latest task end for this project
        project_tasks = [t for t in schedule if t.project_id == project_id]
        if not project_tasks:
            return True
        
        latest_end = max(
            datetime.fromisoformat(t.end_datetime) for t in project_tasks
        )
        
        # Calculate allowed overrun
        original_duration = (original_end - datetime.now()).total_seconds()
        max_overrun = original_duration * max_overrun_percent
        
        actual_overrun = (latest_end - original_end).total_seconds()
        
        return actual_overrun <= max_overrun
