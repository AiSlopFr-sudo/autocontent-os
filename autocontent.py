"""
AutoContent OS v3 — wijzigingen t.o.v. v2 (zie chat voor volledige uitleg):

1. Herhaling van onderwerpen/feiten:
   - git push gebeurt nu met fetch+rebase, retries, en een zichtbare
     "::error::" annotatie in de GitHub Actions-log als het écht niet
     lukt — in plaats van een silent "except: print warning" die het
     probleem verborgen hield.
   - Nieuwe anti-duplicate check (difflib) met een retry-loop rond de
     Gemini-call op zowel fact_name als script, plus een "topic_facts"
     geschiedenis per onderwerp voor gerichtere context.

2. Niet-passende titels:
   - Titel/beschrijving/tags komen nu uit een TWEEDE, aparte Gemini-call
     die het AFGERONDE script als input krijgt (i.p.v. gokken vóórdat
     het script af is), met expliciete goed/fout-voorbeelden en een
     "benoem eerst de kern-verrassing"-aanpak.

3. Beelden die niet passen bij de tekst:
   - Scène-duur wordt nu berekend met de ECHTE TTS word-boundary
     timestamps (edge_tts library i.p.v. de CLI + VTT-regex-parsing),
     in plaats van een schatting op basis van karakterlengte.
   - Ondertitels worden uit diezelfde timestamps opgebouwd (geen regex
     meer nodig).
   - Pexels-selectie kreeg een bredere backup-keyword per scène, en
     geeft voorkeur aan relevantere (eerdere) en lang-genoege resultaten
     i.p.v. een volledig willekeurige keuze uit de top 15.
"""

import os
import sys
import re
import json
import random
import time
import asyncio
import difflib
import subprocess
import requests
import edge_tts
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
    "used_pexels_ids": [],
    "topic_facts": {}  # NIEUW: {topic: [fact_name, ...]} voor gerichte anti-duplicate context
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
GIT_BRANCH = os.getenv("GITHUB_REF_NAME", "main")  # GitHub Actions zet dit automatisch

random.seed(time.time_ns() ^ os.getpid())

