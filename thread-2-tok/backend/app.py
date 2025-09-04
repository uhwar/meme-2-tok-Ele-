from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import praw  # Python Reddit Wrapper
import edge_tts
import asyncio
from tiktok_voice_api import TikTokTTS
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, CompositeAudioClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap
from dotenv import load_dotenv
import os
import random
import json
import time

# Load environment variables
load_dotenv()

# Files to track used content to avoid repeats
USED_STORIES_FILE = "used_stories.json"
LAST_VOICE_FILE = "last_voice.json"
BLACKLISTED_STORIES_FILE = "blacklisted_stories.json"

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching
CORS(app)  # Enable Cross-Origin Resource Sharing for React

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    user_agent="thread-2-tok/0.1 by u/Complex_Balance4016"
)

def select_quality_weighted_story(posts):
    """Select a story using quality-weighted random selection."""
    if not posts:
        return None
    
    # Sort posts by score for analysis
    sorted_posts = sorted(posts, key=lambda p: p.score, reverse=True)
    
    # Show score distribution
    scores = [p.score for p in sorted_posts]
    if scores:
        print(f"  📊 Score range: {min(scores)} - {max(scores)} (avg: {sum(scores)//len(scores)})")
        
        # Show top scores for reference
        top_5_scores = scores[:5] if len(scores) >= 5 else scores
        print(f"  🏆 Top scores available: {top_5_scores}")
    
    # Create weighted selection based on score
    # Higher scores get exponentially higher weights
    weights = []
    for post in posts:
        score = post.score
        
        # Weight calculation: heavily favor high scores
        if score >= 100:
            weight = score * 3  # 3x weight for 100+ scores
        elif score >= 50:
            weight = score * 2  # 2x weight for 50+ scores
        elif score >= 20:
            weight = score * 1.5  # 1.5x weight for 20+ scores
        else:
            weight = score  # Normal weight for lower scores
        
        weights.append(weight)
    
    # Weighted random selection
    selected_post = random.choices(posts, weights=weights)[0]
    
    # Show selection info
    total_weight = sum(weights)
    selected_weight = weights[posts.index(selected_post)]
    selection_probability = (selected_weight / total_weight) * 100
    
    print(f"  🎯 Selected post with score {selected_post.score} ({selection_probability:.1f}% selection probability)")
    
    return selected_post

# Helper function to fetch a Reddit story from multiple subreddits
def get_subreddit_selection():
    """Ask user to choose which subreddit path to use."""
    print("\n" + "="*70)
    print("🎬 REDDIT-TO-TIKTOK GENERATOR - SUBREDDIT SELECTION")
    print("="*70)
    print("\nChoose your content path:")
    print()
    print("1️⃣  PERSONAL STORIES PATH")
    print("    📖 r/TrueOffMyChest + r/Confessions")
    print("    💭 Personal experiences, life stories, confessions")
    print("    🎯 Great for emotional, relatable content")
    print()
    print("2️⃣  AITA PATH") 
    print("    ⚖️  r/AmItheAsshole + r/AITA")
    print("    🤔 Moral dilemmas, relationship conflicts")
    print("    🎯 Great for debate-worthy, engaging content")
    print()
    print("3️⃣  SPOOKY PATH")
    print("    👻 r/NoSleep + r/ScaryStories") 
    print("    🎃 Horror stories, creepy experiences")
    print("    🎯 Great for thrilling, suspenseful content")
    print()
    print("="*70)
    
    while True:
        try:
            choice = input("\n🎮 Select your path (1/2/3): ").strip()
            
            if choice == "1":
                print("✅ Selected: PERSONAL STORIES PATH (TrueOffMyChest + Confessions)")
                return ["TrueOffMyChest", "Confessions"], "Personal Stories"
            elif choice == "2":
                print("✅ Selected: AITA PATH (AmItheAsshole + AITA)")
                return ["AmItheAsshole", "AITA"], "AITA Stories"
            elif choice == "3":
                print("✅ Selected: SPOOKY PATH (NoSleep + ScaryStories)")
                return ["nosleep", "scarystories"], "Spooky Stories"
            else:
                print("❌ Please enter 1, 2, or 3")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            exit(0)

def fetch_story_from_multiple_subreddits(subreddits):
    """Fetch stories from selected subreddits."""
    
    for subreddit_name in subreddits:
        print(f"🔍 Searching r/{subreddit_name}...")
        story = fetch_story_from_subreddit(subreddit_name)
        if story:
            return story
    
    print("❌ No suitable stories found in any subreddit")
    return None

