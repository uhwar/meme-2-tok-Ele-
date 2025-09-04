@echo off
title Reddit-to-TikTok Generator
color 0A

echo.
echo  ██████╗ ███████╗██████╗ ██████╗ ██╗████████╗    ████████╗ ██████╗     ████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗
echo  ██╔══██╗██╔════╝██╔══██╗██╔══██╗██║╚══██╔══╝    ╚══██╔══╝██╔═══██╗    ╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝
echo  ██████╔╝█████╗  ██║  ██║██║  ██║██║   ██║          ██║   ██║   ██║       ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝ 
echo  ██╔══██╗██╔══╝  ██║  ██║██║  ██║██║   ██║          ██║   ██║   ██║       ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗ 
echo  ██║  ██║███████╗██████╔╝██████╔╝██║   ██║          ██║   ╚██████╔╝       ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗
echo  ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═════╝ ╚═╝   ╚═╝          ╚═╝    ╚═════╝        ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
echo.
echo                                    🎬 AITA Story to TikTok Video Generator 🎬
echo.
echo  ✅ Fetches stories from r/AmItheAsshole
echo  ✅ Interactive story approval system  
echo  ✅ TikTok-style videos with captions
echo  ✅ Automatic blacklisting of rejected stories
echo.

REM Navigate to the project directory
cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Navigate to backend directory
cd thread-2-tok\backend

REM Run the app
py app.py

REM Keep window open
echo.
echo Press any key to exit...
pause >nul