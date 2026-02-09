# Gemini PM - Technical Architecture

## System Overview

Gemini PM implements a **Neuro-Symbolic Architecture** that combines:
- **Symbolic AI** (Mathematical Optimization) for deterministic scheduling
- **Neural AI** (Large Language Models) for natural language understanding

This hybrid approach ensures both flexibility (understand messy requirements) and reliability (mathematically optimal schedules).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│                      (Streamlit - app.py)                   │
│                                                              │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │ Requirements │   Schedule   │     Chat     │  Manual  │ │
│  │    Parser    │    Viewer    │  Assistant   │   Tasks  │ │
│  └──────────────┴──────────────┴──────────────┴──────────┘ │
└────────────────┬─────────────────────────────────┬──────────┘
                 │                                 │
                 ▼                                 ▼
┌────────────────────────────────┐  ┌─────────────────────────┐
│       AI BRAIN (brain.py)      │  │  STATE MANAGEMENT       │
│                                │  │  (state.json)           │
│  ┌──────────────────────────┐  │  │                         │
│  │  Gemini 3 Pro            │  │  │  • Tasks                │
│  │  (Requirement Parsing)   │  │  │  • Resources            │
│  └──────────────────────────┘  │  │  • Schedule             │
│                                │  │  • Project Settings     │
│  ┌──────────────────────────┐  │  │                         │
│  │  Gemini 3 Flash          │  │  └─────────────────────────┘
│  │  (Chat & Updates)        │  │
│  └──────────────────────────┘  │
│                                │
│  Converts Natural Language     │
│  to Structured Data (JSON)     │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│    DATA MODELS (models.py)     │
│                                │
│  • Task (Pydantic)             │
│  • Resource (Pydantic)         │
│  • ScheduledTask (Pydantic)    │
│  • ProjectState (Pydantic)     │
│                                │
│  Enforces type safety and      │
│  validation between AI & Math  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────────┐
│         SCHEDULER ENGINE (scheduler.py)                     │
│                                                              │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  NetworkX (Graph)    │      │  OR-Tools (CP-SAT)   │   │
│  │                      │      │                      │   │
│  │  • DAG Validation    │      │  • Constraint Solver │   │
│  │  • Cycle Detection   │      │  • Optimization      │   │
│  │  • Dependency Check  │      │  • Resource Alloc    │   │
│  └──────────────────────┘      └──────────────────────┘   │
│                                                              │
│  Constraints:                                                │
│  1. Precedence (dependencies)                               │
│  2. No overlap (resource conflicts)                         │
│  3. Business hours (9 AM - 5 PM)                            │
│  4. Weekends (skip Sat/Sun)                                 │
│                                                              │
│  Objective: Minimize project duration                       │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────┐
│  TIME PROJECTION (utils/)      │
│                                │
│  Maps abstract "Business Hours"│
│  to real calendar dates        │
│                                │
│  Hour 0 → Monday 9:00 AM       │
│  Hour 8 → Monday 5:00 PM       │
│  Hour 9 → Tuesday 9:00 AM      │
│  (Skips weekends automatically)│
└────────────────────────────────┘
```

## Data Flow

### 1. Requirement Parsing Flow

```
User Input (Text)
    │
    ▼
Gemini 3 Pro
    │
    ▼
Prompt Engineering
    │
    ▼
JSON Response
    │
    ▼
Pydantic Validation
    │
    ▼
Task[] Objects
    │
    ▼
Save to state.json
```

### 2. Scheduling Flow

```
Task[] + Resource[]
    │
    ▼
NetworkX DAG Check
    │
    ▼
OR-Tools CP-SAT Solver
    │
    ├─► Create Variables (start, end, interval)
    ├─► Add Constraints (precedence, no-overlap)
    ├─► Set Objective (minimize makespan)
    └─► Solve
    │
    ▼
Integer Solution (Business Hours)
    │
    ▼
Time Projection (_project_business_hours)
    │
    ▼
Real Calendar Dates
    │
    ▼
ScheduledTask[] Objects
    │
    ▼
Save to state.json
    │
    ▼
Gantt Chart Visualization
```

### 3. Chat Update Flow

```
User Message (Natural Language)
    │
    ▼
Gemini 3 Flash
    │
    ▼
Intent Classification
    │
    ├─► add_task
    ├─► update_task
    ├─► add_resource
    └─► clarify
    │
    ▼
State Mutation
    │
    ▼
