"""
Test script to validate the Gemini PM installation and core functionality.
Run this before using the full application to ensure everything works.
"""

import sys
import json
from datetime import datetime

def test_imports():
    """Test that all required packages are installed."""
    print("Testing package imports...")
    try:
        import streamlit
        print("✓ Streamlit installed")
    except ImportError:
        print("✗ Streamlit not found. Run: pip install streamlit")
        return False
    
    try:
        import google.generativeai
        print("✓ Google Generative AI installed")
    except ImportError:
        print("✗ google-generativeai not found. Run: pip install google-generativeai")
        return False
    
    try:
        import ortools
        print("✓ OR-Tools installed")
    except ImportError:
        print("✗ OR-Tools not found. Run: pip install ortools")
        return False
    
    try:
        import networkx
        print("✓ NetworkX installed")
    except ImportError:
        print("✗ NetworkX not found. Run: pip install networkx")
        return False
    
    try:
        import pydantic
        print("✓ Pydantic installed")
    except ImportError:
        print("✗ Pydantic not found. Run: pip install pydantic")
        return False
    
    try:
        import pandas
        print("✓ Pandas installed")
    except ImportError:
        print("✗ Pandas not found. Run: pip install pandas")
        return False
    
    try:
        import plotly
        print("✓ Plotly installed")
    except ImportError:
        print("✗ Plotly not found. Run: pip install plotly")
        return False
    
    print("\n✓ All packages installed successfully!\n")
    return True

def test_core_modules():
    """Test that core modules can be imported."""
    print("Testing core modules...")
    try:
        from core.models import Task, Resource, ScheduledTask, ProjectState
        print("✓ Models module working")
    except ImportError as e:
        print(f"✗ Models module failed: {e}")
        return False
    
    try:
        from core.scheduler import SchedulerEngine
        print("✓ Scheduler module working")
    except ImportError as e:
        print(f"✗ Scheduler module failed: {e}")
        return False
    
    try:
        from utils.time_utils import format_duration, is_business_day
        print("✓ Time utils module working")
    except ImportError as e:
        print(f"✗ Time utils module failed: {e}")
        return False
    
    print("\n✓ All core modules loaded successfully!\n")
    return True

def test_scheduler():
    """Test the scheduler with sample data."""
    print("Testing scheduler engine...")
    try:
        from core.models import Task, Resource
        from core.scheduler import SchedulerEngine
        
        # Create test resources
        resources = [
            Resource(id="R1", name="Alice", role="Developer"),
            Resource(id="R2", name="Bob", role="Developer")
        ]
        
        # Create test tasks
        tasks = [
            Task(id="T1", name="Setup", duration_hours=8, dependencies=[], assigned_to="R1", priority=1),
            Task(id="T2", name="Development", duration_hours=16, dependencies=["T1"], assigned_to="R1", priority=1),
            Task(id="T3", name="Testing", duration_hours=8, dependencies=["T2"], assigned_to="R2", priority=1)
        ]
        
        # Run scheduler
        scheduler = SchedulerEngine(tasks, resources, "2024-03-04")
        schedule = scheduler.solve()
        
        if len(schedule) == 3:
            print(f"✓ Scheduler created schedule with {len(schedule)} tasks")
            print(f"  First task starts: {schedule[0].start_datetime}")
            print(f"  Last task ends: {schedule[-1].end_datetime}")
        else:
            print("✗ Scheduler didn't create expected number of tasks")
            return False
        
    except Exception as e:
        print(f"✗ Scheduler test failed: {e}")
        return False
    
    print("\n✓ Scheduler working correctly!\n")
    return True

def test_data_models():
    """Test Pydantic data models."""
    print("Testing data models...")
    try:
        from core.models import Task, Resource, ProjectState
        
        # Create test objects
        resource = Resource(id="R1", name="Test User", role="Developer")
        task = Task(
            id="T1",
            name="Test Task",
            duration_hours=8,
            dependencies=[],
            assigned_to="R1",
            priority=1
        )
        state = ProjectState(
            tasks=[task],
            resources=[resource],
            project_start_date="2024-03-04",
            schedule=[]
        )
        
        # Test serialization
        state_dict = state.model_dump()
        if state_dict['tasks'][0]['name'] == 'Test Task':
            print("✓ Data models working correctly")
        else:
            print("✗ Data model serialization failed")
            return False
        
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        return False
    
    print("\n✓ Data models validated!\n")
    return True

def test_env_file():
    """Check if .env file exists and has API key."""
    print("Testing environment configuration...")
    try:
        from dotenv import load_dotenv
        import os
        
        if not os.path.exists('.env'):
            print("⚠ Warning: .env file not found")
            print("  Copy .env.example to .env and add your Gemini API key")
            return True  # Not a critical failure
        
        load_dotenv()
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key or api_key == 'your_api_key_here':
            print("⚠ Warning: GEMINI_API_KEY not set in .env")
            print("  Add your API key to use AI features")
            print("  Get key from: https://makersuite.google.com/app/apikey")
            return True  # Not a critical failure
        
        print(f"✓ API key found (length: {len(api_key)} characters)")
        
    except Exception as e:
        print(f"⚠ Environment test warning: {e}")
        return True  # Not critical
    
    print("\n✓ Environment configured!\n")
    return True

def test_state_file():
    """Check if state.json exists and is valid."""
    print("Testing state file...")
    try:
        with open('state.json', 'r') as f:
            state_data = json.load(f)
        
        required_keys = ['tasks', 'resources', 'project_start_date', 'schedule']
        if all(key in state_data for key in required_keys):
            print("✓ state.json is valid")
        else:
            print("✗ state.json missing required keys")
            return False
        
    except FileNotFoundError:
        print("✗ state.json not found")
        return False
    except json.JSONDecodeError:
        print("✗ state.json is not valid JSON")
        return False
    except Exception as e:
        print(f"✗ State file test failed: {e}")
        return False
    
    print("\n✓ State file validated!\n")
    return True

def run_all_tests():
    """Run all validation tests."""
    print("="*60)
    print("GEMINI PM - Installation Validation")
    print("="*60)
    print()
    
    tests = [
        ("Package Imports", test_imports),
        ("Core Modules", test_core_modules),
        ("Data Models", test_data_models),
        ("State File", test_state_file),
        ("Scheduler Engine", test_scheduler),
        ("Environment Config", test_env_file),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}\n")
            results.append((name, False))
    
    print("="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {name}")
    
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    if passed == total:
        print(f"✓ All {total} tests passed! You're ready to use Gemini PM.")
        print("\nNext steps:")
        print("1. Make sure your .env file has a valid GEMINI_API_KEY")
        print("2. Run: streamlit run app.py")
        print("3. Open http://localhost:8501 in your browser")
        return True
    else:
        print(f"✗ {total - passed} of {total} tests failed.")
        print("\nPlease fix the issues above before running the application.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
