import os
import subprocess
import requests
import imageio_ffmpeg

print("🚀 AutoContent OS: MVP Pipeline gestart!\n")

# A. SCRIPT AGENT
print("1/4 📝 Testscript geladen...")
script_text = "Kunstmatige intelligentie ontwikkelt zich sneller dan ooit. Wist je dat AI binnen enkele seconden complete video's kan maken?"
print(f"   └─ Script: \"{script_text}\"\n")

# B. VOICE AGENT (Edge-TTS)
print("2/4 🎙️ Voice-over genereren via Edge-TTS...")
try:
    cmd_tts = [
        "edge-tts",
        "--text", script_text,
        "--voice", "nl-NL-ColetteNeural",
        "--write-media", "audio.mp3"
    ]
    subprocess.run(cmd_tts, check=True)
    print("   └─ Audio opgeslagen als 'audio.mp3'\n")
except Exception as e:
    print(f"   ❌ Fout bij Edge-TTS: {e}")
    exit()

# C. VISUAL AGENT (Gratis HD Tech Afbeelding)
print("3/4 🎨 Gratis HD-afbeelding ophalen...")
img_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1080&auto=format&fit=crop"
headers = {"User-Agent": "Mozilla/5.0"}
img_res = requests.get(img_url, headers=headers)

with open("image.jpg", "wb") as f:
    f.write(img_res.content)
print("   └─ Afbeelding opgeslagen als 'image.jpg'\n")

# D. RENDER AGENT (FFmpeg via imageio-ffmpeg)
print("4/4 🎬 Video monteren met FFmpeg...")
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

cmd = [
    ffmpeg_exe, "-y",
    "-loop", "1",
    "-i", "image.jpg",
    "-i", "audio.mp3",
    "-c:v", "libx264",
    "-tune", "stillimage",
    "-c:a", "aac",
    "-b:a", "192k",
    "-pix_fmt", "yuv420p",
    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
    "-shortest",
    "output.mp4"
]

subprocess.run(cmd, check=True)
print("\n🎉 GEFELICITEERD! Je allereerste AI-video is klaar!")
print("👉 Typ 'open .' in je Terminal om het bestand 'output.mp4' te bekijken!")
