"""
Leave Manager - Manages employee leave/time-off for resource scheduling.
"""
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from core.models import Leave, Resource


class LeaveManager:
    """
    Manages leave records for resources and checks availability.
    """
    
    def __init__(self, leaves: Optional[List[Leave]] = None):
        """
        Initialize the leave manager.
        
        Args:
            leaves: Initial list of leave records
        """
        self.leaves: List[Leave] = leaves or []
        self._cache: Dict[str, List[Leave]] = {}
        self._rebuild_cache()
    
    def _rebuild_cache(self):
        """Rebuild the cache of leaves grouped by resource ID."""
        self._cache = {}
        for leave in self.leaves:
            if leave.resource_id not in self._cache:
                self._cache[leave.resource_id] = []
            self._cache[leave.resource_id].append(leave)
    
    def add_leave(self, leave: Leave) -> None:
        """
        Add a new leave record.
        
        Args:
            leave: Leave object to add
        """
        # Validate dates
        start = datetime.fromisoformat(leave.start_date).date()
        end = datetime.fromisoformat(leave.end_date).date()
        
        if end < start:
            raise ValueError("Leave end date cannot be before start date")
        
        self.leaves.append(leave)
        self._rebuild_cache()
    
    def remove_leave(self, leave_id: str) -> bool:
        """
        Remove a leave record by ID.
        
        Args:
            leave_id: ID of the leave to remove
            
        Returns:
            True if leave was found and removed, False otherwise
        """
        initial_count = len(self.leaves)
        self.leaves = [l for l in self.leaves if l.id != leave_id]
        
        if len(self.leaves) < initial_count:
            self._rebuild_cache()
            return True
        return False
    
    def get_leave_by_id(self, leave_id: str) -> Optional[Leave]:
        """
        Get a leave record by ID.
        
        Args:
            leave_id: ID of the leave to find
            
        Returns:
            Leave object if found, None otherwise
        """
        for leave in self.leaves:
            if leave.id == leave_id:
                return leave
        return None
    
    def get_leaves_for_resource(self, resource_id: str) -> List[Leave]:
        """
        Get all leave records for a specific resource.
        
        Args:
            resource_id: ID of the resource
            
        Returns:
            List of Leave objects for the resource
        """
        return self._cache.get(resource_id, [])
    
    def is_resource_available(self, resource_id: str, check_date: date) -> bool:
        """
        Check if a resource is available (not on leave) on a specific date.
        
        Args:
            resource_id: ID of the resource to check
            check_date: Date to check availability
            
        Returns:
            True if resource is available, False if on leave
        """
        leaves = self.get_leaves_for_resource(resource_id)
        
        for leave in leaves:
            start = datetime.fromisoformat(leave.start_date).date()
            end = datetime.fromisoformat(leave.end_date).date()
            
            if start <= check_date <= end:
                return False
        
        return True
    
    def get_leave_conflicts(self, resource_id: str, start_date: date, end_date: date) -> List[Leave]:
        """
        Find all leave records that conflict with a given date range.
        
        Args:
            resource_id: ID of the resource
            start_date: Start of the range to check
            end_date: End of the range to check
            
        Returns:
            List of conflicting Leave objects
        """
        leaves = self.get_leaves_for_resource(resource_id)
        conflicts = []
        
        for leave in leaves:
            leave_start = datetime.fromisoformat(leave.start_date).date()
            leave_end = datetime.fromisoformat(leave.end_date).date()
            
            # Check if ranges overlap
            if not (leave_end < start_date or leave_start > end_date):
                conflicts.append(leave)
        
        return conflicts
    
    def get_unavailable_dates(self, resource_id: str, year: int, month: Optional[int] = None) -> List[date]:
        """
        Get all dates when a resource is unavailable in a given time period.
        
        Args:
            resource_id: ID of the resource
            year: Year to check
            month: Optional month (1-12). If None, returns for entire year
            
        Returns:
            List of dates when resource is on leave
        """
        leaves = self.get_leaves_for_resource(resource_id)
        unavailable_dates = []
        
        for leave in leaves:
            leave_start = datetime.fromisoformat(leave.start_date).date()
            leave_end = datetime.fromisoformat(leave.end_date).date()
            
            current_date = leave_start
            while current_date <= leave_end:
                # Check if date matches the requested time period
                if current_date.year == year:
                    if month is None or current_date.month == month:
                        unavailable_dates.append(current_date)
                current_date += timedelta(days=1)
        
        return sorted(unavailable_dates)
    
    def update_leave(self, leave_id: str, **updates) -> bool:
        """
        Update fields of an existing leave record.
        
        Args:
            leave_id: ID of the leave to update
            **updates: Field names and new values
            
        Returns:
            True if leave was found and updated, False otherwise
        """
        for leave in self.leaves:
            if leave.id == leave_id:
                for key, value in updates.items():
                    if hasattr(leave, key):
                        setattr(leave, key, value)
                
                # Rebuild cache if resource_id was changed
                if 'resource_id' in updates:
                    self._rebuild_cache()
                
                return True
        return False
    
    def get_all_leaves(self) -> List[Leave]:
        """
        Get all leave records.
        
        Returns:
            List of all Leave objects
        """
        return self.leaves.copy()
    
    def get_leaves_in_range(self, start_date: date, end_date: date) -> List[Leave]:
        """
        Get all leaves that occur within or overlap a date range.
        
        Args:
            start_date: Start of the range
            end_date: End of the range
            
        Returns:
            List of Leave objects in range
        """
        leaves_in_range = []
        
        for leave in self.leaves:
            leave_start = datetime.fromisoformat(leave.start_date).date()
            leave_end = datetime.fromisoformat(leave.end_date).date()
            
            # Check if ranges overlap
            if not (leave_end < start_date or leave_start > end_date):
                leaves_in_range.append(leave)
        
        return leaves_in_range
    
    def get_resource_leave_summary(self, resource_id: str, year: int) -> Dict[str, int]:
        """
        Get a summary of leave statistics for a resource in a year.
        
        Args:
            resource_id: ID of the resource
            year: Year to analyze
            
        Returns:
            Dictionary with leave statistics
        """
        leaves = self.get_leaves_for_resource(resource_id)
        
        total_days = 0
        by_type = {}
        
        for leave in leaves:
            leave_start = datetime.fromisoformat(leave.start_date).date()
            leave_end = datetime.fromisoformat(leave.end_date).date()
            
            # Calculate days in the requested year
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            
            effective_start = max(leave_start, year_start)
            effective_end = min(leave_end, year_end)
            
            if effective_start <= effective_end:
                days = (effective_end - effective_start).days + 1
                total_days += days
                
                leave_type = leave.leave_type
                by_type[leave_type] = by_type.get(leave_type, 0) + days
        
        return {
            "total_days": total_days,
            "by_type": by_type
        }


# Singleton instance
_leave_manager_instance = None


def get_leave_manager(leaves: Optional[List[Leave]] = None) -> LeaveManager:
    """
    Get the singleton LeaveManager instance.
    
    Args:
        leaves: Initial leaves list (only used on first call)
        
    Returns:
        LeaveManager instance
    """
    global _leave_manager_instance
    if _leave_manager_instance is None:
        _leave_manager_instance = LeaveManager(leaves)
    return _leave_manager_instance


def reset_leave_manager():
    """Reset the singleton instance (useful for testing)."""
    global _leave_manager_instance
    _leave_manager_instance = None
