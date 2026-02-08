import streamlit as st
import json
import os
import warnings
from datetime import datetime
from typing import Optional, List
import pandas as pd
import plotly.figure_factory as ff
import plotly.express as px
from dotenv import load_dotenv

# Suppress known third-party warnings (Python 3.9, OpenSSL, google-auth EOL)
warnings.filterwarnings("ignore", message=".*non-supported Python version.*", module="google.api_core")
warnings.filterwarnings("ignore", message=".*Python version 3.9 past its end of life.*", module="google.auth")
warnings.filterwarnings("ignore", message=".*Python version 3.9 past its end of life.*", module="google.oauth2")
warnings.filterwarnings("ignore", message=".*OpenSSL 1.1.1.*", module="urllib3")

from core.models import Task, Resource, ProjectState, ScheduledTask, MultiProjectState, Project, Leave, ReducedCapacity
from core.migrations import migrate_project_state_to_multi
from core.scheduler import SchedulerEngine
from core.brain import GeminiBrain
from core.leave_manager import LeaveManager
from core.shift_optimizer import ShiftOptimizer
from utils.time_utils import format_duration
from utils.user_state import get_user_id, get_state_path, is_logged_in_via_provider

# Load environment variables
load_dotenv()
_env_api_key = os.getenv("GEMINI_API_KEY", "")
if not _env_api_key:
    try:
        _env_api_key = str(st.secrets.get("GEMINI_API_KEY", "") or getattr(st.secrets, "GEMINI_API_KEY", ""))
    except Exception:
        pass


def get_api_key() -> str:
    """API key from Space secrets/env or sidebar input (so Parse with AI works when no secret is set)."""
    return _env_api_key or st.session_state.get("gemini_api_key_input", "")

# Page configuration
st.set_page_config(
    page_title="Gemini PM - AI Project Manager",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state: per-user file (user_data/state_{user_id}.json) or empty
if 'state' not in st.session_state:
    state_path = get_state_path()
    if os.path.isfile(state_path):
        with open(state_path, 'r') as f:
            data = json.load(f)
        if 'projects' not in data:
            old_state = ProjectState(**data)
            st.session_state.state = migrate_project_state_to_multi(old_state)
            with open(state_path, 'w') as fw:
                json.dump(st.session_state.state.model_dump(), fw, indent=2)
            st.success("✅ State migrated to multi-project format!")
        else:
            st.session_state.state = MultiProjectState(**data)
    else:
        st.session_state.state = MultiProjectState(
            projects=[], tasks=[], resources=[], schedule=[], leaves=[], reduced_capacities=[]
        )

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def save_state():
    """Save the current state to the logged-in user's file."""
    state_path = get_state_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, 'w') as f:
        json.dump(st.session_state.state.model_dump(), f, indent=2)


def get_effective_start_date() -> str:
    """First project start date or today (MultiProjectState has no project_start_date)."""
    if st.session_state.state.projects:
        return st.session_state.state.projects[0].start_date
    return datetime.now().strftime("%Y-%m-%d")


def set_effective_start_date(date_str: str) -> None:
    """Update first project start date if any project exists."""
    if st.session_state.state.projects:
        st.session_state.state.projects[0].start_date = date_str

