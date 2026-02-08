---
title: Gemini Advanced PM
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.31.0
app_file: app.py
pinned: false
---

# Gemini Advanced PM
Your project description goes here.

# 🤖 Gemini PM - AI-Powered Project Manager

An autonomous Project Management agent that uses **Neuro-Symbolic AI** architecture: combining Google Gemini (AI reasoning) with Google OR-Tools (mathematical optimization) to intelligently parse requirements and optimally schedule tasks.

## 🎯 What Makes This Special?

Unlike typical AI tools that just generate text, Gemini PM uses a **hybrid approach**:

- **The Brain (AI)**: Gemini 1.5 understands messy, unstructured requirements
- **The Hands (Math)**: OR-Tools creates mathematically optimal schedules that respect real-world constraints

This separation ensures you get:
- ✅ Realistic schedules (no AI hallucination on dates)
- ✅ Weekend-aware timelines (automatically skips Sat/Sun)
- ✅ Resource conflict resolution (no person does two things at once)
- ✅ Dependency validation (circular dependencies detected)

## 🏗️ Architecture

```
┌─────────────────────┐
│   User Input        │
│  (Natural Language) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Gemini 1.5 Pro     │  ◄── Parsing & Understanding
│  (brain.py)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Pydantic Models    │  ◄── Structured Data Contract
│  (models.py)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  OR-Tools CP-SAT    │  ◄── Mathematical Optimization
│  (scheduler.py)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Gantt Chart        │  ◄── Visual Timeline
│  (Streamlit UI)     │
└─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone or download this project**

```bash
cd gemini-pm
```

2. **Create a virtual environment** (recommended)

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up your API key**

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_actual_api_key_here
```

5. **Run the application**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📖 How to Use

### Step 1: Add Team Members

In the sidebar, add your team members with their roles (e.g., Frontend, Backend, Designer).

### Step 2: Parse Requirements

Go to the **Requirements** tab and paste your project description:

```
Build a web app with:
- User authentication (login/register)
- Dashboard with analytics
- REST API for mobile app
- Database schema design
- Deployment to AWS

Frontend: React
Backend: Python FastAPI
Timeline: ASAP
```

Click **"🧠 Parse with AI"** - Gemini will convert this into structured tasks.

### Step 3: Generate Schedule

Click **"📅 Generate Schedule"** - OR-Tools will create an optimal timeline that:
- Respects task dependencies
- Prevents resource conflicts
- Skips weekends automatically
- Minimizes project duration

### Step 4: View Timeline

Switch to the **Schedule** tab to see:
- Interactive Gantt chart
- Task details table
- Project metrics (duration, task count)
- AI-generated summary

### Step 5: Make Changes (Optional)

Use the **Chat** tab to make natural language updates:
- "John is sick tomorrow, reassign his tasks"
- "Add a task for performance testing"
- "Task T3 will take 3 more days"

## 🧠 Core Features

### 1. AI-Powered Requirement Parsing
- Paste unstructured project descriptions
- Gemini extracts tasks, dependencies, and assignments
- Automatically estimates durations

### 2. Mathematical Scheduling
- Google OR-Tools CP-SAT solver
- Constraints:
  - **Precedence**: Task B starts only after Task A finishes
  - **No Overlap**: One person, one task at a time
  - **Business Hours**: 9 AM - 5 PM, Monday-Friday only
- Objective: Minimize project completion time

### 3. Weekend-Aware Calendar
- The scheduler automatically skips weekends
- Handles edge cases (task ending Friday 5 PM → next task starts Monday 9 AM)

### 4. Dependency Validation
- Uses NetworkX to detect circular dependencies
- Prevents invalid project logic (Task A waits for B, B waits for A)

### 5. Interactive Chat
- Natural language project updates
- Add/modify tasks on the fly
- Dynamic rescheduling

## 📁 Project Structure

```
gemini-pm/
│
├── app.py                 # Streamlit UI (Frontend)
├── requirements.txt       # Python dependencies
├── state.json             # Project state persistence
├── .env                   # API keys (create from .env.example)
│
├── core/
│   ├── models.py          # Pydantic data models (Task, Resource, etc.)
│   ├── scheduler.py       # OR-Tools optimization engine
│   └── brain.py           # Gemini API integration
│
└── utils/
    └── time_utils.py      # Date/time helper functions
```

## 🔧 Technical Details

### Why Neuro-Symbolic?

Traditional approaches fail because:
- **Pure AI**: Hallucinates dates, ignores constraints, unreliable math
- **Pure Code**: Can't parse natural language, requires manual task input

This hybrid approach:
- Uses AI where it excels (language understanding)
- Uses math where it excels (constraint satisfaction)
- Gets the best of both worlds

### The Weekend Problem

Challenge: How do you schedule "40 hours of work" realistically?

**Bad approach**: Add modulo constraints to the solver (makes it exponentially slow)

**Our approach**: 
1. Solver works in abstract "business hours" (Hour 0, Hour 1, Hour 2...)
2. After solving, we project onto a real calendar using `_project_business_hours()`
3. This function skips weekends and off-hours efficiently

### Models Used

- **Gemini 1.5 Pro**: Requirements parsing (slower, more accurate)
- **Gemini 1.5 Flash**: Chat interface (faster, cheaper)
- **OR-Tools CP-SAT**: Constraint programming solver

## 🎓 Example Use Cases

1. **Software Development Projects**
   - Parse sprint requirements
   - Auto-assign to developers
   - Respect skill sets (frontend/backend)

2. **Event Planning**
   - Break down event tasks
   - Schedule across multiple team members
   - Ensure dependencies (venue before catering)

3. **Research Projects**
   - Literature review → Experimentation → Writing
   - Assign to research team members
   - Optimize for publication deadlines

## 🐛 Troubleshooting

### "No module named 'google.generativeai'"
```bash
pip install --upgrade google-generativeai
```

### "Solver failed"
- Check for circular dependencies in your tasks
- Ensure all tasks have assigned resources
- Verify task durations are reasonable

### Gantt chart not displaying
- Make sure you've clicked "Generate Schedule"
- Check that tasks have start/end dates
- Refresh the page

## 🚧 Future Enhancements

- [ ] Export to Microsoft Project / Jira
- [ ] Custom availability windows per resource
- [ ] Multi-project portfolio management
- [ ] Risk analysis and buffer time
- [ ] Cost optimization
- [ ] Integration with Calendar APIs

## 📝 License

This is an educational project demonstrating Neuro-Symbolic AI architecture.

## 🙏 Credits

- **Google Gemini**: AI reasoning and parsing
- **Google OR-Tools**: Mathematical optimization
- **Streamlit**: Rapid UI development
- **NetworkX**: Graph algorithms for dependency validation

## 📞 Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the code comments (heavily documented)
3. Test with simple examples first

---

**Built with ❤️ using Neuro-Symbolic AI**

*Combining the creativity of Large Language Models with the precision of Mathematical Solvers*
