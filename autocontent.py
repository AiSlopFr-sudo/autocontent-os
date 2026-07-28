import os
import sys
import re
import json
import random
import time
import subprocess
import requests
import imageio_ffmpeg
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
history_file = BASE_DIR / "history.json"

# Laad eerdere geschiedenis om duplicaten te voorkomen
history_data = {"topics": [], "scripts": []}
if history_file.exists():
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except Exception:
        pass

MASTER_TOPICS = [
    "Quantum Physics Oddities", 
    "Deep Ocean Trenches and Monsters", 
    "Ancient Roman Engineering Secrets", 
    "Human Brain Psychology Hacks", 
    "Bizarre Space Weather and Black Holes", 
    "Lost Historical Treasures", 
    "Microscopic Creatures and Insects", 
    "Strange Laws That Still Exist Today", 
    "Weird Animal Survival Tactics", 
    "Forbidden Archaeology Discoveries", 
    "Cybersecurity and Digital Myths", 
    "Extreme Earth Survival Stories",
    "Medical Oddities of the Human Body",
    "Conspiracies That Turned Out To Be True",
    "Bizarre Planet Facts in our Solar System"
]

# Filter onderwerpen die al zijn gebruikt
available_topics = [t for t in MASTER_TOPICS if t not in history_data.get("topics", [])]
if not available_topics:
    available_topics = MASTER_TOPICS
    history_data["topics"] = []

TOPIC = random.choice(available_topics)
history_data["topics"].append(TOPIC)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

random.seed(time.time_ns() ^ os.getpid())

safe_topic = "".join(c for c in TOPIC if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
timestamp_id = int(time.time())
output_file = BASE_DIR / f"video_{safe_topic}_{timestamp_id}.mp4"
metadata_file = BASE_DIR / f"video_{safe_topic}_{timestamp_id}.json"
audio_file = BASE_DIR / "audio.mp3"
music_file = BASE_DIR / "bg_music.mp3"
raw_vtt_file = BASE_DIR / "subtitles_raw.vtt"
ass_file = BASE_DIR / "subtitles.ass"
bg_image = BASE_DIR / "matching_background.jpg"

VOICE_MAP = {
    "Health": "en-US-AvaMultilingualNeural",
    "Lifestyle": "en-US-AvaMultilingualNeural",
    "Space": "en-US-AndrewMultilingualNeural",
    "AI": "en-US-BrianNeural",
    "Tech": "en-US-AndrewMultilingualNeural",
    "Money": "en-US-BrianNeural",
    "History": "en-GB-RyanNeural"
}

topic_key = next((k for k in VOICE_MAP if k.lower() in TOPIC.lower()), None)
CHOSEN_VOICE = VOICE_MAP[topic_key] if topic_key else random.choice(["en-US-AvaMultilingualNeural", "en-US-AndrewMultilingualNeural", "en-US-BrianNeural", "en-GB-RyanNeural"])

print(f"🚀 AutoContent OS: Single Video & Metadata Generator")
print(f"    ├─ Gekozen Onderwerp: '{TOPIC}'")
print(f"    ├─ Stem: '{CHOSEN_VOICE}'")
print(f"    └─ Output: '{output_file.name}'\n")

for old_clip in BASE_DIR.glob("temp_clip_*.mp4"):
    try:
        old_clip.unlink()
    except Exception:
        pass

if music_file.exists() and music_file.stat().st_size < 50000:
    music_file.unlink()

if not music_file.exists():
    try:
        music_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        res = requests.get(music_url, headers=headers, timeout=15)
        if res.status_code == 200 and len(res.content) > 50000:
            with open(music_file, "wb") as f:
                f.write(res.content)
    except Exception:
        pass

# 1. SCRIPT, KEYWORDS & YOUTUBE METADATA GENEREREN
print("1/4 🧠 Uniek script, Beeldzoektermen & YouTube Metadata genereren via Gemini AI...")
script_text = ""
search_keywords = [TOPIC, TOPIC, TOPIC]
youtube_metadata = {
    "title": f"Mind-Blowing Fact About {TOPIC}! #Shorts",
    "description": f"Learn a crazy fact about {TOPIC}!\n\n🤖 Disclaimer: This video was generated using AI tools for educational purposes.\n\n#Shorts #Facts #{safe_topic}",
    "tags": [TOPIC, "Facts", "Shorts", "Science"]
}

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        unique_seed = random.randint(10000000, 99999999)
        previous_scripts_snippet = "\n".join([f"- {s}" for s in history_data.get("scripts", [])[-15:]])
        
        prompt = (
            f"System Unique Hash ID: {unique_seed}\n"
            f"Write a viral YouTube Short script about a completely unique, highly specific, bizarre, and obscure micro-fact regarding '{TOPIC}'.\n"
            f"CRITICAL ANTI-DUPLICATE RULE: Do NOT repeat or resemble any of these previously used scripts:\n{previous_scripts_snippet}\n\n"
            f"Provide 3 distinct visual English search queries for Pexels stock video search, AND generate YouTube video metadata.\n\n"
            f"STRICT OUTPUT FORMAT (JSON only, no markdown, no backticks):\n"
            f"{{\n"
            f'  "script": "spoken text here...",\n'
            f'  "keywords": ["search term 1", "search term 2", "search term 3"],\n'
            f'  "title": "Catchy YouTube Short Title with Emojis",\n'
            f'  "description": "Engaging description text including #Shorts and relevant hashtags.",\n'
            f'  "tags": ["tag1", "tag2", "tag3", "tag4"]\n'
            f"}}\n\n"
            f"RULES:\n"
            f"1. Script length: STRICTLY 35 to 45 words total.\n"
            f"2. Title must be under 60 characters and ultra catchy.\n"
            f"3. Keywords must be 1 to 3 simple English visual words suited for stock footage search.\n"
            f"4. HOOK RULE: Start the script IMMEDIATELY with a shocking question, counter-intuitive fact, or direct confrontation. Never use words like 'Welcome', 'Today', 'In this video', or a slow introduction."
        )
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 1.0
            }
        )
        data = json.loads(response.text)
        script_text = data.get("script", "").strip().replace('\n', ' ')
        search_keywords = data.get("keywords", [TOPIC, TOPIC, TOPIC])
        
        raw_desc = data.get("description", f"Mind blowing fact about {TOPIC}!")
        ai_disclaimer = "\n\n🤖 Note: This video contains AI-generated/altered content for educational and entertainment purposes."
        
        youtube_metadata = {
            "title": data.get("title", f"Insane {TOPIC} Fact! #Shorts"),
            "description": raw_desc + ai_disclaimer,
            "tags": data.get("tags", [TOPIC, "Shorts", "Facts"])
        }
        print("    └─ Gemini AI script, unieke beeldsuggesties & metadata succesvol gegenereerd!")
    except Exception as e:
        print(f"    ⚠️ Fout bij Gemini AI API ({e}), terugvallen op backup metadata...")