def fetch_story_from_subreddit(subreddit_name):
    """Fetch a story from a specific subreddit with quality-focused selection."""
    try:
        subreddit_obj = reddit.subreddit(subreddit_name)
        
        print(f"  🎯 Quality-focused search - prioritizing high-scoring posts...")
        
        # Quality-focused search strategy: prioritize top posts across all time periods
        search_strategies = [
            ("top", "all", 500, "🏆 All-time top posts"),
            ("top", "year", 400, "📅 This year's top posts"),
            ("top", "month", 300, "📅 This month's top posts"),
            ("hot", None, 200, "🔥 Currently hot posts"),
            ("top", "week", 200, "📅 This week's top posts"),
            ("new", None, 100, "🆕 Recent posts (for variety)"),
        ]
        
        all_posts = []
        
        for sort_method, time_filter, limit, description in search_strategies:
            try:
                print(f"    {description}...")
                
                if sort_method == "top" and time_filter:
                    posts = subreddit_obj.top(time_filter=time_filter, limit=limit)
                elif sort_method == "hot":
                    posts = subreddit_obj.hot(limit=limit)
                elif sort_method == "new":
                    posts = subreddit_obj.new(limit=limit)
                else:
                    continue
                
                # Filter for posts with text content
                posts_with_text = [post for post in posts if post.selftext]
                update_posts_filtered = 0
                
                valid_posts = []
                for post in posts_with_text:
                    # Enhanced criteria with minimum score threshold
                    if (len(post.selftext) > 100   # Minimum for good stories
                        and len(post.selftext) < 3000  # Conservative max for 2:50
                        and not post.stickied 
                        and post.score >= 10  # Higher minimum score for quality
                        and len(post.title + post.selftext) < 3200):  # Conservative total
                        
                        # Check if it's an update post (skip update posts)
                        if post.title.upper().startswith(('UPDATE:', 'EDIT:', 'FINAL UPDATE', 'PART 2', 'PART 3')):
                            update_posts_filtered += 1
                        else:
                            valid_posts.append(post)
                
                if update_posts_filtered > 0:
                    print(f"      Filtered out {update_posts_filtered} update posts")
                
                # Apply HARD 2:50 validation to each post
                validated_posts = []
                for post in valid_posts:
                    test_story = {
                        "title": post.title,
                        "body": post.selftext
                    }
                    is_valid, duration = validate_story_length(test_story)
                    if is_valid:
                        validated_posts.append(post)
                
                print(f"      Found {len(validated_posts)} quality posts (score ≥10, ≤2:50)")
                all_posts.extend(validated_posts)
                
                # Continue collecting from all sources for better selection
                
            except Exception as e:
                print(f"      Error fetching {description}: {e}")
                continue
        
        # Remove duplicates based on post ID
        unique_posts = {post.id: post for post in all_posts}.values()
        unique_posts = list(unique_posts)
        
        # Filter out previously used and blacklisted stories
        used_stories = load_used_stories()
        blacklisted_stories = load_blacklisted_stories()
        print(f"📚 Found {len(used_stories)} previously used stories")
        print(f"🚫 Found {len(blacklisted_stories)} blacklisted stories")
        
        # Filter out both used and blacklisted stories
        fresh_posts = [post for post in unique_posts 
                      if post.id not in used_stories and post.id not in blacklisted_stories]
        print(f"🆕 {len(fresh_posts)} fresh posts available out of {len(unique_posts)} total")
        
        # If we've used all stories, clear the used stories file and start fresh
        if not fresh_posts:
            print("All recent stories have been used, clearing history and fetching new content...")
            # Clear the used stories file
            try:
                with open(USED_STORIES_FILE, 'w') as f:
                    json.dump({'used_ids': []}, f)
                print("✅ Story history cleared")
            except Exception as e:
                print(f"Error clearing story history: {e}")
            
            fresh_posts = unique_posts
        
        if fresh_posts:
            # Quality-weighted selection: favor higher-scoring posts
            selected_post = select_quality_weighted_story(fresh_posts)
            
            # Mark this story as used
            save_used_story(selected_post.id)
            
            story_data = {
                "title": selected_post.title,
                "body": selected_post.selftext,
                "score": selected_post.score,
                "comments": selected_post.num_comments,
                "url": f"https://reddit.com{selected_post.permalink}",
                "id": selected_post.id,
                "subreddit": subreddit_name
            }
            
            _, duration = validate_story_length(story_data)
            print(f"✅ Selected story from r/{subreddit_name}: '{selected_post.title[:50]}...'")
            print(f"⏱️ Duration: {duration:.1f}s | Score: {selected_post.score} (QUALITY-WEIGHTED)")
            
            return story_data
        else:
            print(f"No valid stories found in r/{subreddit_name}")
            return None
    except Exception as e:
        print(f"Error fetching from r/{subreddit_name}: {e}")
        return None

# Initialize TikTok TTS
tiktok_tts = TikTokTTS()

# Helper functions for tracking used stories
def load_used_stories():
    """Load the list of previously used story IDs."""
    try:
        if os.path.exists(USED_STORIES_FILE):
            with open(USED_STORIES_FILE, 'r') as f:
                data = json.load(f)
                # Clean old entries (older than 7 days)
                current_time = time.time()
                data['used_ids'] = [
                    entry for entry in data.get('used_ids', [])
                    if current_time - entry.get('timestamp', 0) < 7 * 24 * 3600
                ]
                return set(entry['id'] for entry in data['used_ids'])
        return set()
    except Exception as e:
        print(f"Error loading used stories: {e}")
        return set()