Auto Re-schedule (if needed)
    │
    ▼
Updated UI
```

## Key Components

### 1. Streamlit UI (`app.py`)

**Responsibilities:**
- User input handling
- State visualization
- Tab-based navigation
- Real-time updates

**Key Features:**
- Requirements tab: Text input + AI parsing
- Schedule tab: Gantt chart + task list
- Chat tab: Natural language updates
- Manual tab: Direct task CRUD

### 2. Gemini Brain (`core/brain.py`)

**Class: `GeminiBrain`**

**Methods:**
- `parse_requirements(text, resources)` → Task[]
  - Uses Gemini 3 Pro
  - Prompt engineered for JSON extraction
  - Handles task breakdown, dependency inference
  
- `interpret_chat(message, state)` → Action
  - Uses Gemini 3 Flash
  - Returns structured action object
  - Supports add/update/delete operations
  
- `generate_summary(schedule)` → str
  - Uses Gemini 3 Flash
  - Creates executive summary

**Prompt Engineering:**
- Clear output format specification
- Role-based system prompts
- JSON schema enforcement
- Example-driven learning

### 3. Scheduler Engine (`core/scheduler.py`)

**Class: `SchedulerEngine`**

**Methods:**
- `solve()` → ScheduledTask[]
  - Main scheduling algorithm
  - Returns fully computed schedule
  
- `_validate_dag()`
  - Uses NetworkX to check for cycles
  - Raises error if circular dependency found
  
- `_project_business_hours(offset)` → datetime
  - Converts integer hours to real dates
  - Skips weekends and non-work hours

**Constraints Implemented:**

1. **Precedence Constraint:**
   ```python
   model.Add(task_starts[T_dependent] >= task_ends[T_dependency])
   ```
   
2. **No Overlap Constraint:**
   ```python
   model.AddNoOverlap(intervals_for_resource)
   ```
   
3. **Business Hours:**
   - Handled in time projection, not in solver
   - Keeps solver fast (linear time complexity)

**Optimization Objective:**
```python
makespan = max(all_task_end_times)
model.Minimize(makespan)
```

### 4. Data Models (`core/models.py`)

**Pydantic Models:**

```python
class Resource:
    id: str
    name: str
    role: str

class Task:
    id: str
    name: str
    duration_hours: int
    dependencies: List[str]
    assigned_to: Optional[str]
    priority: int

class ScheduledTask:
    task_id: str
    task_name: str
    resource_id: str
    resource_name: str
    start_datetime: str  # ISO format
    end_datetime: str    # ISO format

class ProjectState:
    tasks: List[Task]
    resources: List[Resource]
    project_start_date: str
    schedule: List[ScheduledTask]
```

**Why Pydantic?**
- Type validation at runtime
- Automatic serialization/deserialization
- Clear contract between components
- IDE autocomplete support

### 5. Time Utilities (`utils/time_utils.py`)

**Functions:**
- `is_business_day(date)` → bool
- `get_next_business_day(date)` → datetime
- `format_duration(hours)` → str
- `parse_date(date_str)` → datetime

## Design Decisions

### Why Neuro-Symbolic?

**Problem with Pure AI:**
- LLMs hallucinate dates
- Can't guarantee constraint satisfaction
- Unpredictable edge case handling
- No mathematical optimality

**Problem with Pure Code:**
- Can't parse natural language
- Requires structured input
- Poor user experience
- Brittle to changes

**Solution: Combine Both:**
- AI handles ambiguity (requirement parsing)
- Math handles precision (scheduling)
- Get best of both worlds

### Why OR-Tools over Simple Greedy?

**Greedy Approach:**
```python
for task in sorted_tasks:
    assign_to_first_available_resource()
```

**Problems:**
- Not optimal
- Can't backtrack
- Ignores global constraints
- Poor resource utilization

**OR-Tools Approach:**
- Explores solution space intelligently
- Guarantees optimality (or near-optimal)
- Handles complex constraints
- Industry-standard solver

### The Weekend Skipping Strategy

**Naive Approach:**
```python
# Add to solver: task_start % 168 not in weekend_hours
```
**Problem:** Exponentially slow for many tasks

**Our Approach:**
1. Solver works in abstract "business hours"
2. Post-processing maps to calendar
3. Fast solver + accurate dates

**Implementation:**
```python
def _project_business_hours(self, hour_offset: int) -> datetime:
    current = self.start_datetime
    hours_remaining = hour_offset
    
    while hours_remaining > 0:
        # Skip to next valid hour
        if is_weekend(current) or not is_work_hour(current):
            current = next_valid_hour(current)
            continue
        
        # Consume one business hour
        current += timedelta(hours=1)
        hours_remaining -= 1
    
    return current
