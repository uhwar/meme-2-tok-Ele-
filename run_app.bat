@echo off
echo Starting Reddit-to-TikTok Generator...
echo.

REM Navigate to the project directory
cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Navigate to backend directory
cd thread-2-tok\backend

REM Run the app
echo Starting the app...
echo.
py app.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
)