def save_used_story(story_id):
    """Save a story ID as used (prevent duplicates)."""
    try:
        # Load existing data
        data = {'used_ids': []}
        if os.path.exists(USED_STORIES_FILE):
            with open(USED_STORIES_FILE, 'r') as f:
                data = json.load(f)
        
        # Check if story is already saved
        existing_ids = [entry['id'] for entry in data.get('used_ids', [])]
        if story_id not in existing_ids:
            # Add new story only if not already present
            data['used_ids'].append({
                'id': story_id,
                'timestamp': time.time()
            })
            
            # Save back
            with open(USED_STORIES_FILE, 'w') as f:
                json.dump(data, f)
            print(f"✅ Story {story_id} marked as used")
        else:
            print(f"⚠️ Story {story_id} already marked as used")
            
    except Exception as e:
        print(f"Error saving used story: {e}")

def load_last_voice():
    """Load the last used voice."""
    try:
        if os.path.exists(LAST_VOICE_FILE):
            with open(LAST_VOICE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_voice')
        return None
    except Exception as e:
        print(f"Error loading last voice: {e}")
        return None

def save_last_voice(voice):
    """Save the last used voice."""
    try:
        data = {'last_voice': voice, 'timestamp': time.time()}
        with open(LAST_VOICE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving last voice: {e}")

def estimate_video_duration(text):
    """Estimate video duration based on text length and TikTok TTS speed with 1.3x tempo."""
    # TikTok TTS at 1.3x speed: approximately 180-200 words per minute
    # Being conservative to ensure we stay under 2:50
    words = len(text.split())
    estimated_duration = (words / 180) * 60  # Convert to seconds (more conservative)
    return estimated_duration

def is_update_post(title):
    """Check if a post is an update thread."""
    title_lower = title.lower().strip()
    
    # Common update post patterns
    update_patterns = [
        'update:',
        'update -',
        'update—',
        'update –',
        '[update]',
        '(update)',
        'final update',
        'small update',
        'quick update',
        'mini update',
        'brief update'
    ]
    
    # Check if title starts with any update pattern
    for pattern in update_patterns:
        if title_lower.startswith(pattern):
            return True
    
    # Check for "UPDATE" anywhere in the first 20 characters (common format)
    if 'update' in title_lower[:20]:
        return True
    
    return False

def validate_story_length(story):
    """HARD RULE: Story MUST fit in 2 minute 50 second video - NO EXCEPTIONS."""
    if not story:
        return False, 0
    
    full_text = f"{story['title']} {story['body']}"
    estimated_duration = estimate_video_duration(full_text)
    
    # HARD LIMIT: 2 minutes 50 seconds = 170 seconds - NEVER EXCEED
    return estimated_duration <= 170, estimated_duration

def validate_caption_accuracy(captions, audio_duration):
    """Validate that captions timing matches audio duration."""
    if not captions:
        return False, "No captions to validate"
    
    try:
        total_caption_time = max(cap.end for cap in captions)
        time_difference = abs(total_caption_time - audio_duration)
        
        if time_difference <= 2.0:  # Within 2 seconds is acceptable
            return True, f"Captions accurate (±{time_difference:.1f}s)"
        else:
            return False, f"Captions timing off by {time_difference:.1f}s"
            
    except Exception as e:
        return False, f"Validation error: {e}"

def create_safe_filename(title, max_length=50):
    """Create a safe filename from story title."""
    import re
    
    # Remove AITA prefix and clean up
    clean_title = title.replace("AITA for ", "").replace("AITA ", "")
    clean_title = clean_title.replace("WIBTA for ", "").replace("WIBTA ", "")
    
    # Remove special characters and replace with underscores
    safe_title = re.sub(r'[<>:"/\\|?*]', '', clean_title)
    safe_title = re.sub(r'[^\w\s-]', '', safe_title)
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    
    # Truncate if too long
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length].rstrip('_')
    
    return safe_title or "untitled_story"

# Helper functions for tracking last used voice
def load_last_voice():
    """Load the last used voice to avoid repetition."""
    try:
        if os.path.exists(LAST_VOICE_FILE):
            with open(LAST_VOICE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_voice')
        return None
    except Exception as e:
        print(f"Error loading last voice: {e}")
        return None

def save_last_voice(voice_id):
    """Save the last used voice."""
    try:
        data = {
            'last_voice': voice_id,
            'timestamp': time.time()
        }
        with open(LAST_VOICE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving last voice: {e}")

def load_blacklisted_stories():
    """Load the list of blacklisted story IDs."""
    try:
        if os.path.exists(BLACKLISTED_STORIES_FILE):
            with open(BLACKLISTED_STORIES_FILE, 'r') as f:
                data = json.load(f)
                return set(entry['id'] for entry in data.get('blacklisted_ids', []))
        return set()
    except Exception as e:
        print(f"Error loading blacklisted stories: {e}")
        return set()

def save_blacklisted_story(story_id, title):
    """Save a story ID as blacklisted (permanently rejected)."""
    try:
        # Load existing data
        data = {'blacklisted_ids': []}
        if os.path.exists(BLACKLISTED_STORIES_FILE):
            with open(BLACKLISTED_STORIES_FILE, 'r') as f:
                data = json.load(f)
        
        # Check if story is already blacklisted
        existing_ids = [entry['id'] for entry in data.get('blacklisted_ids', [])]
        if story_id not in existing_ids:
            # Add new blacklisted story
            data['blacklisted_ids'].append({
                'id': story_id,
                'title': title,
                'timestamp': time.time()
            })
            
            # Save back
            with open(BLACKLISTED_STORIES_FILE, 'w') as f:
                json.dump(data, f)
            print(f"🚫 Story {story_id} blacklisted: '{title[:50]}...'")
        else:
            print(f"⚠️ Story {story_id} already blacklisted")
            
    except Exception as e:
        print(f"Error saving blacklisted story: {e}")

def ask_user_approval(story):
    """Ask user if they want to create a video with this story."""
    print(f"\n" + "="*60)
    print(f"📖 STORY PREVIEW:")
    print(f"Title: {story['title']}")
    print(f"Score: {story['score']} upvotes | Comments: {story['comments']}")
    print(f"URL: {story['url']}")
    print(f"\n📝 Content Preview:")
    print("-" * 40)
    
    # Show first 300 characters of the story
    preview_text = story['body'][:300]
    if len(story['body']) > 300:
        preview_text += "..."
    print(preview_text)
    print("-" * 40)
    
    # Get duration info
    is_valid, estimated_duration = validate_story_length(story)
    print(f"⏱️ Estimated duration: {estimated_duration:.1f} seconds")
    print(f"✅ Within 2:50 limit: {'Yes' if is_valid else 'No'}")
    print("="*60)
    
    while True:
        response = input("\n🎬 Create video with this story? (y/n/q): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            # Blacklist this story
            save_blacklisted_story(story['id'], story['title'])
            return False
        elif response in ['q', 'quit']:
            print("👋 Exiting...")
            exit(0)
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'q' to quit.")

# Helper function to generate narration audio using TikTok TTS
def generate_tiktok_narration(text, output_file="narration.mp3", voice="en_us_rocket"):
    """Generate audio from text using TikTok's actual TTS voices."""
    try:
        output_file = os.path.join(os.getcwd(), output_file)
        
        # Generate TikTok TTS audio
        result = tiktok_tts.generate_speech(text, voice, output_file)
        
        if result and os.path.exists(result):
            return result
        else:
            print("Failed to generate TikTok TTS audio")
            return None
            
    except Exception as e:
        print(f"Error generating TikTok narration: {e}")
        return None

# Helper function to generate narration audio using Edge-TTS (fallback)
async def generate_narration_async(text, output_file="narration.mp3", voice="en-US-AndrewNeural"):
    """Generate audio from text using Edge-TTS with natural voices."""
    try:
        output_file = os.path.join(os.getcwd(), output_file)
        
        # Create TTS communication
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
        # Speed up the audio by 1.3x for faster narration (increased from 1.2x)
        temp_file = output_file.replace('.mp3', '_temp.mp3')
        os.rename(output_file, temp_file)
        
        # Use FFmpeg to speed up audio more for longer stories
        import subprocess
        subprocess.run([
            'ffmpeg', '-i', temp_file, '-filter:a', 'atempo=1.3', 
            '-y', output_file
        ], capture_output=True)
        
        # Clean up temp file
        os.remove(temp_file)
        
        return output_file
    except Exception as e:
        print(f"Error generating narration: {e}")
        return None

def generate_narration(text, output_file="narration.mp3", voice="en-US-AndrewNeural", use_tiktok=True):
    """Wrapper function to generate narration with TikTok or Edge-TTS."""
    print(f"Generating narration with {'TikTok' if use_tiktok else 'Edge-TTS'} voice: {voice}")
    print(f"Text length: {len(text)} characters")
    
    if use_tiktok:
        result = generate_tiktok_narration(text, output_file, voice)
        print(f"TikTok TTS result: {result}")
        return result
    else:
        result = asyncio.run(generate_narration_async(text, output_file, voice))
        print(f"Edge-TTS result: {result}")
        return result

# Helper function to analyze audio and create accurate captions
def analyze_audio_timing(audio_file, text):
    """Analyze audio file to get accurate timing for captions."""
    try:
        from moviepy.editor import AudioFileClip
        
        # Load audio to get actual duration
        audio = AudioFileClip(audio_file)
        actual_duration = audio.duration
        
        # Split text into sentences for natural breaks
        sentences = []
        current_sentence = ""
        
        # Split by common sentence endings
        for char in text:
            current_sentence += char
            if char in '.!?' and len(current_sentence.strip()) > 10:
                sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # Add remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # Calculate timing based on sentence length (more accurate)
        total_chars = sum(len(s) for s in sentences)
        timings = []
        current_time = 0
        
        for sentence in sentences:
            # Calculate duration based on character count and faster speaking speed
            char_ratio = len(sentence) / total_chars
            duration = actual_duration * char_ratio
            
            timings.append({
                'text': sentence,
                'start': current_time,
                'duration': duration,
                'end': current_time + duration
            })
            current_time += duration
        
        return timings, actual_duration
        
    except Exception as e:
        print(f"Error analyzing audio timing: {e}")
        return [], 0

def wrap_text_to_width(text, font, max_width, draw):
    """Wrap text to fit within specified width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word would exceed max width
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        
        if line_width <= max_width:
            current_line.append(word)
        else:
            # Start new line
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway
                lines.append(word)
    
    # Add remaining words
    if current_line:
        lines.append(' '.join(current_line))
    
    return '\n'.join(lines)

def create_caption_image(text, width=700, height=250):
    """Create a caption image with exact text fitting and 4px padding minimum."""
    try:
        # First, create a temporary image to measure text size
        temp_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Popular TikTok fonts in order of preference
        tiktok_fonts = [
            # TikTok's preferred fonts
            "C:/Windows/Fonts/impact.ttf",      # Impact - very popular for TikTok
            "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold - clean and bold
            "C:/Windows/Fonts/arial.ttf",       # Arial - fallback
            "C:/Windows/Fonts/calibrib.ttf",    # Calibri Bold - modern
            "C:/Windows/Fonts/verdanab.ttf",    # Verdana Bold - readable
            # Generic names that might work
            "impact.ttf",
            "arial-bold.ttf", 
            "arial.ttf"
        ]
        
        font = None
        font_size = 48  # Even larger for better visibility
        
        # Try each font until one works
        for font_path in tiktok_fonts:
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"✅ Using TikTok font: {font_path}")
                break
            except:
                continue
        
        # Ultimate fallback
        if font is None:
            font = ImageFont.load_default()
            print("⚠️ Using default font (TikTok fonts not found)")
        
        # Smart text wrapping to prevent cropping
        max_width = width - 20  # Leave 10px margin on each side for wrapping
        wrapped_text = wrap_text_to_width(text, font, max_width, temp_draw)
        
        # Test with descender letters to get accurate height measurement
        test_text_with_descenders = wrapped_text + "\npgjyq"  # Add descender letters for measurement
        bbox_with_descenders = temp_draw.multiline_textbbox((0, 0), test_text_with_descenders, font=font, align='center')
        
        # Calculate exact text dimensions
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=font, align='center')
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Get the full height including potential descenders
        full_height_with_descenders = bbox_with_descenders[3] - bbox_with_descenders[1]
        descender_extra = full_height_with_descenders - text_height
        
        # Create final image with exact size needed + padding + descender space
        padding = 16  # 8px on each side
        final_width = max(width, text_width + padding)
        final_height = max(height, text_height + padding + descender_extra + 8)  # Extra 8px for safety
        
        # Create the actual image with proper size
        img = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Center text with guaranteed padding and descender space
        x = (final_width - text_width) // 2
        y = max(8, (final_height - text_height - descender_extra) // 2)  # Ensure top padding and descender space
        
        # TikTok-style text with thick black outline
        outline_width = 3  # Thicker outline for TikTok style
        
        # Draw black outline (multiple passes for thickness)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.multiline_text((x + dx, y + dy), wrapped_text, font=font, 
                                      fill=(0, 0, 0, 255), align='center')
        
        # Draw bright white text on top (TikTok style)
        draw.multiline_text((x, y), wrapped_text, font=font, 
                          fill=(255, 255, 255, 255), align='center')
        
        # Convert to numpy array for MoviePy
        return np.array(img)
        
    except Exception as e:
        print(f"Error creating caption image: {e}")
        return None

def split_long_caption(text, max_chars=80):
    """Split long captions into two parts if they're too long."""
    if len(text) <= max_chars:
        return [text]
    
    # Try to split at a natural break point (sentence, comma, etc.)
    words = text.split()
    mid_point = len(words) // 2
    
    # Look for a good break point near the middle
    for offset in range(5):  # Check 5 words before and after mid point
        for direction in [-1, 1]:
            check_idx = mid_point + (offset * direction)
            if 0 <= check_idx < len(words):
                word = words[check_idx]
                # Good break points
                if word.endswith(('.', '!', '?', ',')) or word in ['and', 'but', 'so', 'then', 'because']:
                    first_part = ' '.join(words[:check_idx + 1])
                    second_part = ' '.join(words[check_idx + 1:])
                    if first_part and second_part:
                        return [first_part, second_part]
    
    # Fallback: split at midpoint
    first_part = ' '.join(words[:mid_point])
    second_part = ' '.join(words[mid_point:])
    return [first_part, second_part]

def create_accurate_captions(text, audio_file, video_size):
    """Create captions with accurate timing and smart text splitting."""
    try:
        # Analyze audio for accurate timing
        timings, duration = analyze_audio_timing(audio_file, text)
        
        if not timings:
            print("Could not analyze audio timing, using estimated timing")
            return create_pil_captions(text, duration, video_size)
        
        caption_clips = []
        
        for i, timing in enumerate(timings):
            try:
                caption_text = timing['text']
                
                # Check if caption is too long and needs splitting
                caption_parts = split_long_caption(caption_text, max_chars=60)
                
                if len(caption_parts) == 1:
                    # Single caption - use full duration, position at bottom
                    caption_img = create_caption_image(caption_parts[0], width=int(video_size[0]), height=100)
                    
                    if caption_img is not None:
                        img_clip = ImageClip(caption_img, transparent=True, duration=timing['duration'])
                        img_clip = img_clip.set_position(('center', 0.5), relative=True)  # Centered in middle
                        img_clip = img_clip.set_start(timing['start'])
                        
                        caption_clips.append(img_clip)
                        print(f"Caption {i+1}: {timing['start']:.1f}s - {timing['end']:.1f}s")
                
                else:
                    # Split caption - show each part for half the duration
                    part_duration = timing['duration'] / 2
                    
                    for part_idx, part_text in enumerate(caption_parts):
                        caption_img = create_caption_image(part_text, width=int(video_size[0]), height=80)
                        
                        if caption_img is not None:
                            part_start = timing['start'] + (part_idx * part_duration)
                            img_clip = ImageClip(caption_img, transparent=True, duration=part_duration)
                            img_clip = img_clip.set_position(('center', 0.5), relative=True)  # Centered in middle
                            img_clip = img_clip.set_start(part_start)
                            
                            caption_clips.append(img_clip)
                            print(f"Caption {i+1}.{part_idx+1}: {part_start:.1f}s - {part_start + part_duration:.1f}s (split)")
                
            except Exception as e:
                print(f"Error creating caption clip {i}: {e}")
                continue
        
        return caption_clips
        
    except Exception as e:
        print(f"Error creating accurate captions: {e}")
        return create_pil_captions(text, 60, video_size)

def create_pil_captions(text, video_duration, video_size):
    """Create captions using PIL images with estimated timing."""
    try:
        # Split text into readable chunks
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            # Create chunks of about 6-8 words for better readability
            if len(current_chunk) >= 7 or len(' '.join(current_chunk)) > 45:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
        
        # Add remaining words
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        if not chunks:
            return []
        
        # Calculate timing for each chunk
        time_per_chunk = video_duration / len(chunks)
        caption_clips = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Check if chunk needs splitting
                chunk_parts = split_long_caption(chunk, max_chars=60)
                
                if len(chunk_parts) == 1:
                    # Single caption
                    caption_img = create_caption_image(chunk_parts[0], width=int(video_size[0]), height=100)
                
                    if caption_img is not None:
                        # Single caption - use full duration
                        duration = min(time_per_chunk, video_duration - (i * time_per_chunk))
                        img_clip = ImageClip(caption_img, transparent=True, duration=duration)
                        img_clip = img_clip.set_position(('center', 0.5), relative=True)  # Centered in middle
                        img_clip = img_clip.set_start(i * time_per_chunk)
                        
                        caption_clips.append(img_clip)
                        print(f"PIL Caption {i+1}: {i * time_per_chunk:.1f}s - {(i+1) * time_per_chunk:.1f}s")
                
                else:
                    # Split caption - show each part for half the duration
                    part_duration = time_per_chunk / 2
                    
                    for part_idx, part_text in enumerate(chunk_parts):
                        caption_img = create_caption_image(part_text, width=int(video_size[0]), height=80)
                        
                        if caption_img is not None:
                            part_start = (i * time_per_chunk) + (part_idx * part_duration)
                            duration = min(part_duration, video_duration - part_start)
                            img_clip = ImageClip(caption_img, transparent=True, duration=duration)
                            img_clip = img_clip.set_position(('center', 0.5), relative=True)  # Centered in middle
                            img_clip = img_clip.set_start(part_start)
                            
                            caption_clips.append(img_clip)
                            print(f"PIL Caption {i+1}.{part_idx+1}: {part_start:.1f}s - {part_start + duration:.1f}s (split)")
                
            except Exception as e:
                print(f"Error creating PIL caption clip {i}: {e}")
                continue
        
        return caption_clips
    except Exception as e:
        print(f"Error creating PIL captions: {e}")
        return []

# Helper function to create a TikTok-compatible video with captions and background music
def create_video(input_video_file, input_audio_file, output_file, story_text=""):
    """Creates a TikTok-style video with captions, background music, and 9:16 aspect ratio."""
    try:
        output_path = os.path.join(os.getcwd(), output_file)

        # Load video and narration audio
        video = VideoFileClip(input_video_file)
        narration_audio = AudioFileClip(input_audio_file)

        # Calculate audio duration and select a video slice
        audio_duration = narration_audio.duration
        max_start_time = max(0, video.duration - audio_duration)
        start_time = random.uniform(0, max_start_time)
        end_time = start_time + audio_duration
        video_slice = video.subclip(start_time, end_time)

        # Crop video to fit TikTok's 9:16 aspect ratio
        target_aspect_ratio = 9 / 16
        video_width, video_height = video_slice.size
        current_aspect_ratio = video_width / video_height

        if current_aspect_ratio > target_aspect_ratio:
            # Crop width (landscape video)
            new_width = int(video_height * target_aspect_ratio)
            crop_x1 = (video_width - new_width) // 2
            crop_x2 = crop_x1 + new_width
            video_cropped = video_slice.crop(x1=crop_x1, x2=crop_x2)
        else:
            # Crop height (portrait video)
            new_height = int(video_width / target_aspect_ratio)
            crop_y1 = (video_height - new_height) // 2
            crop_y2 = crop_y1 + new_height
            video_cropped = video_slice.crop(y1=crop_y1, y2=crop_y2)

        # Create background music (soft lofi)
        try:
            lofi_path = os.path.join(os.getcwd(), "static/lofi_background.wav")
            if os.path.exists(lofi_path):
                background_music = AudioFileClip(lofi_path).subclip(0, audio_duration)
                background_music = background_music.volumex(0.15)  # Soft background volume
                print("Added lofi background music")
            else:
                # Fallback to video's original audio as ambient sound
                background_music = video_cropped.audio
                if background_music:
                    background_music = background_music.volumex(0.05)  # Very quiet background
                else:
                    background_music = None
                print("Using video ambient audio as background")
        except Exception as e:
            print(f"Error loading background music: {e}")
            background_music = None

        # Combine narration with background music
        if background_music:
            final_audio = CompositeAudioClip([
                narration_audio.volumex(0.9),  # Main narration slightly reduced
                background_music.volumex(0.15)  # Soft background music
            ])
        else:
            final_audio = narration_audio

        # Add audio to the cropped video
        video_with_audio = video_cropped.set_audio(final_audio)

        # Create accurate captions based on audio analysis
        print("Creating accurate captions with audio timing...")
        try:
            caption_clips = create_accurate_captions(story_text, input_audio_file, video_cropped.size)
            
            if caption_clips:
                final_video = CompositeVideoClip([video_with_audio] + caption_clips)
                print(f"✅ Added {len(caption_clips)} caption segments with accurate timing")
            else:
                final_video = video_with_audio
                print("⚠️ No captions added - using video without captions")
        except Exception as e:
            print(f"❌ Caption creation failed: {e}")
            final_video = video_with_audio

        # Write the final video
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            fps=24
        )

        # Ensure the file exists before returning
        return output_path if os.path.exists(output_path) else None
    except Exception as e:
        print(f"Error creating video: {e}")
        return None

def create_safe_filename(title, max_length=50):
    """Create a safe filename from story title."""
    import re
    
    # Remove common prefixes from different subreddit types
    clean_title = title
    
    # Personal Stories prefixes
    clean_title = clean_title.replace("TrueOffMyChest: ", "").replace("Confession: ", "")
    
    # AITA prefixes
    clean_title = clean_title.replace("AITA for ", "").replace("AITA ", "")
    clean_title = clean_title.replace("WIBTA for ", "").replace("WIBTA ", "")
    
    # Horror story prefixes (usually don't have standard prefixes, but clean up common ones)
    clean_title = clean_title.replace("NoSleep: ", "").replace("Scary Story: ", "")
    
    # Remove special characters and replace with underscores
    safe_title = re.sub(r'[<>:"/\\|?*]', '', clean_title)
    safe_title = re.sub(r'[^\w\s-]', '', safe_title)
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    
    # Truncate if too long
    if len(safe_title) > max_length:
        safe_title = safe_title[:max_length].rstrip('_')
    
    return safe_title or "untitled_story"

if __name__ == "__main__":
    print("🎬 Reddit-to-TikTok Generator Starting...")
    
    # Get user's subreddit choice once at startup
    selected_subreddits, path_name = get_subreddit_selection()
    print(f"\n🔍 Using {path_name} subreddits: {', '.join([f'r/{sub}' for sub in selected_subreddits])}")
    print("="*70)
    
    approved_story = None
    
    # Keep fetching stories until one is approved
    while approved_story is None:
        print(f"\n🔍 Fetching a new story from {path_name} subreddits...")
        
        # Fetch a story from the user's selected subreddits
        story = fetch_story_from_multiple_subreddits(selected_subreddits)
        
        if story:
            # Ask user for approval
            if ask_user_approval(story):
                approved_story = story
                print(f"\n✅ Story approved! Proceeding with video generation...")
            else:
                print(f"\n❌ Story rejected and blacklisted. Fetching another story...")
                continue
        else:
            print("❌ No suitable stories found. Exiting...")
            break
    
    if approved_story:
        print(f"\n🎯 GENERATING VIDEO FOR APPROVED STORY:")
        print(f"Title: {approved_story['title']}")
        print(f"Score: {approved_story['score']} | Comments: {approved_story['comments']}")
        print(f"URL: {approved_story['url']}")
        print(f"Text length: {len(approved_story['body'])} characters")
        
        # Final duration check
        is_valid, estimated_duration = validate_story_length(approved_story)
        if estimated_duration > 170:
            print(f"❌ HARD LIMIT VIOLATION: Story exceeds 2:50 ({estimated_duration:.1f}s)")
        else:
            print(f"✅ Story duration: {estimated_duration:.1f} seconds (within HARD LIMIT)")
        print()
        # Combine the title and body for narration
        narration_text = f"{approved_story['title']} {approved_story['body']}"

        # File paths
        input_video = os.path.join(os.getcwd(), "static/minecraft_background.mp4")  # Path to test video
        input_audio = os.path.join(os.getcwd(), "narration.mp3")  # Path to generated narration audio
        
        # Create filename based on story title
        safe_filename = create_safe_filename(approved_story['title'])
        
        # Create separate folders for each story type
        folder_name = path_name.lower().replace(" ", "_")  # Convert "Personal Stories" to "personal_stories"
        story_type_dir = os.path.join(os.path.dirname(os.getcwd()), "rendered_videos", folder_name)
        
        # Create the story type directory if it doesn't exist
        os.makedirs(story_type_dir, exist_ok=True)
        
        output_video = os.path.join(story_type_dir, f"{safe_filename}.mp4")
        print(f"📁 Output filename: {safe_filename}.mp4 (saved to thread-2-tok/rendered_videos/{folder_name}/)")

        # Generate narration audio from the fetched story
        # Popular TikTok voices you can choose from (Disney voices disabled):
        tiktok_voices = {
            "en_us_001": "Female (Standard)",
            "en_us_002": "Female (Warm)",
            "en_us_006": "Male (Standard)", 
            "en_us_007": "Male (Narrator)",
            "en_us_009": "Male (Funny)",
            "en_us_010": "Male (Serious)",
            "en_male_narration": "Male (Storyteller)",
            "en_male_funny": "Male (Comedic)",
            "en_female_emotional": "Female (Emotional)",
            "en_male_cody": "Male (Cody)",
            "en_us_chewbacca": "Chewbacca (Star Wars)",
            "en_us_ghostface": "Ghostface (Scream)",
            "en_us_c3po": "C-3PO (Star Wars)"
        }
        
        # Select a popular voice with weighted randomness (Disney voices disabled)
        voice_weights = {
            "en_male_narration": 35, # Great storyteller voice (boosted)
            "en_us_007": 25,         # Professional narrator (boosted)
            "en_us_009": 20,         # Funny voice (boosted)
            "en_us_006": 15,         # Male standard voice
            "en_us_ghostface": 5     # Dramatic but niche
        }
        
        # Get last used voice to avoid repetition
        last_voice = load_last_voice()
        
        # Remove last voice from selection to ensure variety
        available_voices = voice_weights.copy()
        if last_voice and last_voice in available_voices:
            del available_voices[last_voice]
            print(f"🚫 Excluding last used voice: {tiktok_voices.get(last_voice, last_voice)}")
        
        # Weighted random selection from remaining voices
        voices = list(available_voices.keys())
        weights = list(available_voices.values())
        selected_voice = random.choices(voices, weights=weights)[0]
        
        # Save this voice as the last used
        save_last_voice(selected_voice)
        
        print(f"Trying TikTok voice: {tiktok_voices.get(selected_voice, selected_voice)}")
        narration_path = generate_narration(narration_text, input_audio, selected_voice, use_tiktok=True)
        
        # If TikTok TTS fails, fall back to Edge-TTS
        if not narration_path or not os.path.exists(narration_path):
            print("TikTok TTS failed, falling back to Edge-TTS...")
            edge_voice = "en-US-AndrewNeural"  # Professional male voice
            narration_path = generate_narration(narration_text, input_audio, edge_voice, use_tiktok=False)

        # Create the video with the narration audio
        print(f"Checking files:")
        print(f"  Narration path: {narration_path}")
        print(f"  Narration exists: {narration_path and os.path.exists(narration_path)}")
        print(f"  Input video: {input_video}")
        print(f"  Input video exists: {os.path.exists(input_video)}")
        print(f"  Input audio: {input_audio}")
        print(f"  Input audio exists: {os.path.exists(input_audio)}")
        
        if narration_path and os.path.exists(narration_path) and os.path.exists(input_video):
            print("Creating video with captions and background music...")
            video_path = create_video(input_video, input_audio, output_video, narration_text)
            if video_path:
                print(f"Video successfully created: {video_path}")
            else:
                print("Error: Video generation failed.")
        else:
            print("Error: Input video or narration file not found.")
    else:
        print(f"No stories found in the subreddit '{subreddit_name}'.")