```

### State Management: Why JSON?

**Alternatives Considered:**
- SQLite: Overkill for MVP
- PostgreSQL: Requires server
- MongoDB: Unnecessary complexity

**JSON Benefits:**
- Zero setup
- Human readable
- Git-friendly
- Easy debugging
- Fast for small datasets (<1000 tasks)

**When to Migrate:**
- Multi-user scenarios
- Concurrent editing
- Large projects (>1000 tasks)
- Audit trail requirements

## Performance Characteristics

### Scheduler Complexity

- **Time:** O(n log n) for n tasks (typical)
- **Space:** O(n) 
- **Solver timeout:** 30 seconds (configurable)

### Gemini API Latency

- **Parsing:** 5-15 seconds (Gemini 3 Pro)
- **Chat:** 1-3 seconds (Gemini 3 Flash)
- **Rate limits:** 2 RPM (Pro), 15 RPM (Flash)

### Scaling Considerations

**Current Limits:**
- Tasks: ~500 (OR-Tools solver time)
- Resources: ~50
- Projects: 1 (single state.json)

**To Scale Up:**
1. Implement caching for Gemini calls
2. Use database instead of JSON
3. Add async task processing
4. Implement project partitioning

## Security Considerations

### API Key Protection

**Current:**
- Stored in `.env` file
- Not committed to git
- Loaded via python-dotenv

**Production:**
- Use secret manager (AWS Secrets, GCP Secret Manager)
- Implement key rotation
- Add usage quotas per user

### Input Validation

**Current:**
- Pydantic model validation
- Basic type checking

**Production:**
- SQL injection prevention (if using DB)
- XSS protection (if web-exposed)
- Rate limiting on AI calls
- Input sanitization

## Extension Points

### Adding Custom Constraints

Edit `core/scheduler.py`:
```python
# Example: Max 3 tasks per person per day
for resource in resources:
    tasks_per_day = group_tasks_by_day(resource)
    for day, tasks in tasks_per_day:
        model.Add(len(tasks) <= 3)
```

### Custom AI Prompts

Edit `core/brain.py`:
```python
def parse_requirements(self, text, resources):
    custom_prompt = f"""
    You are an expert project manager specializing in {domain}.
    
    Parse the following requirements with focus on {aspect}:
    {text}
    
    Return JSON with additional field '{custom_field}'.
    """
    # Rest of implementation
```

### Adding New Visualizations

Edit `app.py`:
```python
def create_custom_chart(schedule):
    import plotly.graph_objects as go
    
    # Custom visualization logic
    fig = go.Figure(...)
    return fig

# In Streamlit tab:
st.plotly_chart(create_custom_chart(schedule))
```

## Testing Strategy

### Unit Tests

```python
# Test scheduler in isolation
def test_simple_schedule():
    tasks = [Task(...)]
    resources = [Resource(...)]
    scheduler = SchedulerEngine(tasks, resources, "2024-01-01")
    result = scheduler.solve()
    assert len(result) == len(tasks)

# Test time projection
def test_weekend_skip():
    date = datetime(2024, 1, 5, 17, 0)  # Friday 5 PM
    next_hour = project_business_hours(date, 1)
    assert next_hour.weekday() == 0  # Monday
    assert next_hour.hour == 9  # 9 AM
```

### Integration Tests

```python
# Test full flow
def test_end_to_end():
    # Parse requirements
    brain = GeminiBrain(api_key)
    tasks = brain.parse_requirements(text, resources)
    
    # Schedule
    scheduler = SchedulerEngine(tasks, resources, "2024-01-01")
    schedule = scheduler.solve()
    
    # Verify
    assert all(task.start_datetime < task.end_datetime for task in schedule)
```

## Conclusion

Gemini PM demonstrates how combining AI (neural) with mathematical solvers (symbolic) creates a more reliable and capable system than either approach alone.

The architecture is designed for:
- **Clarity:** Each component has a single responsibility
- **Extensibility:** Easy to add new features
- **Reliability:** Deterministic where it matters
- **Usability:** Natural language interface

This pattern can be applied to many domains where you need both flexibility and precision.
