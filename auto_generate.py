import os
import subprocess
import requests
import imageio_ffmpeg

print("🚀 AutoContent OS: High-Engagement English Pipeline\n")

# 1. ENGELS SCRIPT
print("1/4 📝 Engelse content laden...")
script_text = "Did you know that Artificial Intelligence can now read brainwaves and turn them into text with over eighty percent accuracy? The future is happening much faster than we think."
print(f"   └─ Script: \"{script_text}\"\n")

# 2. ENGELSE AI-VOICE (Christopher Neural - Edge-TTS)
print("2/4 🎙️ Engelse voice-over genereren (Edge-TTS)...")
try:
    cmd_tts = [
        "edge-tts",
        "--text", script_text,
        "--voice", "en-US-ChristopherNeural",
        "--write-media", "audio.mp3"
    ]
    subprocess.run(cmd_tts, check=True)
    print("   └─ Engelse audio opgeslagen als 'audio.mp3'\n")
except Exception as e:
    print(f"   ❌ Fout bij spraak: {e}")
    exit()

# 3. BEWEGEND BEELD (HD Motion Video of Camera Zoom Motion)
print("3/4 🎥 Dynamische achtergrond ophalen...")
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Betrouwbare HD Abstract Network Motion Video (Wikimedia Commons)
video_url = "https://upload.wikimedia.org/wikipedia/commons/transcoded/f/f0/Network_connections_abstract.ogv/Network_connections_abstract.ogv.720p.vp9.webm"

use_video = False
try:
    res = requests.get(video_url, headers=headers, timeout=10)
    # Check of het bestand echt een video is (>100KB)
    if res.status_code == 200 and len(res.content) > 100000:
        with open("background.webm", "wb") as f:
            f.write(res.content)
        use_video = True
        print("   └─ Bewegende HD-videoclip opgeslagen als 'background.webm'\n")
except Exception as e:
    print(f"   ⚠️ Videodownload overgeslagen ({e})")

if not use_video:
    print("   └─ Gebruik geanimeerde Ken Burns camera-zoom op HD Tech Visual...")
    img_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1080&auto=format&fit=crop"
    img_res = requests.get(img_url, headers=headers)
    with open("background.jpg", "wb") as f:
        f.write(img_res.content)

# 4. RENDER ENGINE (FFmpeg)
print("4/4 🎬 Video monteren met bewegend beeld...")
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

if use_video:
    cmd = [
        ffmpeg_exe, "-y",
        "-stream_loop", "-1",
        "-i", "background.webm",
        "-i", "audio.mp3",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-shortest",
        "output_english.mp4"
    ]
else:
    # FFmpeg Ken Burns slow-zoom effect (langzaam vloeiend inzoomen)
    cmd = [
        ffmpeg_exe, "-y",
        "-loop", "1",
        "-i", "background.jpg",
        "-i", "audio.mp3",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1280:2272,zoompan=z='min(zoom+0.0015,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=25*30:s=1080x1920",
        "-shortest",
        "output_english.mp4"
    ]

subprocess.run(cmd, check=True)
print("\n🎉 KLAAR! Je Engelse video met bewegend beeld staat voor je klaar!")
print("👉 Typ 'open .' om het bestand 'output_english.mp4' te bekijken!")