safe_topic = "".join(c for c in TOPIC if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
timestamp_id = int(time.time())
output_file = BASE_DIR / f"video_{safe_topic}_{timestamp_id}.mp4"
metadata_file = BASE_DIR / f"video_{safe_topic}_{timestamp_id}.json"
audio_file = BASE_DIR / "audio.mp3"
music_file = BASE_DIR / "bg_music.mp3"
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

print(f"🚀 AutoContent OS v3: Precisie-timing, Anti-Duplicate Engine & Robuuste Git-Sync")
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


def is_too_similar(candidate, existing_list, threshold=0.6):
    """
    Vergelijkt `candidate` met elk item in `existing_list` via difflib en
    geeft (True, meest_gelijkende_match) terug zodra de gelijkenis-ratio
    de drempel overschrijdt. Geen perfecte semantische dedup, maar een
    goedkope, dependency-vrije heuristiek die de meeste "bijna identieke
    feitjes" opvangt waar een pure prompt-instructie soms overheen leest.
    """
    if not candidate:
        return False, None
    candidate_norm = candidate.lower().strip()
    best_ratio = 0.0
    best_match = None
    for existing in existing_list:
        if not existing:
            continue
        ratio = difflib.SequenceMatcher(None, candidate_norm, existing.lower().strip()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = existing
    if best_ratio >= threshold:
        return True, best_match
    return False, None


# 1. GEMINI: UNIEK FEIT, SCRIPT & SCÈNES (met anti-duplicate retry-loop)
print("1/6 🧠 Genereren van uniek feit & scènes via Gemini AI...")
script_text = ""
scenes_data = []
fact_name = TOPIC

if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    topic_history = history_data.get("topic_facts", {}).get(TOPIC, [])
    recent_global_facts = history_data.get("facts", [])[-60:]
    extra_avoid = []
    MAX_GEN_ATTEMPTS = 3

    for attempt in range(1, MAX_GEN_ATTEMPTS + 1):
        try:
            unique_seed = random.randint(10000000, 99999999)
            avoid_list = list(dict.fromkeys(topic_history + recent_global_facts + extra_avoid))
            previous_facts_snippet = "\n".join(f"- {f}" for f in avoid_list[-80:])

            prompt = (
                f"System Unique Hash ID: {unique_seed}\n"
                f"Create a viral YouTube Short about a completely unique, obscure, and specific micro-fact regarding '{TOPIC}'.\n"
                f"CRITICAL ANTI-DUPLICATE RULE: Do NOT repeat, rephrase, or closely resemble ANY of these previously "
                f"used facts (this list specifically includes everything already used about '{TOPIC}'):\n{previous_facts_snippet}\n\n"
                f"Break the script down into 4 to 5 distinct chronological scenes. Each scene must have a short "
                f"sentence segment, a hyper-specific English search keyword for Pexels stock video, and a broader "
                f"backup keyword.\n\n"
                f"STRICT OUTPUT FORMAT (JSON only, no markdown, no backticks):\n"
                f"{{\n"
                f'  "fact_name": "Short unique name of the micro-fact (e.g. Immortal Jellyfish)",\n'
                f'  "script": "Full spoken text here...",\n'
                f'  "scenes": [\n'
                f'    {{"text": "First sentence part...", "keyword": "hyper-specific physical action or object", "keyword_alt": "broader safe backup keyword"}},\n'
                f'    {{"text": "Second sentence part...", "keyword": "hyper-specific environment or object", "keyword_alt": "broader safe backup keyword"}},\n'
                f'    {{"text": "Third sentence part...", "keyword": "hyper-specific close up object", "keyword_alt": "broader safe backup keyword"}},\n'
                f'    {{"text": "Fourth sentence part...", "keyword": "hyper-specific striking visual", "keyword_alt": "broader safe backup keyword"}}\n'
                f'  ]\n'
                f"}}\n\n"
                f"RULES:\n"
                f"1. Total script length: STRICTLY 35 to 45 words.\n"
                f"2. SCENE VISUAL MATCHING: Each scene's keyword must strictly match what is being said in that "
                f"specific sentence fragment. No generic words like 'science' or 'space'. keyword_alt must be a "
                f"safer, more generic version of the same idea (e.g. keyword='pocket watch gear mechanism macro' -> "
                f"keyword_alt='antique clock closeup'), used only as a fallback if the specific keyword returns nothing.\n"
                f"3. HOOK: Start immediately with a shocking statement.\n"
                f"4. REMEMBER THE ANTI-DUPLICATE RULE ABOVE — this is the most important constraint. A repeated fact "
                f"is a failed response."
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
            candidate_fact = data.get("fact_name", TOPIC).strip()
            candidate_script = data.get("script", "").strip().replace('\n', ' ')
            candidate_scenes = data.get("scenes", [])

            dup_fact, match1 = is_too_similar(candidate_fact, topic_history + recent_global_facts, threshold=0.6)
            dup_script, match2 = is_too_similar(candidate_script, history_data.get("scripts", [])[-60:], threshold=0.55)

            if candidate_script and candidate_scenes and not dup_fact and not dup_script:
                script_text = candidate_script
                fact_name = candidate_fact
                scenes_data = candidate_scenes
                print(f"    └─ Gemini AI script & scènes succesvol gegenereerd (poging {attempt}): '{fact_name}'")
                break

            reason = match1 or match2 or "onvolledige data"
            print(f"    ⚠️ Poging {attempt}/{MAX_GEN_ATTEMPTS}: te gelijkend op eerder feit ('{reason}'), opnieuw genereren...")
            if candidate_fact:
                extra_avoid.append(candidate_fact)

            if attempt == MAX_GEN_ATTEMPTS and candidate_script and candidate_scenes:
                script_text = candidate_script
                fact_name = candidate_fact
                scenes_data = candidate_scenes
                print("    ⚠️ Alle pogingen leken op eerdere feiten; laatste poging alsnog geaccepteerd.")
        except Exception as e:
            print(f"    ⚠️ Fout bij Gemini AI poging {attempt} ({e})")

if not script_text or not scenes_data:
    script_text = "Did you know time actually passes faster the higher you are from sea level? Your head ages fractionally faster than your feet! Subscribe for more insane facts!"
    fact_name = "Altitude Time Dilation"
    scenes_data = [
        {"text": "Did you know time actually passes faster", "keyword": "pocket watch mechanism macro", "keyword_alt": "antique clock closeup"},
        {"text": "the higher you are from sea level?", "keyword": "mountain peak clouds aerial", "keyword_alt": "mountain landscape wide shot"},
        {"text": "Your head ages fractionally faster than your feet!", "keyword": "person walking stairs low angle", "keyword_alt": "person walking city street"},
        {"text": "Subscribe for more insane facts!", "keyword": "neon subscribe button close up", "keyword_alt": "neon sign close up"}
    ]
    print("    └─ ⚠️ Terugvallen op statische backup-fact (Gemini gaf geen bruikbaar resultaat).")

history_data["facts"].append(fact_name)
history_data["scripts"].append(script_text)
history_data.setdefault("topic_facts", {}).setdefault(TOPIC, []).append(fact_name)
history_data["topic_facts"][TOPIC] = history_data["topic_facts"][TOPIC][-30:]
history_data["facts"] = history_data["facts"][-300:]
history_data["scripts"] = history_data["scripts"][-150:]


# 1b. GEMINI: LOSSTAANDE, GERICHTE TITEL- & METADATA-GENERATIE
print("    🧠 Genereren van gerichte titel & metadata...")
youtube_metadata = {
    "title": f"Insane {fact_name} Fact! 🤯 #Shorts",
    "description": f"Learn a crazy fact about {fact_name}!\n\n🤖 Note: This video contains AI-generated content for educational and entertainment purposes.\n\n#Shorts #Facts",
    "tags": [TOPIC, fact_name, "Facts", "Shorts"]
}

if GEMINI_API_KEY:
    try:
        title_prompt = (
            f"Here is a FINISHED YouTube Shorts script about a micro-fact. Your only task is to write a title and "
            f"metadata that name the SPECIFIC, surprising element from THIS script.\n\n"
            f"Fact name: {fact_name}\n"
            f"Full voice-over text: \"{script_text}\"\n\n"
            f"❌ TOO GENERIC (NEVER DO THIS): 'Insane Space Fact! 🤯', 'You Won't Believe This! 😱', "
            f"'Amazing Facts About {TOPIC}'\n"
            f"✅ SPECIFIC ENOUGH (DO THIS): a title that names the exact, concrete detail from the text above.\n\n"
            f"Method: first identify the core surprise ('hook') of the text above in 5-8 words, then build the "
            f"title FROM that hook — not from the general topic '{TOPIC}'.\n\n"
            f"STRICT OUTPUT FORMAT (JSON only, no markdown, no backticks):\n"
            f"{{\n"
            f'  "hook": "core surprise from the text in 5-8 words",\n'
            f'  "title": "Ultra catchy title containing the concrete detail, max 55 chars, with emoji",\n'
            f'  "description": "Engaging description with #Shorts and relevant hashtags",\n'
            f'  "tags": ["tag1", "tag2", "tag3"]\n'
            f"}}"
        )
        title_response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=title_prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.9
            }
        )
        title_data = json.loads(title_response.text)
        raw_desc = title_data.get("description", f"Mind blowing fact about {fact_name}!")
        ai_disclaimer = "\n\n🤖 Note: This video contains AI-generated content for educational and entertainment purposes."
        youtube_metadata = {
            "title": title_data.get("title", youtube_metadata["title"]),
            "description": raw_desc + ai_disclaimer,
            "tags": title_data.get("tags", youtube_metadata["tags"])
        }
        print(f"    └─ Titel gegenereerd: '{youtube_metadata['title']}'")
    except Exception as e:
        print(f"    ⚠️ Fout bij titel-generatie ({e}), terugvallen op standaardtitel...")

history_data["titles"].append(youtube_metadata["title"])
history_data["titles"] = history_data["titles"][-300:]

with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(youtube_metadata, f, indent=2)

# 2. VOICE-OVER MET WOORD-NAUWKEURIGE TIMING
print("2/6 🎙️ Voice-over genereren met exacte word-boundary timing...")


async def _tts_stream_with_word_timings(text, voice, audio_out_path):
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, boundary="WordBoundary")
    except TypeError:
        communicate = edge_tts.Communicate(text=text, voice=voice)

    word_timings = []
    with open(audio_out_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_s = chunk["offset"] / 10_000_000
                dur_s = chunk["duration"] / 10_000_000
                word_timings.append({"text": chunk["text"], "start": start_s, "end": start_s + dur_s})
    return word_timings


def generate_tts_with_word_timings(text, voice, audio_out_path):
    return asyncio.run(_tts_stream_with_word_timings(text, voice, audio_out_path))


try:
    word_timings = generate_tts_with_word_timings(script_text, CHOSEN_VOICE, audio_file)
    if not word_timings:
        print("    ⚠️ Geen WordBoundary-data ontvangen; val terug op tekstlengte-schatting voor scène-timing.")
except Exception as e:
    print(f"    ❌ Fout bij spraakgeneratie: {e}")
    sys.exit(1)

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()


def get_audio_duration(file_path):
    cmd = [ffmpeg_exe, "-i", str(file_path)]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if match:
        h, m, s = match.groups()
        return float(h) * 3600 + float(m) * 60 + float(s)
    return 15.0


audio_duration = get_audio_duration(audio_file)


def format_time_ass(seconds):
    seconds = max(seconds, 0.0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs -= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


try:
    dialogues = []
    max_words = 3
    if word_timings:
        for i in range(0, len(word_timings), max_words):
            group = word_timings[i:i + max_words]
            if not group:
                continue
            c_start = group[0]["start"]
            c_end = group[-1]["end"]
            text = " ".join(w["text"] for w in group)
            dialogues.append(f"Dialogue: 0,{format_time_ass(c_start)},{format_time_ass(c_end)},Default,,0,0,0,,{text}")
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
    print(f"    ⚠️ Fout bij ondertitel-opbouw: {e}")


def allocate_scene_timings(scenes, timings, total_duration):
    if not timings:
        total_chars = sum(len(s.get("text", "")) for s in scenes) or 1
        out = []
        cursor = 0.0
        for s in scenes:
            dur = max((len(s.get("text", "")) / total_chars) * total_duration, 1.2)
            out.append((cursor, cursor + dur))
            cursor += dur
        return out

    n_words_total = len(timings)
    word_counts = [max(len(s.get("text", "").split()), 1) for s in scenes]

    start_indices = [0]
    for c in word_counts[:-1]:
        start_indices.append(min(start_indices[-1] + c, n_words_total))

    cut_points = [timings[idx]["start"] if idx < n_words_total else total_duration for idx in start_indices]
    cut_points[0] = 0.0
    cut_points.append(total_duration)

    out = []
    for i in range(len(scenes)):
        start_t = cut_points[i]
        end_t = max(cut_points[i + 1], start_t + 0.4)
        out.append((start_t, end_t))
    return out


scene_time_ranges = allocate_scene_timings(scenes_data, word_timings, audio_duration)

scene_clips = []
seen_video_ids_this_run = set()
global_used_ids = set(history_data.get("used_pexels_ids", []))

print("3/6 🎥 Scène-gebaseerde unieke videoclips ophalen via Pexels (met precisie-timing)...")
pexels_headers = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}


def pick_pexels_clip(primary_kw, alt_kw, min_duration, seen_ids, used_ids, headers):
    for kw in [k for k in (primary_kw, alt_kw) if k]:
        try:
            url = f"https://api.pexels.com/videos/search?query={kw}&orientation=portrait&per_page=15"
            res = requests.get(url, headers=headers, timeout=15).json()
            videos = res.get("videos", [])
            if not videos:
                continue

            top_candidates = videos[:8]
            fresh = [v for v in top_candidates if v["id"] not in seen_ids and v["id"] not in used_ids]
            if not fresh:
                fresh = [v for v in top_candidates if v["id"] not in seen_ids]
            if not fresh:
                fresh = top_candidates

            long_enough = [v for v in fresh if v.get("duration", 0) >= min_duration]
            pool = long_enough or fresh

            weights = [2 if idx < max(len(pool) // 2, 1) else 1 for idx in range(len(pool))]
            chosen = random.choices(pool, weights=weights, k=1)[0]
            return chosen, kw
        except Exception as e:
            print(f"    ⚠️ Pexels-fout bij '{kw}': {e}")
            continue
    return None, None


for idx, scene in enumerate(scenes_data):
    start_t, end_t = scene_time_ranges[idx] if idx < len(scene_time_ranges) else (0.0, 2.0)
    scene_duration = max(end_t - start_t, 0.6)

    kw = scene.get("keyword", TOPIC)
    kw_alt = scene.get("keyword_alt", TOPIC)
    clip_path = BASE_DIR / f"temp_scene_{idx}.mp4"
    downloaded = False

    if PEXELS_API_KEY:
        chosen_item, used_kw = pick_pexels_clip(
            kw, kw_alt, scene_duration, seen_video_ids_this_run, global_used_ids, pexels_headers
        )
        if chosen_item:
            vid_id = chosen_item["id"]
            seen_video_ids_this_run.add(vid_id)
            global_used_ids.add(vid_id)
            history_data.setdefault("used_pexels_ids", []).append(vid_id)

            video_files = chosen_item["video_files"]
            best_video = next((v for v in video_files if v["quality"] == "hd" and "mp4" in v["file_type"]), video_files[0])
            try:
                vid_data = requests.get(best_video["link"], timeout=30)
                with open(clip_path, "wb") as f:
                    f.write(vid_data.content)
                scene_clips.append((clip_path, scene_duration))
                downloaded = True
            except Exception as e:
                print(f"    ⚠️ Kon Pexels-clip niet downloaden voor scène {idx}: {e}")

    if not downloaded:
        img_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1080&auto=format&fit=crop"
        img_res = requests.get(img_url, timeout=15)
        with open(bg_image, "wb") as f:
            f.write(img_res.content)
        scene_clips.append((bg_image, scene_duration))

history_data["used_pexels_ids"] = history_data["used_pexels_ids"][-150:]

# 4. EINDMONTAGE MET SCÈNE TIMINGS
print("4/6 🎬 Vloeiende eindmontage starten op basis van scènes...")
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
print("5/6 📤 Automatisch uploaden naar YouTube...")
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


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def commit_and_push_history():
    _run(["git", "config", "user.name", "github-actions[bot]"])
    _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])

    status = _run(["git", "status", "--porcelain", str(history_file)])
    if not status.stdout.strip():
        print("    └─ ℹ️ Geen wijzigingen in history.json, commit overgeslagen.")
        return True

    _run(["git", "add", str(history_file)])
    commit_res = _run(["git", "commit", "-m", f"chore: update history.json for topic {TOPIC} [skip ci]"])
    if commit_res.returncode != 0:
        print(f"    ⚠️ Commit mislukt: {commit_res.stderr.strip()}")
        return False

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        push_res = _run(["git", "push", "origin", f"HEAD:{GIT_BRANCH}"])
        if push_res.returncode == 0:
            print("    └─ ✅ History.json succesvol gepusht naar GitHub!")
            return True

        print(f"    ⚠️ Push poging {attempt}/{max_retries} mislukt: {push_res.stderr.strip()}")
        if attempt < max_retries:
            _run(["git", "fetch", "origin", GIT_BRANCH])
            rebase_res = _run(["git", "rebase", f"origin/{GIT_BRANCH}"])
            if rebase_res.returncode != 0:
                _run(["git", "rebase", "--abort"])
            time.sleep(2 * attempt)

    print(
        "::error::Kon history.json niet pushen na meerdere pogingen. Controleer: "
        "1) 'permissions: contents: write' in je workflow YAML (of Settings > Actions > "
        "General > Workflow permissions > Read and write permissions), "
        "2) branch protection rules op deze branch, "
        "3) of er geen overlappende runs tegelijk pushen (zet evt. een 'concurrency:' block in je workflow)."
    )
    return False


try:
    commit_and_push_history()
except Exception as e:
    print(f"::error::Onverwachte fout bij git push: {e}")

print("\n🎉 VOLLEDIGE RUN SUCCESVOL AFGEROND!")