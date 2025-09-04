@echo off
echo Setting up Reddit-to-TikTok Generator...
echo.

REM Navigate to the project directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    py -m venv venv
    echo Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Navigate to backend directory
cd thread-2-tok\backend

REM Install/update dependencies
echo Installing dependencies...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install edge-tts python-dotenv pillow

echo.
echo Setup complete! You can now run the app using run_app.bat
echo.
pause