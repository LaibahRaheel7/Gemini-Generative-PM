# Calendar Streamlit Component

A custom Streamlit component that provides an interactive calendar (react-big-calendar) with week, month, day, and agenda views.

## Development Setup

1. Install dependencies:
```bash
cd components/frontend
npm install
```

2. Start development server:
```bash
npm start
```

3. In `fullcalendar_component.py`, set `_RELEASE = False` to use dev server.

## Building for Production

```bash
cd components/frontend
npm install
npm run build
```

This creates `components/frontend/build`. The Streamlit app uses it automatically when present.

## Usage

```python
from components import render_resource_gantt

clicked_event = render_resource_gantt(
    schedule=scheduled_tasks,
    resources=team_resources,
    view="resourceTimelineWeek",  # maps to week view
    initial_date="2024-03-01"
)

if clicked_event:
    st.write(f"Clicked task: {clicked_event['event']['title']}")
```

## Features

- Week, month, day, and agenda views (react-big-calendar)
- View names like `resourceTimelineWeek` / `dayGridMonth` map to week/month/day/agenda
- Interactive event clicking
- Color-coded events (e.g. by project)
- Simple build (no CRACO or ajv patches)
