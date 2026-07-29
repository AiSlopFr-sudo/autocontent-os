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
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
history_file = BASE_DIR / "history.json"

if os.getenv("CLIENT_SECRET_JSON") and not Path("client_secret.json").exists():
    with open("client_secret.json", "w", encoding="utf-8") as f:
        f.write(os.getenv("CLIENT_SECRET_JSON"))

if os.getenv("TOKEN_JSON") and not Path("token.json").exists():
    with open("token.json", "w", encoding="utf-8") as f:
        f.write(os.getenv("TOKEN_JSON"))

# Uitgebreid persistent geheugen
history_data = {
    "topics": [],
    "facts": [],
    "titles": [],
    "scripts": [],
    "used_pexels_ids": []
}
if history_file.exists():
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
            if isinstance(loaded_data, dict):
                history_data.update(loaded_data)
    except Exception:
        pass

MASTER_TOPICS = [
    "Quantum Physics Oddities", "Deep Ocean Trenches and Monsters", "Ancient Roman Engineering Secrets", 
    "Human Brain Psychology Hacks", "Bizarre Space Weather and Black Holes", "Lost Historical Treasures", 
    "Microscopic Creatures and Insects", "Strange Laws That Still Exist Today", "Weird Animal Survival Tactics", 
    "Forbidden Archaeology Discoveries", "Cybersecurity and Digital Myths", "Extreme Earth Survival Stories",
    "Medical Oddities of the Human Body", "Conspiracies That Turned Out To Be True", "Bizarre Planet Facts in our Solar System",
    "Unsolved Deep Sea Mysteries", "Cryptids and Mythical Creatures Explained", "The Dark Side of Space Exploration",
    "Bizarre Body Modifications Through History", "Hidden Rooms in Famous Landmarks", "Strange Historical Medical Treatments",
    "The Weirdest Patents Ever Granted", "Unexplained Natural Phenomena on Earth", "Psychological Experiments That Went Too Far",
    "Lost Civilizations and Technologies", "Bizarre Deep Space Signals", "Unusual Animal Friendships and Behaviors",
    "Bizarre Deep Sea Fish Adaptations", "Bizarre Historical Weather Events", "Weird Quantum Entanglement Experiments",
    "Strange Medical Anomalies and Conditions", "Lost Ancient Roman Technologies", "Bizarre Psychological Illusion Hacks",
    "Unexplained Anomalies in the Sahara Desert", "Weird Plant Survival and Defense Mechanisms"
]

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

print(f"🚀 AutoContent OS v2: Scene-based Pipeline & Persistent Memory")
print(f"    ├─ Gekozen Onderwerp: '{TOPIC}'")
print(f"    ├─ Stem: '{CHOSEN_VOICE}'")
print(f"    └─ Output: '{output_file.name}'\n")

for old_clip in BASE_DIR.glob("temp_scene_*.mp4"):
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

