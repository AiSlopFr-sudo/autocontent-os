import os
import sys
import time
import subprocess
from pathlib import Path

TOPICS = [
    "Quantum Computing",
    "Deep Sea Creatures",
    "Ancient Egypt Secrets",
    "Artificial General Intelligence",
    "Black Holes"
]

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

print("==================================================")
print(f"🚀 AutoContent OS: Batch Video & Metadata Generation")
print(f"📦 Totaal aantal video's te maken: {len(TOPICS)}")
print(f"📁 Output map: {OUTPUT_DIR.name}/")
print("==================================================\n")

successful = 0
failed = 0

for index, topic in enumerate(TOPICS, 1):
    print(f"--------------------------------------------------")
    print(f"▶️  [{index}/{len(TOPICS)}] Starten met onderwerp: '{topic}'")
    print(f"--------------------------------------------------")
    
    try:
        cmd = [sys.executable, str(BASE_DIR / "autocontent.py"), topic]
        subprocess.run(cmd, check=True)
        
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        generated_video = BASE_DIR / f"video_{safe_topic}.mp4"
        generated_json = BASE_DIR / f"video_{safe_topic}.json"
        
        if generated_video.exists():
            target_video = OUTPUT_DIR / generated_video.name
            generated_video.replace(target_video)
            
            if generated_json.exists():
                target_json = OUTPUT_DIR / generated_json.name
                generated_json.replace(target_json)
                
            print(f"✅ Gelukt! Video & Metadata verplaatst naar: {OUTPUT_DIR.name}/")
            successful += 1
        else:
            print(f"⚠️ Waarschuwing: Videobestand niet gevonden voor '{topic}'.")
            failed += 1

    except Exception as e:
        print(f"❌ Fout bij '{topic}': {e}")
        failed += 1

    if index < len(TOPICS):
        print("\n⏳ 5 seconden pauze voor het volgende onderwerp...\n")
        time.sleep(5)

print("\n==================================================")
print("🎉 BATCH VERWERKING VOLTOOID!")
print(f"📊 Resultaat: {successful} gelukt, {failed} mislukt.")
print(f"📂 Bekijk je video's + metadata in: {OUTPUT_DIR}/")
print("==================================================")