def generate_schedule():
    """Run the OR-Tools scheduler with leave optimization"""
    try:
        if not st.session_state.state.tasks:
            st.warning("No tasks to schedule. Please add tasks first.")
            return
        
        if not st.session_state.state.resources:
            st.error("No resources available. Please add team members first.")
            return
        
        # Step 1: Run base scheduler
        with st.spinner("Running constraint solver..."):
            scheduler = SchedulerEngine(
                tasks=st.session_state.state.tasks,
                resources=st.session_state.state.resources,
                start_date_str=get_effective_start_date(),
                projects=st.session_state.state.projects,
                reduced_capacities=getattr(st.session_state.state, "reduced_capacities", None) or [],
            )
            
            base_schedule = scheduler.solve()
        
        # Step 2: Calculate project buffers
        for project in st.session_state.state.projects:
            leave_mgr = LeaveManager(st.session_state.state.leaves)
            optimizer = ShiftOptimizer(
                leave_manager=leave_mgr,
                projects=st.session_state.state.projects,
                tasks=st.session_state.state.tasks
            )
            
            # Update project buffer
            project.buffer_hours = optimizer.calculate_project_buffer(project.id)
            
            # Calculate total hours
            project_tasks = [t for t in st.session_state.state.tasks if t.project_id == project.id]
            project.total_estimated_hours = sum(t.duration_hours for t in project_tasks)
        
        # Step 3: Apply leave-based optimizations if leaves exist
        if st.session_state.state.leaves:
            with st.spinner("Optimizing for leave conflicts..."):
                leave_manager = LeaveManager(st.session_state.state.leaves)
                shift_optimizer = ShiftOptimizer(
                    leave_manager=leave_manager,
                    projects=st.session_state.state.projects,
                    tasks=st.session_state.state.tasks
                )
                
                optimized_schedule = shift_optimizer.apply_leave_shifts(base_schedule)
                st.session_state.state.schedule = optimized_schedule
                
                # Calculate how much buffer was used
                buffer_used = 0
                for project in st.session_state.state.projects:
                    compressed_tasks = [t for t in optimized_schedule if t.project_id == project.id]
                    # This is a simplified calculation; in reality you'd compare original vs optimized
                    # For now, just show the message
                
                st.success(f"✅ Schedule optimized! {len(optimized_schedule)} tasks scheduled with leave adjustments.")
        else:
            st.session_state.state.schedule = base_schedule
            st.success(f"✅ Schedule generated! {len(base_schedule)} tasks scheduled.")
        
        save_state()
        
    except Exception as e:
        st.error(f"Scheduling failed: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def create_gantt_chart(schedule):
    """Create a Gantt chart from the schedule"""
    if not schedule:
        return None
    
    # Prepare data for Gantt chart
    df_data = []
    for task in schedule:
        df_data.append({
            'Task': task.task_name,
            'Start': task.start_datetime,
            'Finish': task.end_datetime,
            'Resource': task.resource_name
        })
    
    df = pd.DataFrame(df_data)
    
    # Create Gantt chart
    fig = ff.create_gantt(
        df,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        height=400
    )
    
    fig.update_layout(
        title="Project Timeline",
        xaxis_title="Date",
        font=dict(size=10)
    )
    
    return fig


def create_resource_calendar_chart(schedule, height: int = 600, tasks: Optional[List] = None):
    """Create a resource timeline (Plotly). Colors by health (at_risk/blocked) when set, else by project."""
    if not schedule:
        return None
    from utils.color_utils import get_project_color
    task_health = {t.id: getattr(t, "health", "on_track") for t in (tasks or [])}
    df_data = []
    for s in schedule:
        health = task_health.get(s.task_id, "on_track")
        df_data.append({
            "Task": f"{s.task_name} ({s.task_id})",
            "Start": s.start_datetime,
            "Finish": s.end_datetime,
            "Resource": s.resource_name,
            "Project": s.project_id or "—",
            "Health": health,
        })
    df = pd.DataFrame(df_data)
    color_col = "Health" if (tasks and any(getattr(t, "health", "on_track") != "on_track" for t in tasks)) else "Project"
    if color_col == "Health":
        color_map = {"blocked": "#e74c3c", "at_risk": "#f1c40f", "on_track": "#2ecc71"}
    else:
        color_map = {pid: get_project_color(pid) for pid in df["Project"].unique()}
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color=color_col,
        color_discrete_map=color_map,
        title="Resource calendar",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=height, xaxis_title="", font=dict(size=10), showlegend=True)
    return fig

# Header
st.title("🤖 Gemini PM - AI Project Manager")
st.markdown("*Neuro-Symbolic Project Management: AI + Math*")