# 1. GEMINI: SCRIPT, SCÈNES, FACT_NAME & METADATA
print("1/5 🧠 Genereren van uniek feit, scènes met zoekwoorden & metadata via Gemini AI...")
script_text = ""
scenes_data = []
youtube_metadata = {
    "title": f"Mind-Blowing Fact About {TOPIC}! #Shorts",
    "description": f"Learn a crazy fact about {TOPIC}!\n\n🤖 Note: Educational AI content.\n\n#Shorts #Facts",
    "tags": [TOPIC, "Facts", "Shorts"]
}

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        unique_seed = random.randint(10000000, 99999999)
        previous_facts_snippet = "\n".join([f"- {f}" for f in history_data.get("facts", [])[-40:]])
        
        prompt = (
            f"System Unique Hash ID: {unique_seed}\n"
            f"Create a viral YouTube Short about a completely unique, obscure, and specific micro-fact regarding '{TOPIC}'.\n"
            f"CRITICAL ANTI-DUPLICATE RULE: Do NOT repeat or resemble any of these previously used facts:\n{previous_facts_snippet}\n\n"
            f"Break the script down into 4 to 5 distinct chronological scenes. Each scene must have a short sentence segment and a hyper-specific English search keyword for Pexels stock video.\n\n"
            f"STRICT OUTPUT FORMAT (JSON only, no markdown, no backticks):\n"
            f"{{\n"
            f'  "fact_name": "Short unique name of the micro-fact (e.g. Immortal Jellyfish)",\n'
            f'  "script": "Full spoken text here...",\n'
            f'  "title": "Ultra catchy title containing the fact_name, max 55 chars, with emojis",\n'
            f'  "description": "Engaging description text including #Shorts and relevant hashtags.",\n'
            f'  "tags": ["tag1", "tag2", "tag3"],\n'
            f'  "scenes": [\n'
            f'    {{"text": "First sentence part...", "keyword": "hyper-specific physical action or object"}},\n'
            f'    {{"text": "Second sentence part...", "keyword": "hyper-specific environment or object"}},\n'
            f'    {{"text": "Third sentence part...", "keyword": "hyper-specific close up object"}},\n'
            f'    {{"text": "Fourth sentence part...", "keyword": "hyper-specific striking visual"}}\n'
            f'  ]\n'
            f"}}\n\n"
            f"RULES:\n"
            f"1. Total script length: STRICTLY 35 to 45 words.\n"
            f"2. Title must directly describe the exact micro-fact, never generic.\n"
            f"3. SCENE VISUAL MATCHING: Each scene's keyword must strictly match what is being said in that specific sentence fragment. No generic words like 'science' or 'space'.\n"
            f"4. HOOK: Start immediately with a shocking statement."
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
        fact_name = data.get("fact_name", TOPIC)
        scenes_data = data.get("scenes", [])
        
        raw_desc = data.get("description", f"Mind blowing fact about {TOPIC}!")
        ai_disclaimer = "\n\n🤖 Note: This video contains AI-generated content for educational and entertainment purposes."
        
        youtube_metadata = {
            "title": data.get("title", f"Insane {TOPIC} Fact! #Shorts"),
            "description": raw_desc + ai_disclaimer,
            "tags": data.get("tags", [TOPIC, "Shorts", "Facts"])
        }
        
        history_data["facts"].append(fact_name)
        history_data["titles"].append(youtube_metadata["title"])
        print("    └─ Gemini AI script, scènes & metadata succesvol gegenereerd!")
    except Exception as e:
        print(f"    ⚠️ Fout bij Gemini AI API ({e}), terugvallen op backup...")

if not script_text or not scenes_data:
    script_text = "Did you know time actually passes faster the higher you are from sea level? Your head ages fractionally faster than your feet! Subscribe for more insane facts!"
    fact_name = "Altitude Time Dilation"
    scenes_data = [
        {"text": "Did you know time actually passes faster", "keyword": "pocket watch mechanism macro"},
        {"text": "the higher you are from sea level?", "keyword": "mountain peak clouds aerial"},
        {"text": "Your head ages fractionally faster than your feet!", "keyword": "person walking stairs low angle"},
        {"text": "Subscribe for more insane facts!", "keyword": "neon subscribe button close up"}
    ]

history_data["scripts"].append(script_text)

with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(youtube_metadata, f, indent=2)

# 2. VOICE-OVER & ONDERTITELS GENEREREN
print("2/5 🎙️ Voice-over & ondertiteling genereren...")
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

# 3. SCENE-BASED B-ROLL OPHALEN VAN PEXELS
scene_clips = []
seen_video_ids_this_run = set()
global_used_ids = set(history_data.get("used_pexels_ids", []))

print(f"3/5 🎥 Scène-gebaseerde unieke videoclips ophalen via Pexels...")
headers = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}

total_scene_chars = sum(len(s["text"]) for s in scenes_data)
if total_scene_chars == 0:
    total_scene_chars = 1

for idx, scene in enumerate(scenes_data):
    kw = scene["keyword"]
    scene_duration = (len(scene["text"]) / total_scene_chars) * audio_duration
    scene_duration = max(scene_duration, 1.55)

    clip_path = BASE_DIR / f"temp_scene_{idx}.mp4"
    downloaded = False

    if PEXELS_API_KEY:
        try:
            url = f"https://api.pexels.com/videos/search?query={kw}&orientation=portrait&per_page=15"
            res = requests.get(url, headers=headers).json()
            if "videos" in res and len(res["videos"]) > 0:
                available_videos = [
                    v for v in res["videos"][:15] 
                    if v["id"] not in seen_video_ids_this_run and v["id"] not in global_used_ids
                ]
                if not available_videos:
                    available_videos = [v for v in res["videos"][:15] if v["id"] not in seen_video_ids_this_run]
                if not available_videos:
                    available_videos = res["videos"][:15]
                
                chosen_item = random.choice(available_videos)
                vid_id = chosen_item["id"]
                seen_video_ids_this_run.add(vid_id)
                global_used_ids.add(vid_id)
                history_data.setdefault("used_pexels_ids", []).append(vid_id)

                video_files = chosen_item["video_files"]
                best_video = next((v for v in video_files if v["quality"] == "hd" and "mp4" in v["file_type"]), video_files[0])
                
                vid_data = requests.get(best_video["link"])
                with open(clip_path, "wb") as f:
                    f.write(vid_data.content)
                scene_clips.append((clip_path, scene_duration))
                downloaded = True
        except Exception as e:
            print(f"    ⚠️ Kon geen Pexels clip ophalen voor scène {idx} ('{kw}'): {e}")

    if not downloaded:
        img_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1080&auto=format&fit=crop"
        img_res = requests.get(img_url)
        with open(bg_image, "wb") as f:
            f.write(img_res.content)
        scene_clips.append((bg_image, scene_duration))

