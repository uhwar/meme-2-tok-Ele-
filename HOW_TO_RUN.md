# 🎬 Reddit-to-TikTok Generator - Quick Start Guide

## 🚀 Easy Launch Options

### Option 1: Double-Click Launch (Recommended)
Simply double-click: **`🎬 Start Reddit-to-TikTok Generator.bat`**
- Beautiful startup screen
- Automatically activates virtual environment
- Runs the app with interactive story approval

### Option 2: Simple Launch
Double-click: **`run_app.bat`**
- Clean, simple startup
- Activates venv and runs the app

### Option 3: PowerShell Launch
Right-click **`run_app.ps1`** → "Run with PowerShell"
- PowerShell version with colored output

## 🛠️ First Time Setup

If you're running this for the first time or need to install dependencies:

1. Double-click **`setup.bat`**
2. Wait for it to create the virtual environment and install all dependencies
3. Then use any of the launch options above

## 📋 How the App Works

1. **Story Fetching**: Automatically fetches fresh stories from r/AmItheAsshole
2. **Preview & Approval**: Shows you a preview of each story with:
   - Title and content preview
   - Score and comment count
   - Estimated video duration
3. **Interactive Choice**:
   - `y` or `yes` → Create video with this story
   - `n` or `no` → Reject and blacklist this story forever
   - `q` or `quit` → Exit the program
4. **Video Generation**: Creates TikTok-style video with:
   - TikTok TTS narration
   - Centered captions with Impact font
   - Background music
   - 9:16 aspect ratio

## 📁 Output Files

Generated videos are saved in: `thread-2-tok/backend/`
- Format: `story_title.mp4`
- Ready to upload to TikTok!

## 🚫 Blacklist System

- Rejected stories are permanently blacklisted
- Stored in: `blacklisted_stories.json`
- You'll never see the same rejected story again

## ⚙️ Requirements

- Python (accessible via `py` command)
- Virtual environment (created automatically by setup.bat)
- Reddit API credentials (already configured in .env)

---

**Tip**: Use the emoji launcher (`🎬 Start Reddit-to-TikTok Generator.bat`) for the best experience!