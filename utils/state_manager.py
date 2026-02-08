"""
State Manager - Centralized state management with observer pattern.
Handles state updates and triggers re-computation when needed.
"""
from typing import Callable, List, Dict, Any, Optional
from datetime import datetime
from core.models import MultiProjectState, Leave, Task, Resource, Project


class StateObserver:
    """Base class for state observers."""
    
    def on_state_change(self, event_type: str, data: Any):
        """
        Called when state changes.
        
        Args:
            event_type: Type of change (e.g., "leave_added", "task_updated")
            data: Relevant data for the change
        """
        pass


class StateManager:
    """
    Manages application state with observer pattern.
    Provides centralized state updates and change notifications.
    """
    
    def __init__(self, state: MultiProjectState):
        """
        Initialize the state manager.
        
        Args:
            state: Initial state
        """
        self.state = state
        self.observers: List[StateObserver] = []
        self.change_history: List[Dict[str, Any]] = []
        self._auto_schedule = False
    
    def register_observer(self, observer: StateObserver):
        """Register an observer to receive state change notifications."""
        if observer not in self.observers:
            self.observers.append(observer)
    
    def unregister_observer(self, observer: StateObserver):
        """Unregister an observer."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def _notify_observers(self, event_type: str, data: Any):
        """Notify all observers of a state change."""
        for observer in self.observers:
            try:
                observer.on_state_change(event_type, data)
            except Exception as e:
                print(f"Error notifying observer: {e}")
        
        # Record change in history
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        })
    
    def set_auto_schedule(self, enabled: bool):
        """
        Enable/disable automatic re-scheduling on state changes.
        
        Args:
            enabled: Whether to auto-schedule
        """
        self._auto_schedule = enabled
    
    # Leave operations
    def add_leave(self, leave: Leave):
        """
        Add a leave record and notify observers.
        
        Args:
            leave: Leave object to add
        """
        self.state.leaves.append(leave)
        self._notify_observers("leave_added", {"leave_id": leave.id, "resource_id": leave.resource_id})
        
        if self._auto_schedule:
            self._trigger_reschedule()
    
    def remove_leave(self, leave_id: str) -> bool:
        """
        Remove a leave record and notify observers.
        
        Args:
            leave_id: ID of the leave to remove
            
        Returns:
            True if leave was found and removed
        """
        initial_count = len(self.state.leaves)
        self.state.leaves = [l for l in self.state.leaves if l.id != leave_id]
        
        if len(self.state.leaves) < initial_count:
            self._notify_observers("leave_removed", {"leave_id": leave_id})
            
            if self._auto_schedule:
                self._trigger_reschedule()
            
            return True
        return False
    
    def update_leave(self, leave_id: str, **updates) -> bool:
        """
        Update a leave record and notify observers.
        
        Args:
            leave_id: ID of the leave to update
            **updates: Fields to update
            
        Returns:
            True if leave was found and updated
        """
        for leave in self.state.leaves:
            if leave.id == leave_id:
                for key, value in updates.items():
                    if hasattr(leave, key):
                        setattr(leave, key, value)
                
                self._notify_observers("leave_updated", {"leave_id": leave_id, "updates": updates})
                
                if self._auto_schedule:
                    self._trigger_reschedule()
                
                return True
        return False
    
    # Task operations
    def add_task(self, task: Task):
        """Add a task and notify observers."""
        self.state.tasks.append(task)
        self._notify_observers("task_added", {"task_id": task.id})
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task and notify observers."""
        initial_count = len(self.state.tasks)
        self.state.tasks = [t for t in self.state.tasks if t.id != task_id]
        
        if len(self.state.tasks) < initial_count:
            self._notify_observers("task_removed", {"task_id": task_id})
            return True
        return False
    
    def update_task(self, task_id: str, **updates) -> bool:
        """Update a task and notify observers."""
        for task in self.state.tasks:
            if task.id == task_id:
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                
                self._notify_observers("task_updated", {"task_id": task_id, "updates": updates})
                return True
        return False
    
    # Resource operations
    def add_resource(self, resource: Resource):
        """Add a resource and notify observers."""
        self.state.resources.append(resource)
        self._notify_observers("resource_added", {"resource_id": resource.id})
    
    def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource and notify observers."""
        initial_count = len(self.state.resources)
        self.state.resources = [r for r in self.state.resources if r.id != resource_id]
        
        if len(self.state.resources) < initial_count:
            self._notify_observers("resource_removed", {"resource_id": resource_id})
            return True
        return False
    
    def update_resource(self, resource_id: str, **updates) -> bool:
        """Update a resource and notify observers."""
        for resource in self.state.resources:
            if resource.id == resource_id:
                for key, value in updates.items():
                    if hasattr(resource, key):
                        setattr(resource, key, value)
                
                self._notify_observers("resource_updated", {"resource_id": resource_id, "updates": updates})
                return True
        return False
    
    # Project operations
    def add_project(self, project: Project):
        """Add a project and notify observers."""
        self.state.projects.append(project)
        self._notify_observers("project_added", {"project_id": project.id})
    
    def remove_project(self, project_id: str) -> bool:
        """Remove a project and notify observers."""
        initial_count = len(self.state.projects)
        self.state.projects = [p for p in self.state.projects if p.id != project_id]
        
        if len(self.state.projects) < initial_count:
            self._notify_observers("project_removed", {"project_id": project_id})
            return True
        return False
    
    def update_project(self, project_id: str, **updates) -> bool:
        """Update a project and notify observers."""
        for project in self.state.projects:
            if project.id == project_id:
                for key, value in updates.items():
                    if hasattr(project, key):
                        setattr(project, key, value)
                
                self._notify_observers("project_updated", {"project_id": project_id, "updates": updates})
                return True
        return False
    
    def _trigger_reschedule(self):
        """Trigger automatic rescheduling."""
        self._notify_observers("reschedule_requested", {})
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current state."""
        return self.state.model_dump()
    
    def get_change_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the history of state changes.
        
        Args:
            limit: Optional limit on number of changes to return
            
        Returns:
            List of change records
        """
        if limit:
            return self.change_history[-limit:]
        return self.change_history.copy()
    
    def clear_history(self):
        """Clear the change history."""
        self.change_history.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the current state."""
        return {
            "total_projects": len(self.state.projects),
            "total_tasks": len(self.state.tasks),
            "total_resources": len(self.state.resources),
            "total_leaves": len(self.state.leaves),
            "scheduled_tasks": len(self.state.schedule),
            "changes_tracked": len(self.change_history)
        }


