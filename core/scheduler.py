import networkx as nx
from ortools.sat.python import cp_model
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any
from core.models import Task, Resource, ScheduledTask, Project
from core.holiday_manager import get_holiday_manager

class SchedulerEngine:
    """
    The mathematical brain of the project manager.
    Uses Google OR-Tools to optimally schedule tasks while respecting:
    - Dependencies (Task B can't start until Task A finishes)
    - Resource constraints (No person does two things at once)
    - Business hours (9 AM - 5 PM, Monday-Friday)
    """
    
    def __init__(
        self,
        tasks: List[Task],
        resources: List[Resource],
        start_date_str: str,
        projects: Optional[List[Project]] = None,
        reduced_capacities: Optional[List[Any]] = None,
    ):
        self.tasks = tasks
        self.resources = resources
        self.start_datetime = datetime.strptime(start_date_str, "%Y-%m-%d").replace(hour=9, minute=0, second=0)
        self.projects = projects or []
        self.holiday_manager = get_holiday_manager()
        self.reduced_capacities = reduced_capacities or []
        self.project_map = {p.id: p for p in self.projects}
        self.work_start_hour = 9
        self.work_end_hour = 17
        self.daily_hours = self.work_end_hour - self.work_start_hour

    def _validate_dag(self):
        """Uses NetworkX to ensure no circular dependencies exist."""
        G = nx.DiGraph()
        for t in self.tasks:
            G.add_node(t.id)
            for dep in t.dependencies:
                G.add_edge(dep, t.id)
        
        if not nx.is_directed_acyclic_graph(G):
            try:
                cycle = nx.find_cycle(G)
                raise ValueError(f"Circular dependency detected: {cycle}")
            except:
                raise ValueError("Project logic contains a cycle (Task A waits for B, B waits for A).")
        return True

    def solve(self) -> List[ScheduledTask]:
        """
        Main solver method. Returns a list of scheduled tasks with real datetime values.
        """
        # 1. Validation
        if not self.tasks:
            return []
            
        self._validate_dag()
        
        # 2. Setup OR-Tools Model
        model = cp_model.CpModel()
        
        # Horizon: Theoretical max time (sum of all durations)
        horizon = sum(t.duration_hours for t in self.tasks) + 100
        
        # Variables
        task_starts = {}
        task_ends = {}
        task_intervals = {}
        
        # Map tasks and resources by ID for easy lookup
        task_map = {t.id: t for t in self.tasks}
        resource_map = {r.id: r for r in self.resources}
        
        # Group tasks by assignee for resource constraints
        resource_tasks = {r.id: [] for r in self.resources}

        for t in self.tasks:
            # Create integer variables for Start and End (in Business Hours)
            start_var = model.NewIntVar(0, horizon, f'start_{t.id}')
            end_var = model.NewIntVar(0, horizon, f'end_{t.id}')
            
            # Create Interval Variable (Start, Duration, End)
            # This links start + duration = end
            interval_var = model.NewIntervalVar(start_var, t.duration_hours, end_var, f'interval_{t.id}')
            
            task_starts[t.id] = start_var
            task_ends[t.id] = end_var
            task_intervals[t.id] = interval_var
            
            if t.assigned_to and t.assigned_to in resource_tasks:
                resource_tasks[t.assigned_to].append(interval_var)

        # 3. Add Constraints
        
        # Dependency Constraints (Precedence)
        for t in self.tasks:
            for dep_id in t.dependencies:
                if dep_id in task_ends:
                    # Start of T >= End of Dep
                    model.Add(task_starts[t.id] >= task_ends[dep_id])

        # Resource Constraints (No Overlap)
        for r_id, intervals in resource_tasks.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # 4. Objective: Minimize Project MakeSpan (Finish date of last task)
        makespan = model.NewIntVar(0, horizon, 'makespan')
        model.AddMaxEquality(makespan, [task_ends[t.id] for t in self.tasks])
        model.Minimize(makespan)

        # 5. Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # Timeout after 30 seconds
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            schedule_results = []
            
            for t in self.tasks:
                # Get solver integer output (Business Hours offset)
                start_offset = solver.Value(task_starts[t.id])
                end_offset = solver.Value(task_ends[t.id])
                
                # Convert Business Hours Integer -> Calendar Datetime (Respecting work weeks & holidays)
                real_start_date = self._project_business_hours(start_offset, t)
                real_end_date = self._project_business_hours(end_offset, t)
                
                # Get resource name
                resource_name = "Unassigned"
                if t.assigned_to and t.assigned_to in resource_map:
                    resource_name = resource_map[t.assigned_to].name
                
                schedule_results.append(ScheduledTask(
                    task_id=t.id,
                    task_name=t.name,
                    resource_id=t.assigned_to if t.assigned_to else "Unassigned",
                    resource_name=resource_name,
                    start_datetime=real_start_date.strftime("%Y-%m-%d %H:%M"),
                    end_datetime=real_end_date.strftime("%Y-%m-%d %H:%M"),
                    project_id=t.project_id
                ))
            
            # Sort by start time for the Gantt chart
            schedule_results.sort(key=lambda x: x.start_datetime)
            return schedule_results
        else:
            raise Exception(f"No solution found. Solver status: {solver.StatusName(status)}")

    def _is_working_day(self, check_date: datetime, project: Optional[Project] = None) -> bool:
        """
        Check if a given date is a working day based on project configuration.
        
        Args:
            check_date: Date to check
            project: Project with work week config (if None, use default Mon-Fri)
            
        Returns:
            True if it's a working day, False otherwise
        """
        # Get working days from project config or use default Mon-Fri
        working_days = [0, 1, 2, 3, 4]  # Default: Monday-Friday
        if project and project.work_week_config:
            working_days = project.work_week_config.working_days
        
        # Check if day of week is in working days
        if check_date.weekday() not in working_days:
            return False
        
        # Check if it's a holiday
        if project and project.holiday_preset:
            if self.holiday_manager.is_holiday(check_date.date(), project.holiday_preset):
                return False
        
        return True

    def _max_hours_on_date(self, d: date, resource_id: Optional[str]) -> int:
        """Max working hours allowed on this date for this resource (demos / reduced capacity)."""
        date_str = d.strftime("%Y-%m-%d")
        for rc in self.reduced_capacities:
            if getattr(rc, "date", None) != date_str:
                continue
            if getattr(rc, "resource_id", None) is None or getattr(rc, "resource_id", None) == resource_id:
                return int(getattr(rc, "available_hours", self.daily_hours))
        return self.daily_hours
    
    def _project_business_hours(self, hour_offset: int, task: Optional[Task] = None) -> datetime:
        """
        Maps a theoretical 'Business Hour Index' (e.g., Hour 20) to a real datetime
        assuming 09:00-17:00 work days and respecting:
        - Custom work week configurations (e.g., Sunday-Thursday for Middle East)
        - Country-specific holidays
        
        Args:
            hour_offset: Number of business hours from start
            task: Task being scheduled (used to get project config)
            
        Returns:
            Actual datetime accounting for work weeks and holidays
        """
        # Get project for this task
        project = None
        if task and task.project_id and task.project_id in self.project_map:
            project = self.project_map[task.project_id]
        
        current = self.start_datetime
        hours_remaining = hour_offset
        
        # Safety counter to prevent infinite loops
        max_iterations = hour_offset * 10 + 10000
        iteration = 0
        
        resource_id = task.assigned_to if task else None
        hours_used_today = 0
        current_date = current.date()

        while hours_remaining > 0:
            iteration += 1
            if iteration > max_iterations:
                return current + timedelta(hours=hours_remaining)

            if not self._is_working_day(current, project):
                current = current.replace(hour=self.work_start_hour, minute=0, second=0) + timedelta(days=1)
                hours_used_today = 0
                current_date = current.date()
                continue

            if current.date() != current_date:
                hours_used_today = 0
                current_date = current.date()

            max_today = self._max_hours_on_date(current_date, resource_id)
            if hours_used_today >= max_today:
                current = current.replace(hour=self.work_start_hour, minute=0, second=0) + timedelta(days=1)
                hours_used_today = 0
                current_date = current.date()
                continue

            if current.hour >= self.work_end_hour:
                current = current.replace(hour=self.work_start_hour, minute=0, second=0) + timedelta(days=1)
                continue
            if current.hour < self.work_start_hour:
                current = current.replace(hour=self.work_start_hour, minute=0, second=0)
                continue

            current += timedelta(hours=1)
            hours_remaining -= 1
            hours_used_today += 1

        return current