# Sidebar - Configuration
with st.sidebar:
    # Per-user workspace indicator
    user_id = get_user_id()
    if is_logged_in_via_provider():
        st.caption(f"👤 **{user_id}**")
    else:
        st.caption(f"👤 Session workspace")
    st.divider()
    # Gemini API key: from env/secrets or paste in sidebar (used for Parse with AI, chat, PDF extract)
    st.text_input(
        "Gemini API key",
        type="password",
        key="gemini_api_key_input",
        placeholder="Paste key here (or set GEMINI_API_KEY in Space secrets)" if not _env_api_key else "Using key from environment",
        help="Get one at makersuite.google.com/app/apikey. Optional if set in env/secrets.",
    )
    st.divider()
    st.header("⚙️ Configuration")
    
    # Project Start Date (uses first project when in multi-project mode)
    start_date = st.date_input(
        "Project Start Date",
        value=datetime.strptime(get_effective_start_date(), "%Y-%m-%d")
    )
    
    if st.button("Update Start Date"):
        set_effective_start_date(start_date.strftime("%Y-%m-%d"))
        save_state()
        st.success("Start date updated!")
    
    st.divider()
    
    # Team Members
    st.header("👥 Team Members")
    
    with st.expander("Add New Member"):
        new_member_id = st.text_input("ID (e.g., R1)", key="new_member_id")
        new_member_name = st.text_input("Name", key="new_member_name")
        new_member_role = st.selectbox(
            "Role",
            ["Frontend", "Backend", "Full-Stack", "Designer", "QA", "DevOps", "PM"],
            key="new_member_role"
        )
        
        if st.button("Add Member"):
            if new_member_id and new_member_name:
                new_resource = Resource(
                    id=new_member_id,
                    name=new_member_name,
                    role=new_member_role
                )
                st.session_state.state.resources.append(new_resource)
                save_state()
                st.success(f"Added {new_member_name}!")
                st.rerun()
    
    # Display existing members
    if st.session_state.state.resources:
        for resource in st.session_state.state.resources:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{resource.name}** ({resource.role})")
            with col2:
                if st.button("🗑️", key=f"del_{resource.id}"):
                    st.session_state.state.resources = [
                        r for r in st.session_state.state.resources if r.id != resource.id
                    ]
                    save_state()
                    st.rerun()
    else:
        st.info("No team members yet")
    
    st.divider()
    
    # Leave Management
    st.header("🏖️ Leave Management")
    
    with st.expander("Add Leave"):
        leave_resource = st.selectbox(
            "Team Member",
            [r.id for r in st.session_state.state.resources],
            format_func=lambda x: next((r.name for r in st.session_state.state.resources if r.id == x), x),
            key="leave_resource"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            leave_start = st.date_input("Start Date", key="leave_start")
        with col2:
            leave_end = st.date_input("End Date", key="leave_end")
        
        leave_type = st.selectbox(
            "Leave Type",
            ["vacation", "sick", "personal", "unpaid"],
            key="leave_type"
        )
        
        if st.button("Add Leave"):
            if leave_resource and leave_start and leave_end:
                # Generate unique leave ID
                leave_id = f"L{len(st.session_state.state.leaves) + 1}"
                
                new_leave = Leave(
                    id=leave_id,
                    resource_id=leave_resource,
                    start_date=leave_start.strftime("%Y-%m-%d"),
                    end_date=leave_end.strftime("%Y-%m-%d"),
                    leave_type=leave_type
                )
                
                st.session_state.state.leaves.append(new_leave)
                save_state()
                st.success(f"Added {leave_type} leave for {leave_resource}")
                st.rerun()
    
    # Display existing leaves
    if st.session_state.state.leaves:
        st.subheader("Current Leaves")
        for leave in st.session_state.state.leaves:
            resource_name = next((r.name for r in st.session_state.state.resources if r.id == leave.resource_id), leave.resource_id)
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{resource_name}**: {leave.start_date} to {leave.end_date} ({leave.leave_type})")
            with col2:
                if st.button("🗑️", key=f"del_leave_{leave.id}"):
                    st.session_state.state.leaves = [
                        l for l in st.session_state.state.leaves if l.id != leave.id
                    ]
                    save_state()
                    st.rerun()
    else:
        st.info("No leaves scheduled")
    
    st.divider()
    st.subheader("⏱ Reduced capacity (demos)")
    with st.expander("Add reduced capacity day"):
        rc_date = st.date_input("Date", key="rc_date")
        rc_resource = st.selectbox(
            "Resource (optional = all)",
            ["All"] + [r.id for r in st.session_state.state.resources],
            key="rc_resource",
        )
        rc_hours = st.number_input("Available hours", min_value=1, max_value=8, value=2, key="rc_hours")
        rc_reason = st.text_input("Reason", value="Scheduled Demo", key="rc_reason")
        if st.button("Add reduced capacity", key="add_rc"):
            rc_list = getattr(st.session_state.state, "reduced_capacities", None) or []
            rc_list.append(ReducedCapacity(
                id=f"RC{len(rc_list) + 1}",
                date=rc_date.strftime("%Y-%m-%d"),
                resource_id=None if rc_resource == "All" else rc_resource,
                available_hours=rc_hours,
                reason=rc_reason,
            ))
            st.session_state.state.reduced_capacities = rc_list
            save_state()
            st.success("Added.")
            st.rerun()
    if getattr(st.session_state.state, "reduced_capacities", None):
        for rc in st.session_state.state.reduced_capacities:
            st.caption(f"{rc.date}: {rc.available_hours}h — {rc.reason}")

# Initialize calendar view state
if 'calendar_view' not in st.session_state:
    st.session_state.calendar_view = "resourceTimelineWeek"

# Main area - Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Requirements", "📊 Schedule", "📘 Resource Calendar", "💬 Chat", "🔧 Manual Tasks"])

# Tab 1: Requirements Parser
with tab1:
    st.header("Project Requirements Parser")
    st.markdown("Upload a PDF project brief or paste a description. Gemini extracts tasks, deadlines, and man-hours.")
    
    # PDF upload
    uploaded_file = st.file_uploader("Upload PDF project brief", type=["pdf"], key="pdf_brief")
    if uploaded_file and get_api_key():
        if st.button("📄 Extract from PDF (Gemini 2.5 Pro)", key="extract_pdf"):
            with st.spinner("Extracting structured data from PDF..."):
                try:
                    from core.document_parser import get_document_parser
                    parser = get_document_parser()
                    pdf_text = parser.extract_text_from_bytes(uploaded_file.getvalue(), uploaded_file.name)
                    brain = GeminiBrain(get_api_key())
                    brief = brain.extract_project_brief(pdf_text)
                    st.session_state["extracted_brief"] = brief
                    st.success(f"Extracted: {len(brief.get('tasks', []))} tasks, deadline: {brief.get('project_deadline', 'N/A')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {str(e)}")
    
    if st.session_state.get("extracted_brief"):
        brief = st.session_state["extracted_brief"]
        with st.expander("📋 Extracted brief (Apply to create tasks)", expanded=True):
            st.json(brief)
            if st.button("Apply to project", key="apply_brief"):
                tasks_from_brief = []
                priority_map = {"High": 1, "Medium": 2, "Low": 3}
                for i, t in enumerate(brief.get("tasks", []), 1):
                    tid = f"T{i}"
                    tasks_from_brief.append(Task(
                        id=tid,
                        name=t.get("name", "Task"),
                        duration_hours=int(t.get("estimated_hours", 8)),
                        dependencies=[],  # could resolve by name if needed
                        assigned_to=None,
                        priority=priority_map.get(t.get("priority", "Medium"), 2),
                        project_id=st.session_state.state.projects[0].id if st.session_state.state.projects else "P1",
                        complexity="medium",
                        required_skillset=t.get("required_skillset"),
                    ))
                st.session_state.state.tasks = tasks_from_brief
                if brief.get("project_deadline") and st.session_state.state.projects:
                    st.session_state.state.projects[0].end_date = brief["project_deadline"]
                save_state()
                del st.session_state["extracted_brief"]
                st.success(f"Applied {len(tasks_from_brief)} tasks.")
                st.rerun()
    
    requirements = st.text_area(
        "Or paste project description",
        height=200,
        placeholder="Example: Build a web app with user authentication, dashboard, and API integration."
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🧠 Parse with AI", type="primary", disabled=not get_api_key()):
            if not get_api_key():
                st.error("Add your Gemini API key in the sidebar (or set GEMINI_API_KEY in Space secrets)")
            elif not st.session_state.state.resources:
                st.error("Please add team members first")
            else:
                with st.spinner("Analyzing requirements with Gemini..."):
                    try:
                        brain = GeminiBrain(get_api_key())
                        tasks = brain.parse_requirements(requirements, st.session_state.state.resources)
                        st.session_state.state.tasks = tasks
                        save_state()
                        st.success(f"✅ Parsed {len(tasks)} tasks!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Parsing failed: {str(e)}")
    with col2:
        if st.button("📅 Generate Schedule", disabled=not st.session_state.state.tasks):
            generate_schedule()
            st.rerun()
    
    if st.session_state.state.tasks:
        st.subheader("Parsed Tasks")
        for task in st.session_state.state.tasks:
            with st.expander(f"{task.id}: {task.name}"):
                st.write(f"**Duration:** {format_duration(task.duration_hours)}")
                st.write(f"**Assigned to:** {task.assigned_to or 'Unassigned'}")
                st.write(f"**Dependencies:** {', '.join(task.dependencies) if task.dependencies else 'None'}")
                st.write(f"**Priority:** {task.priority}")
                if getattr(task, "required_skillset", None):
                    st.write(f"**Skillset:** {task.required_skillset}")

# Tab 2: Schedule Visualization
with tab2:
    st.header("Project Schedule")
    
    if st.session_state.state.schedule:
        # Deadline at-risk (critical path)
        from core.deadline_engine import get_tasks_at_risk, suggest_priority_compression
        deadline = None
        if st.session_state.state.projects and st.session_state.state.projects[0].end_date:
            deadline = st.session_state.state.projects[0].end_date
        if deadline:
            at_risk = get_tasks_at_risk(
                st.session_state.state.tasks,
                st.session_state.state.schedule,
                deadline,
            )
            if at_risk:
                st.warning(f"⚠️ **Deadline {deadline}**: {len(at_risk)} task(s) at risk (end after deadline).")
                suggestions = suggest_priority_compression(
                    at_risk,
                    st.session_state.state.resources,
                    st.session_state.state.schedule,
                )
                if suggestions:
                    with st.expander("💡 Priority compression (re-assign low-priority tasks)"):
                        for s in suggestions[:5]:
                            st.write(f"**{s['task_name']}** ({s['task_id']}): {s['suggestion']}")
                for t in at_risk[:10]:
                    st.caption(f"• {t.id}: {t.name}")
            else:
                st.success(f"✅ Schedule meets deadline {deadline}.")
        # Buffer information
        if st.session_state.state.projects:
            st.subheader("Project Buffer Status")
            
            for project in st.session_state.state.projects:
                # Calculate buffer utilization
                from core.shift_optimizer import ShiftOptimizer
                from core.leave_manager import LeaveManager
                
                leave_mgr = LeaveManager(st.session_state.state.leaves)
                optimizer = ShiftOptimizer(
                    leave_manager=leave_mgr,
                    projects=st.session_state.state.projects,
                    tasks=st.session_state.state.tasks
                )
                
                available_buffer = optimizer.calculate_project_buffer(project.id)
                total_hours = project.total_estimated_hours or sum(
                    t.duration_hours for t in st.session_state.state.tasks if t.project_id == project.id
                )
                
                buffer_percentage = (available_buffer / total_hours * 100) if total_hours > 0 else 0
                
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{project.name}**")
                
                with col2:
                    st.metric("Total Hours", f"{total_hours}h")
                
                with col3:
                    st.metric("Buffer", f"{available_buffer:.0f}h")
                
                with col4:
                    # Color-code buffer status
                    if buffer_percentage >= 15:
                        st.success(f"{buffer_percentage:.1f}%")
                    elif buffer_percentage >= 10:
                        st.warning(f"{buffer_percentage:.1f}%")
                    else:
                        st.error(f"{buffer_percentage:.1f}%")
                
                # Progress bar showing buffer
                st.progress(min(buffer_percentage / 20, 1.0), text=f"Buffer Health: {buffer_percentage:.1f}%")
            
            st.divider()
        # Summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Tasks", len(st.session_state.state.schedule))
        
        with col2:
            first_task = min(st.session_state.state.schedule, key=lambda x: x.start_datetime)
            last_task = max(st.session_state.state.schedule, key=lambda x: x.end_datetime)
            start = datetime.strptime(first_task.start_datetime, "%Y-%m-%d %H:%M")
            end = datetime.strptime(last_task.end_datetime, "%Y-%m-%d %H:%M")
            duration_days = (end - start).days + 1
            st.metric("Project Duration", f"{duration_days} days")
        
        with col3:
            st.metric("Team Members", len(st.session_state.state.resources))
        
        # Gantt Chart
        st.subheader("Timeline")
        gantt = create_gantt_chart(st.session_state.state.schedule)
        if gantt:
            st.plotly_chart(gantt, use_container_width=True)
        
        # Task List
        st.subheader("Task Details")
        df = pd.DataFrame([task.model_dump() for task in st.session_state.state.schedule])
        st.dataframe(df, use_container_width=True)
        
        # AI Summary
        if get_api_key():
            if st.button("🤖 Generate AI Summary"):
                with st.spinner("Generating summary..."):
                    try:
                        brain = GeminiBrain(get_api_key())
                        summary = brain.generate_summary([task.model_dump() for task in st.session_state.state.schedule])
                        st.info(summary)
                    except Exception as e:
                        st.error(f"Summary generation failed: {str(e)}")
        
    else:
        st.info("No schedule generated yet. Parse requirements and generate a schedule first.")

# Tab 3: Resource Calendar (Plotly timeline - no custom component)
with tab3:
    st.header("Resource Calendar View")
    st.markdown("Timeline of resource allocation by project. Uses Plotly so it loads in all environments.")
    
    if st.session_state.state.schedule and st.session_state.state.resources:
        chart = create_resource_calendar_chart(
            st.session_state.state.schedule,
            height=600,
            tasks=st.session_state.state.tasks,
        )
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        with st.expander("📋 Schedule table"):
            rows = [
                {
                    "Task": t.task_name,
                    "Resource": t.resource_name,
                    "Start": t.start_datetime,
                    "End": t.end_datetime,
                    "Project": t.project_id or "—",
                }
                for t in st.session_state.state.schedule
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Generate a schedule in the **📊 Schedule** tab to see the resource calendar here.")

# Tab 4: Chat Interface
with tab4:
    st.header("Project Chat Assistant")
    st.markdown("Ask questions or make changes to your project plan in natural language.")
    
    # Chat history display
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Chat input
    user_input = st.chat_input("Ask something or request a change...")
    
    if user_input:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        if not get_api_key():
            response = "Add your Gemini API key in the sidebar to use the chat feature."
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        else:
            with st.spinner("Thinking..."):
                try:
                    brain = GeminiBrain(get_api_key())
                    action = brain.interpret_chat(
                        user_input,
                        st.session_state.state.model_dump()
                    )
                    
                    schedule_updated = False
                    if action["action"] == "add_task":
                        new_task = Task(**action["task"])
                        st.session_state.state.tasks.append(new_task)
                        schedule_updated = True
                        response = f"✅ Added task: {new_task.name}"
                        
                    elif action["action"] == "update_task":
                        task_id = action["task_id"]
                        updates = action["updates"]
                        for task in st.session_state.state.tasks:
                            if task.id == task_id:
                                for key, value in updates.items():
                                    setattr(task, key, value)
                        schedule_updated = True
                        response = f"✅ Updated task {task_id}"
                        
                    elif action["action"] == "remove_task":
                        task_id = action.get("task_id")
                        if task_id:
                            st.session_state.state.tasks = [t for t in st.session_state.state.tasks if t.id != task_id]
                            schedule_updated = True
                            response = f"✅ Removed task {task_id}"
                        else:
                            response = "No task ID provided to remove."
                        
                    elif action["action"] == "add_resource":
                        new_resource = Resource(**action["resource"])
                        st.session_state.state.resources.append(new_resource)
                        schedule_updated = True
                        response = f"✅ Added team member: {new_resource.name}"
                        
                    else:
                        response = action.get("message", "I processed your request.")
                    
                    if schedule_updated:
                        try:
                            generate_schedule()
                            response += " Schedule has been regenerated; check the Schedule and Resource Calendar tabs."
                        except Exception as sched_err:
                            response += f" (Schedule could not be regenerated: {sched_err})"
                        save_state()
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    response = f"Error: {str(e)}"
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        st.rerun()

# Tab 5: Manual Task Management
with tab5:
    st.header("Manual Task Management")
    
    with st.expander("Add New Task Manually"):
        task_id = st.text_input("Task ID (e.g., T1)", key="manual_task_id")
        task_name = st.text_input("Task Name", key="manual_task_name")
        task_duration = st.number_input("Duration (hours)", min_value=1, max_value=160, value=8, key="manual_duration")
        task_assigned = st.selectbox(
            "Assigned To",
            [""] + [r.id for r in st.session_state.state.resources],
            key="manual_assigned"
        )
        task_deps = st.multiselect(
            "Dependencies",
            [t.id for t in st.session_state.state.tasks],
            key="manual_deps"
        )
        task_priority = st.slider("Priority", 1, 5, 1, key="manual_priority")
        
        if st.button("Add Task", key="manual_add_button"):
            if task_id and task_name:
                new_task = Task(
                    id=task_id,
                    name=task_name,
                    duration_hours=task_duration,
                    assigned_to=task_assigned if task_assigned else None,
                    dependencies=task_deps,
                    priority=task_priority,
                    project_id=st.session_state.state.projects[0].id if st.session_state.state.projects else "P1",
                )
                st.session_state.state.tasks.append(new_task)
                save_state()
                st.success(f"Added task: {task_name}")
                st.rerun()
    
    if st.session_state.state.tasks:
        st.subheader("Current Tasks (status & health)")
        for i, task in enumerate(st.session_state.state.tasks):
            with st.expander(f"{task.id}: {task.name} — {getattr(task, 'health', 'on_track')}"):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**Duration:** {format_duration(task.duration_hours)} | **Assigned:** {task.assigned_to or 'Unassigned'}")
                    health = st.selectbox(
                        "Health",
                        ["on_track", "at_risk", "blocked"],
                        index=["on_track", "at_risk", "blocked"].index(getattr(task, "health", "on_track")),
                        key=f"health_{task.id}",
                    )
                    status_note = st.text_area("User suggestion / status", value=getattr(task, "status_note", "") or "", key=f"note_{task.id}", placeholder="e.g. Dependency on client is slowing this down")
                    if health != getattr(task, "health", "on_track") or (status_note or "") != (getattr(task, "status_note", None) or ""):
                        if st.button("Save", key=f"save_task_{task.id}"):
                            task.health = health
                            task.status_note = status_note.strip() or None
                            save_state()
                            st.rerun()
                with col2:
                    if st.button("Delete", key=f"del_task_{i}"):
                        st.session_state.state.tasks.pop(i)
                        save_state()
                        st.rerun()
    else:
        st.info("No tasks yet. Add tasks using the Requirements Parser or manually above.")

# Footer
st.divider()
st.caption("Powered by Google Gemini 1.5 + OR-Tools | Neuro-Symbolic AI Architecture")
