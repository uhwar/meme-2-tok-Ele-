#!/usr/bin/env python3
"""
TikTok Video Generator Launcher
Simple launcher that runs the main app with proper error handling
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def print_header():
    print("\n" + "="*50)
    print("    🎬 TikTok Video Generator")
    print("="*50)
    print()

def print_status(message, status="info"):
    icons = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}
    icon = icons.get(status, "•")
    print(f"{icon} {message}")

def main():
    print_header()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print_status("Starting TikTok video generation...")
    print_status("• Fetching fresh Reddit story")
    print_status("• Creating TikTok voice narration") 
    print_status("• Adding lofi background music")
    print_status("• Generating captions with Impact font")
    print_status("• Rendering video for TikTok")
    print()
    
    try:
        # Run the main app
        result = subprocess.run([sys.executable, "app.py"], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print()
            print("="*50)
            print_status("Video Generation Complete!", "success")
            print("="*50)
            print()
            
            # Find and open the most recent MP4 file
            mp4_files = list(Path(".").glob("*.mp4"))
            if mp4_files:
                latest_video = max(mp4_files, key=lambda p: p.stat().st_mtime)
                print_status(f"Video created: {latest_video.name}", "success")
                print_status("Opening video...", "info")
                
                # Open the video with default player
                if os.name == 'nt':  # Windows
                    os.startfile(latest_video)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', 
                                  str(latest_video)])
                
                # Show file details
                file_size = latest_video.stat().st_size / (1024 * 1024)  # MB
                print()
                print_status("Video Details:", "info")
                print(f"   • File: {latest_video.name}")
                print(f"   • Size: {file_size:.2f} MB")
                print(f"   • Location: {latest_video.absolute()}")
                
            else:
                print_status("No video files found", "warning")
                
        else:
            print_status("Video generation failed", "error")
            
    except FileNotFoundError:
        print_status("Error: app.py not found in current directory", "error")
    except Exception as e:
        print_status(f"Error: {str(e)}", "error")
    
    print()
    print_status("Your video is ready to upload to TikTok!", "success")
    print()
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()