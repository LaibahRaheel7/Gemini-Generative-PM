@echo off
echo ========================================
echo   Gemini PM - AI Project Manager
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env and add your Gemini API key!
    echo Get your key from: https://makersuite.google.com/app/apikey
    echo.
    pause
)

REM Run the app
echo Starting Gemini PM...
echo.
streamlit run app.py

pause