class SchedulingObserver(StateObserver):
    """Observer that triggers re-scheduling on relevant state changes."""
    
    def __init__(self, schedule_callback: Callable):
        """
        Initialize the scheduling observer.
        
        Args:
            schedule_callback: Function to call when rescheduling is needed
        """
        self.schedule_callback = schedule_callback
        self.trigger_events = {
            "leave_added", "leave_removed", "leave_updated",
            "task_added", "task_removed", "task_updated",
            "resource_added", "resource_removed"
        }
    
    def on_state_change(self, event_type: str, data: Any):
        """Trigger rescheduling for relevant events."""
        if event_type in self.trigger_events:
            print(f"Triggering reschedule due to: {event_type}")
            self.schedule_callback()


# Singleton instance
_state_manager_instance: Optional[StateManager] = None


def get_state_manager(state: Optional[MultiProjectState] = None) -> StateManager:
    """
    Get the singleton StateManager instance.
    
    Args:
        state: Initial state (only used on first call)
        
    Returns:
        StateManager instance
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        if state is None:
            raise ValueError("State must be provided on first call to get_state_manager")
        _state_manager_instance = StateManager(state)
    return _state_manager_instance


def reset_state_manager():
    """Reset the singleton instance (useful for testing)."""
    global _state_manager_instance
    _state_manager_instance = None
