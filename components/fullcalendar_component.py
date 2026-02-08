"""
Calendar component wrapper for Streamlit (react-big-calendar).
Provides interactive week/month/day and agenda views.
"""
import os
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Dict, Any, Optional

# Declare the custom component only when build exists (allows app to run without building frontend)
_RELEASE = True  # Set to False during development
_component_func = None

if not _RELEASE:
    _component_func = components.declare_component(
        "fullcalendar",
        url="http://localhost:3001",  # Dev server URL
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    if os.path.isdir(build_dir):
        _component_func = components.declare_component("fullcalendar", path=build_dir)


def render_fullcalendar(
    events: List[Dict[str, Any]],
    resources: Optional[List[Dict[str, Any]]] = None,
    view: str = "resourceTimelineWeek",
    initial_date: Optional[str] = None,
    height: int = 600,
    header_toolbar: Optional[Dict[str, str]] = None,
    key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Render a calendar component in Streamlit (react-big-calendar).

    View names (e.g. resourceTimelineWeek, dayGridMonth) are mapped to
    week, month, day, or agenda.

    Args:
        events: List of event objects with structure:
            {
                "id": str,
                "title": str,
                "start": str (ISO datetime),
                "end": str (ISO datetime),
                "resourceId": str (for resource timeline),
                "backgroundColor": str (hex color),
                "borderColor": str (hex color),
                "extendedProps": dict (custom data)
            }
        
        resources: List of resource objects (for resource timeline view):
            {
                "id": str,
                "title": str (resource name),
                "businessHours": dict (optional)
            }
        
        view: Calendar view type. Options:
            - "dayGridMonth": Month view
            - "timeGridWeek": Week view with times
            - "timeGridDay": Day view with times
            - "resourceTimelineDay": Resource timeline (day)
            - "resourceTimelineWeek": Resource timeline (week)
            - "resourceTimelineMonth": Resource timeline (month)
            - "resourceTimelineYear": Resource timeline (year)
        
        initial_date: Initial date to display (ISO format YYYY-MM-DD)
        
        height: Height of the calendar in pixels
        
        header_toolbar: Custom toolbar configuration:
            {
                "left": "prev,next today",
                "center": "title",
                "right": "resourceTimelineWeek,resourceTimelineMonth"
            }
        
        key: Unique key for the component
    
    Returns:
        Dictionary with clicked event data, or None if no event clicked
    """
    if _component_func is None:
        st.warning(
            "Calendar component not built. Run: `cd components/frontend && npm run build`"
        )
        return None

    # Default header toolbar
    if header_toolbar is None:
        if view.startswith("resourceTimeline"):
            header_toolbar = {
                "left": "prev,next today",
                "center": "title",
                "right": "resourceTimelineWeek,resourceTimelineMonth,resourceTimelineYear"
            }
        else:
            header_toolbar = {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay"
            }
    
    # Component configuration
    component_value = _component_func(
        events=events,
        resources=resources,
        view=view,
        initialDate=initial_date,
        height=height,
        headerToolbar=header_toolbar,
        key=key,
        default=None
    )
    
    return component_value


def render_resource_gantt(
    schedule: List[Dict[str, Any]],
    resources: List[Dict[str, str]],
    view: str = "resourceTimelineWeek",
    initial_date: Optional[str] = None,
    key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Simplified interface for rendering a resource Gantt chart.
    
    Args:
        schedule: List of scheduled tasks with structure:
            {
                "task_id": str,
                "task_name": str,
                "resource_id": str,
                "resource_name": str,
                "start_datetime": str,
                "end_datetime": str,
                "project_id": str,
                "backgroundColor": str (hex color)
            }
        
        resources: List of resources with structure:
            {
                "id": str,
                "name": str,
                "role": str
            }
        
        view: Timeline view (Week, Month, or Year)
        initial_date: Starting date
        key: Component key
    
    Returns:
        Clicked task data or None
    """
    # Convert schedule to calendar events format
    events = []
    for task in schedule:
        events.append({
            "id": task["task_id"],
            "title": task["task_name"],
            "start": task["start_datetime"],
            "end": task["end_datetime"],
            "resourceId": task["resource_id"],
            "backgroundColor": task.get("backgroundColor", "#3498db"),
            "borderColor": task.get("backgroundColor", "#3498db"),
            "extendedProps": {
                "projectId": task.get("project_id", ""),
                "resourceName": task["resource_name"]
            }
        })
    
    # Convert resources to calendar format
    fc_resources = []
    for resource in resources:
        fc_resources.append({
            "id": resource["id"],
            "title": f"{resource['name']} ({resource['role']})"
        })
    
    return render_fullcalendar(
        events=events,
        resources=fc_resources,
        view=view,
        initial_date=initial_date,
        key=key
    )
