# Complete Setup Guide for Gemini PM

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Getting Your API Key](#getting-your-api-key)
4. [Running the Application](#running-the-application)
5. [First-Time Setup](#first-time-setup)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Python**: Version 3.10 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 500MB for dependencies
- **Internet**: Required for Gemini API calls

### Check Your Python Version

Open a terminal/command prompt and run:
```bash
python --version
# or
python3 --version
```

You should see `Python 3.10.x` or higher.

---

## Installation

### Option 1: Using Quick Start Scripts (Recommended)

#### On Windows:
1. Extract the `gemini-pm` folder
2. Double-click `start.bat`
3. The script will:
   - Create a virtual environment
   - Install all dependencies
   - Create a `.env` file
   - Launch the application

#### On Mac/Linux:
1. Extract the `gemini-pm` folder
2. Open Terminal and navigate to the folder:
   ```bash
   cd path/to/gemini-pm
   ```
3. Run the start script:
   ```bash
   ./start.sh
   ```
4. The script will handle everything automatically

### Option 2: Manual Installation

#### Step 1: Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Configure Environment
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key
# On Windows: notepad .env
# On Mac: nano .env
# On Linux: nano .env
```

#### Step 4: Run the Application
```bash
streamlit run app.py
```

---

## Getting Your API Key

Gemini PM requires a Google Gemini API key to function.

### Steps to Get Your Key:

1. **Visit Google AI Studio**
   - Go to: https://makersuite.google.com/app/apikey
   
2. **Sign In**
   - Use your Google account
   
3. **Create API Key**
   - Click "Create API Key"
   - Choose "Create API key in new project" (or select existing project)
   - Copy the generated key
   
4. **Add to .env File**
   - Open the `.env` file in your `gemini-pm` folder
   - Replace `your_api_key_here` with your actual key:
   ```
   GEMINI_API_KEY=AIzaSyC...your_actual_key_here
   ```
   - Save the file

### API Key Best Practices:

- ⚠️ **Never share your API key publicly**
- ⚠️ **Don't commit .env to version control** (already in .gitignore)
- 💡 Keep it in a secure password manager
- 💡 Regenerate if accidentally exposed

### Free Tier Limits:

- Gemini 3 Flash: 15 requests per minute, 1 million tokens per day
- Gemini 3 Pro: 2 requests per minute, 32,000 tokens per day

For most project management use cases, the free tier is sufficient.

---

## Running the Application

### First Time:

1. **Start the application**
   - Windows: Double-click `start.bat`
   - Mac/Linux: Run `./start.sh` in terminal
   
2. **Browser opens automatically**
   - If not, go to: http://localhost:8501
   
3. **You'll see the Gemini PM interface**

### Subsequent Uses:

Just run the start script again, or manually:
```bash
# Activate virtual environment
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Run app
streamlit run app.py
```

---

## First-Time Setup

### Step 1: Add Team Members

1. In the **sidebar**, find "👥 Team Members"
2. Click "Add New Member"
3. Fill in:
   - **ID**: Unique identifier (e.g., R1, R2)
   - **Name**: Person's name
   - **Role**: Their expertise (Frontend, Backend, etc.)
4. Click "Add Member"

Example team:
- R1 | John Smith | Full-Stack
- R2 | Sarah Lee | Frontend
- R3 | Mike Chen | Backend
- R4 | Lisa Wong | DevOps

### Step 2: Set Project Start Date

1. In the sidebar, find "Project Start Date"
2. Select your project start date
3. Click "Update Start Date"

### Step 3: Parse Requirements

1. Go to the **"📋 Requirements"** tab
2. Paste your project description (see EXAMPLES.md)
3. Click **"🧠 Parse with AI"**
4. Wait 5-10 seconds while Gemini analyzes
5. Review the parsed tasks

### Step 4: Generate Schedule

1. Click **"📅 Generate Schedule"**
2. Wait for OR-Tools to optimize
3. View your schedule in the **"📊 Schedule"** tab

---

## Troubleshooting

### Problem: "Module not found" errors

**Solution:**
```bash
# Make sure virtual environment is activated
# You should see (venv) in your terminal prompt

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Problem: "Invalid API Key" or "401 Unauthorized"

**Solution:**
1. Check `.env` file exists in the `gemini-pm` folder
2. Verify your API key is correct (no extra spaces)
3. Test your key at: https://makersuite.google.com/
4. Regenerate if necessary

### Problem: Streamlit won't start

**Solution:**
```bash
# Check if port 8501 is in use
# Kill any running Streamlit instances

# On Windows:
taskkill /F /IM streamlit.exe

# On Mac/Linux:
pkill -f streamlit

# Then restart
streamlit run app.py
```

### Problem: Schedule generation fails

**Solution:**
1. **Check for circular dependencies**
   - Task A depends on B, B depends on A
   - The system will show an error message
   
2. **Ensure tasks are assigned**
   - All tasks need a resource (team member)
   - Add team members first
   
3. **Verify task durations are reasonable**
   - Don't set 1000-hour tasks
   - Keep it under 160 hours (1 month) per task

### Problem: Gantt chart not showing

**Solution:**
1. Make sure you clicked "Generate Schedule"
2. Check that state.json has schedule data
3. Refresh the browser (F5)
4. Check browser console for errors (F12)

### Problem: Slow parsing

**Solution:**
- Gemini Pro can take 10-30 seconds for complex requirements
- This is normal for the first call (API cold start)
- Be patient, don't click multiple times
- Consider breaking very large requirements into smaller chunks

### Problem: "Rate limit exceeded"

**Solution:**
- You've hit Gemini API free tier limits
- Wait 1 minute and try again
- Reduce frequency of AI calls
- Consider upgrading to paid tier for production use

---

## Advanced Configuration

### Changing Work Hours

Edit `core/scheduler.py`:
```python
self.work_start_hour = 9   # Change to 8 for 8 AM start
self.work_end_hour = 17    # Change to 18 for 6 PM end
```

### Changing Solver Timeout

Edit `core/scheduler.py`:
```python
solver.parameters.max_time_in_seconds = 30.0  # Increase for complex projects
```

### Using Different Gemini Models

Edit `core/brain.py`:
```python
# For faster (less accurate) parsing
self.parser_model = genai.GenerativeModel('gemini-3-flash-preview')

# For highest quality
self.parser_model = genai.GenerativeModel('gemini-3-pro-preview')
```

---

## Getting Help

### Resources:
1. **README.md** - Full documentation
2. **EXAMPLES.md** - Sample project requirements
3. **Code comments** - Heavily documented
4. **Google Gemini Docs**: https://ai.google.dev/docs

### Common Questions:

**Q: Is this free?**
A: Yes, for the Gemini API free tier. You get plenty of quota for personal projects.

**Q: Can I use this commercially?**
A: Yes, but be aware of Gemini API usage limits and costs for production use.

**Q: Does it work offline?**
A: No, it requires internet for Gemini API calls. The scheduler itself is offline.

**Q: How accurate is the schedule?**
A: Very accurate mathematically. It's optimal given your constraints. However, task duration estimates depend on your input.

**Q: Can I export to MS Project / Jira?**
A: Not yet, but you can export the data from state.json and convert it.

---

## Next Steps

Once everything is working:
1. Try the sample requirements in EXAMPLES.md
2. Test with your own project
3. Explore the Chat feature for dynamic updates
4. Customize the code to fit your workflow

**Enjoy building with Gemini PM! 🚀**
