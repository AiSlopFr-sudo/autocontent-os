import os
import sys
import time
import random
import subprocess
from pathlib import Path
from uploader import upload_short

BASE_DIR = Path(__file__).resolve().parent

# 🎯 WACHTRIJ VAN ONDERWERPEN (Vul aan met wat je wilt!)
TOPICS = [
    "Space",
    "Artificial Intelligence",
    "Money",
    "Health",
    "Mindfulness",
    "Tech",
    "History"
]

# 🏷️ AUTOMATISCHE HASHTAGS & TITELS PER ONDERWERP
METADATA_MATRIX = {
    "Space": {
        "title_templates": [
            "Mind-Blowing Space Fact You Didn't Know! 🚀 #Shorts",
            "How Big Is The Universe Really? 🌌 #Shorts",
            "Unbelievable Secret About Outer Space! 🪐 #Shorts"
        ],
        "tags": ["space", "universe", "astronomy", "facts", "shorts", "science"],
        "hashtags": "#Shorts #Space #Astronomy #Science #Facts #Viral"
    },
    "AI": {
        "title_templates": [
            "The AI Revolution Is Happening Right Now! 🤖 #Shorts",
            "Is Artificial Intelligence Taking Over? ⚡ #Shorts",
            "Mind-Blowing Fact About AI Future! 🚀 #Shorts"
        ],
        "tags": ["ai", "artificialintelligence", "tech", "future", "shorts"],
        "hashtags": "#Shorts #AI #Tech #Future #Science #Technology"
    },
    "Money": {
        "title_templates": [
            "The Eighth Wonder Of The World Revealed 💰 #Shorts",
            "How Smart People Build Wealth Silently 📈 #Shorts",
            "Financial Rule Everyone Must Know! 💸 #Shorts"
        ],
        "tags": ["money", "finance", "investing", "wealth", "shorts"],
        "hashtags": "#Shorts #Money #Finance #Investing #Wealth #Mindset"
    },
    "Health": {
        "title_templates": [
            "Do This Every Morning For Brain Boost! 🧠 #Shorts",
            "Simple Trick To Transform Your Health 🌿 #Shorts",
            "Did You Know This Secrets About Metabolism? 💧 #Shorts"
        ],
        "tags": ["health", "biohacking", "wellness", "mindset", "shorts"],
        "hashtags": "#Shorts #Health #Wellness #Mindset #Lifestyle"
    },
    "Default": {
        "title_templates": [
            "Mind-Blowing Fact Of The Day! 💡 #Shorts",
            "Did You Know This Crazy Fact? 🤯 #Shorts"
        ],
        "tags": ["facts", "didyouknow", "science", "viral", "shorts"],
        "hashtags": "#Shorts #Facts #DidYouKnow #Viral #Interesting"
    }
}

def generate_metadata(topic):
    meta_key = next((k for k in METADATA_MATRIX if k.lower() in topic.lower()), "Default")
    data = METADATA_MATRIX[meta_key]

    title = random.choice(data["title_templates"])
    description = (
        f"Discover this mind-blowing truth about {topic}!\n\n"
        f"Subscribe for daily facts and automated insights.\n\n"
        f"{data['hashtags']}"
    )
    return title, description, data["tags"]

def run_autopilot(topic=None):
    if not topic:
        topic = random.choice(TOPICS)

    safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
    video_file = BASE_DIR / f"video_{safe_topic}.mp4"

    print(f"═════════════════════════════════════════════════════════")
    print(f"🤖 AUTOPILOT OS: Nieuwe cyclus gestart voor '{topic}'")
    print(f"═════════════════════════════════════════════════════════\n")

    # 1. Genereer video
    cmd = [sys.executable, "autocontent.py", topic]
    subprocess.run(cmd, check=True)

    if not video_file.exists():
        print("❌ Fout: Gegenereerde video niet gevonden!")
        return

    # 2. Genereer hashtags, titel en beschrijving
    title, description, tags = generate_metadata(topic)
    print(f"📝 Gegenereerde Titel: \"{title}\"")
    print(f"🏷️  Hashtags & Tags ingesteld.\n")

    # 3. Upload naar YouTube Shorts
    try:
        upload_short(video_file, title, description, tags)
    except Exception as e:
        print(f"❌ Upload mislukt: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_autopilot(sys.argv[1])
    else:
        run_autopilot()