if not script_text:
    fallback_scripts = [
        f"Did you know time actually passes faster the higher you are from sea level? Your head ages fractionally faster than your feet! Subscribe for more insane facts!",
        f"There is a planet made entirely of burning ice where temperatures reach 800 degrees! How is that physically possible? Subscribe for more wild facts!",
        f"Glass is technically neither a solid nor a liquid; it is a slow-moving amorphous solid! Subscribe for more mind-bending science!"
    ]
    script_text = random.choice(fallback_scripts)
    search_keywords = ["clock time", "planet fire", "glass texture"]

history_data["scripts"].append(script_text)

# Sla het bijgewerkte geheugen direct op
with open(history_file, "w", encoding="utf-8") as f:
    json.dump(history_data, f, indent=2)

with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(youtube_metadata, f, indent=2)

print(f"    ├─ Titel: \"{youtube_metadata['title']}\"")
print(f"    └─ Beeldzoektermen: {search_keywords}\n")

# 2. VOICE-OVER & ONDERTITELS GENEREREN
print("2/4 🎙️ Voice-over & ondertiteling genereren...")
try:
    cmd_tts = [
        "edge-tts",
        "--text", script_text,
        "--voice", CHOSEN_VOICE,
        "--write-media", str(audio_file),
        "--write-subtitles", str(raw_vtt_file)
    ]
    subprocess.run(cmd_tts, check=True)
except Exception as e:
    print(f"    ❌ Fout bij spraak/ondertiteling: {e}")
    exit(1)

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
def get_audio_duration(file_path):
    cmd = [ffmpeg_exe, "-i", str(file_path)]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return float(h)*3600 + float(m)*60 + float(s)
    return 15.0

audio_duration = get_audio_duration(audio_file)

def parse_time_to_sec(t_str):
    t_str = t_str.replace(',', '.')
    parts = t_str.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return 0.0

def format_time_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs -= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

try:
    with open(raw_vtt_file, "r", encoding="utf-8") as f:
        vtt_text = f.read()

    cue_pattern = r'((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})\s*-->\s*((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3})[^\n]*\n([\s\S]*?)(?=\n\n|\Z)'
    matches = re.findall(cue_pattern, vtt_text)

    dialogues = []
    max_words = 3

    for m in matches:
        start_t = parse_time_to_sec(m[0])
        end_t = parse_time_to_sec(m[1])
        text = " ".join(m[2].strip().split())
        words = text.split()
        if not words:
            continue

        total_dur = max(end_t - start_t, 0.5)
        chunks = [' '.join(words[i:i+max_words]) for i in range(0, len(words), max_words)]
        chunk_dur = total_dur / len(chunks)

        for idx, chunk in enumerate(chunks):
            c_start = start_t + idx * chunk_dur
            c_end = start_t + (idx + 1) * chunk_dur
            dialogues.append(f"Dialogue: 0,{format_time_ass(c_start)},{format_time_ass(c_end)},Default,,0,0,0,,{chunk}")

    if not dialogues:
        dialogues.append(f"Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{script_text[:30]}")

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,52,&H0000FFFF,&H00000000,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,0,2,50,50,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(dialogues))
except Exception as e:
    print(f"    ⚠️ Fout bij ondertitel conversie: {e}")

