import time
import subprocess
import schedule
from pathlib import Path
from topic_generator import get_daily_topic

BASE_DIR = Path(__file__).resolve().parent

def run_pipeline():
    print("\n==================================================")
    print("⏰ AUTOMATISCHE RUN GESTART")
    print("==================================================")
    
    # 1. Genereer een vers onderwerp via Gemini
    topic = get_daily_topic()
    print(f"🎯 Gekozen Onderwerp: '{topic}'")
    
    # 2. Genereer de video + metadata
    try:
        print("🎬 Video & Metadata genereren...")
        cmd_gen = [str(BASE_DIR / "venv" / "bin" / "python"), str(BASE_DIR / "autocontent.py"), topic]
        subprocess.run(cmd_gen, check=True)
        print("✅ Video & Metadata succesvol gemaakt!")
    except Exception as e:
        print(f"❌ Fout tijdens videobuild: {e}")
        return

    # 3. Upload direct naar YouTube
    try:
        print("📤 Uploaden naar YouTube...")
        cmd_upload = [str(BASE_DIR / "venv" / "bin" / "python"), str(BASE_DIR / "upload.py")]
        subprocess.run(cmd_upload, check=True)
        print("🎉 Succesvol geüpload naar YouTube!")
    except Exception as e:
        print(f"❌ Fout tijdens uploaden: {e}")

    print("==================================================\n")

# Schedule instellen voor EU + US Piekuren (Nederlandse Tijd)
schedule.every().day.at("08:00").do(run_pipeline)
schedule.every().day.at("15:30").do(run_pipeline)
schedule.every().day.at("21:30").do(run_pipeline)

print("🚀 AutoContent OS Scheduler is Actief!")
print("📅 Ingeplande tijden (Nederlandse tijd):")
print("   ├─ 08:00 uur (EU Ochtend)")
print("   ├─ 15:30 uur (EU Middag / US Oostkust Ochtend)")
print("   └─ 21:30 uur (EU Avond / US Oostkust & Westkust Piek)")
print("\n💤 Script wacht op het volgende actiemoment... (Druk op Ctrl+C om te stoppen)\n")

while True:
    schedule.run_pending()
    time.sleep(30)