history_data["used_pexels_ids"] = history_data["used_pexels_ids"][-150:]

# 4. EINDMONTAGE MET SCÈNE TIMINGS
print("4/5 🎬 Vloeiende eindmontage starten op basis van scènes...")
clean_ass_path = str(ass_file).replace(":", "\\:")
use_music = music_file.exists() and music_file.stat().st_size > 50000

filter_parts = []
cmd = [ffmpeg_exe, "-y"]

for i, (cf, dur) in enumerate(scene_clips):
    if cf == bg_image:
        cmd.extend(["-loop", "1", "-i", str(cf)])
    else:
        cmd.extend(["-stream_loop", "-1", "-i", str(cf)])

cmd.extend(["-i", str(audio_file)])
voice_idx = len(scene_clips)

if use_music:
    cmd.extend(["-i", str(music_file)])
    music_idx = len(scene_clips) + 1

concat_inputs = ""
for i, (cf, dur) in enumerate(scene_clips):
    if cf == bg_image:
        filter_parts.append(
            f"[{i}:v]scale=1280:2272,zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(iw/zoom/2)':d={int(dur*30)}:s=1080x1920,fps=30,trim=duration={dur:.2f}[v{i}]"
        )
    else:
        filter_parts.append(
            f"[{i}:v]trim=0:{dur:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{i}]"
        )
    concat_inputs += f"[v{i}]"

filter_parts.append(f"{concat_inputs}concat=n={len(scene_clips)}:v=1:a=0[vconcat]")
filter_parts.append(f"[vconcat]subtitles=filename='{clean_ass_path}'[vout]")

if use_music:
    filter_parts.append(f"[{voice_idx}:a]volume=1.0[vstem];[{music_idx}:a]volume=0.25[mstem];[vstem][mstem]amix=inputs=2:duration=first[aout]")

cmd.extend(["-filter_complex", ";".join(filter_parts)])
cmd.extend(["-map", "[vout]"])
if use_music:
    cmd.extend(["-map", "[aout]"])
else:
    cmd.extend(["-map", f"{voice_idx}:a:0"])

cmd.extend([
    "-t", f"{audio_duration:.2f}",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-b:a", "128k",
    "-pix_fmt", "yuv420p",
    str(output_file)
])

subprocess.run(cmd, check=True)

for cf, _ in scene_clips:
    if "temp_scene_" in str(cf):
        try:
            cf.unlink()
        except Exception:
            pass

# 5. AUTOMATISCHE YOUTUBE UPLOAD
print("5/5 📤 Automatisch uploaden naar YouTube...")
if Path("token.json").exists():
    try:
        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/youtube.upload"])
        
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": youtube_metadata["title"],
                "description": youtube_metadata["description"],
                "tags": youtube_metadata["tags"],
                "categoryId": "27"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(str(output_file), chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"    ├─ Upload voortgang: {int(status.progress() * 100)}%")

        print(f"    └─ 🎉 Succesvol gepubliceerd op YouTube! Video ID: {response.get('id')}")
    except Exception as e:
        print(f"    ❌ Fout bij YouTube upload: {e}")
else:
    print("    ⚠️ Geen token.json gevonden; video is alleen op GitHub opgeslagen.")

# 6. PERMANENT GEHEUGEN TERUGCOMMITTEERD NAAR GITHUB
print("6/6 💾 Permanent geheugen opslaan in GitHub repository...")
with open(history_file, "w", encoding="utf-8") as f:
    json.dump(history_data, f, indent=2)

try:
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", str(history_file)], check=True)
    subprocess.run(["git", "commit", "-m", f"chore: update history.json for topic {TOPIC} [skip ci]"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("    └─ ✅ History.json succesvol gepusht naar GitHub!")
except Exception as e:
    print(f"    ⚠️ Git push mislukt: {e}")

print(f"\n🎉 VOLLEDIGE RUN SUCCESVOL AFGEROND!")