# 3. WILLEKEURIGE B-ROLL OPHALEN VAN PEXELS
clip_files = []
print(f"3/4 🎥 Willekeurige videoclips ophalen voor zoektermen...")
headers = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}

if PEXELS_API_KEY:
    for idx, kw in enumerate(search_keywords[:3]):
        try:
            url = f"https://api.pexels.com/videos/search?query={kw}&orientation=portrait&per_page=20"
            res = requests.get(url, headers=headers).json()
            if "videos" in res and len(res["videos"]) > 0:
                available_videos = res["videos"][:20]
                chosen_video_item = random.choice(available_videos)
                video_files = chosen_video_item["video_files"]
                best_video = next((v for v in video_files if v["quality"] == "hd" and "mp4" in v["file_type"]), video_files[0])
                clip_path = BASE_DIR / f"temp_clip_{idx}.mp4"
                vid_data = requests.get(best_video["link"])
                with open(clip_path, "wb") as f:
                    f.write(vid_data.content)
                clip_files.append(clip_path)
                print(f"    ├─ Clip {idx+1}: Willekeurig gedownload voor '{kw}'")
        except Exception as e:
            print(f"    ⚠️ Kon geen Pexels video ophalen voor '{kw}' ({e})")

print("")

if not clip_files:
    img_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1080&auto=format&fit=crop"
    img_res = requests.get(img_url)
    with open(bg_image, "wb") as f:
        f.write(img_res.content)

# 4. EINDMONTAGE
print("4/4 🎬 Vloeiende eindmontage starten...")
clean_ass_path = str(ass_file).replace(":", "\\:")
use_music = music_file.exists() and music_file.stat().st_size > 50000

filter_parts = []
cmd = [ffmpeg_exe, "-y"]

if clip_files:
    for cf in clip_files:
        cmd.extend(["-stream_loop", "-1", "-i", str(cf)])
    
    cmd.extend(["-i", str(audio_file)])
    voice_idx = len(clip_files)
    
    if use_music:
        cmd.extend(["-i", str(music_file)])
        music_idx = len(clip_files) + 1

    clip_dur = audio_duration / len(clip_files)
    concat_inputs = ""

    for i in range(len(clip_files)):
        filter_parts.append(
            f"[{i}:v]trim=0:{clip_dur:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{i}]"
        )
        concat_inputs += f"[v{i}]"

    filter_parts.append(f"{concat_inputs}concat=n={len(clip_files)}:v=1:a=0[vconcat]")
    filter_parts.append(f"[vconcat]subtitles=filename='{clean_ass_path}'[vout]")

    if use_music:
        filter_parts.append(f"[{voice_idx}:a]volume=1.0[vstem];[{music_idx}:a]volume=0.25[mstem];[vstem][mstem]amix=inputs=2:duration=first[aout]")
    
    cmd.extend(["-filter_complex", ";".join(filter_parts)])
    cmd.extend(["-map", "[vout]"])
    if use_music:
        cmd.extend(["-map", "[aout]"])
    else:
        cmd.extend(["-map", f"{voice_idx}:a:0"])

else:
    cmd.extend(["-loop", "1", "-i", str(bg_image), "-i", str(audio_file)])
    if use_music:
        cmd.extend(["-i", str(music_file)])
        filter_parts.append("[1:a]volume=1.0[vstem];[2:a]volume=0.25[mstem];[vstem][mstem]amix=inputs=2:duration=first[aout]")
        cmd.extend(["-filter_complex", ";".join(filter_parts), "-map", "0:v:0", "-map", "[aout]"])
    else:
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])

    vf_fallback = f"scale=1280:2272,zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=25*30:s=1080x1920,subtitles=filename='{clean_ass_path}'"
    cmd.extend(["-vf", vf_fallback])

cmd.extend([
    "-t", f"{audio_duration:.2f}",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-b:a", "128k",
    "-pix_fmt", "yuv420p",
    str(output_file)
])

subprocess.run(cmd, check=True)

for cf in clip_files:
    try:
        cf.unlink()
    except Exception:
        pass

print(f"\n🎉 VIDEO EN METADATA SUCCESVOL GEGENEREERD!")
print(f"    ├─ Video: '{output_file.name}'")
print(f"    └─ Metadata: '{metadata_file.name}'")