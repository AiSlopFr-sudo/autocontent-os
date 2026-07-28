import os
import json
import random
from pathlib import Path
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CATEGORIES = [
    "Oddly Satisfying Processes (ASMR, Crafting, Kinetic Sand, Fluid Dynamics)",
    "Deep Ocean & Cosmic Mysteries",
    "Mind-Blowing Science & Technology Facts",
    "Unbelievable History & Forgotten Secrets",
    "Psychology Tricks & Human Brain Secrets"
]

def get_daily_topic():
    category = random.choice(CATEGORIES)
    if not GEMINI_API_KEY:
        return category

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = (
            f"Give me 1 single highly engaging and viral YouTube Short topic idea in the category: '{category}'.\n"
            f"Requirements:\n"
            f"- Output ONLY the topic title in 2-5 English words.\n"
            f"- No quotation marks, no punctuation, no preamble.\n"
            f"Example output: Kinetic Sand Physics"
        )
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        topic = response.text.strip().replace('"', '').replace("'", "")
        return topic if topic else "Satisfying Crafts"
    except Exception as e:
        print(f"⚠️ Fout bij topic generator ({e}), fallback naar categorie.")
        return category

if __name__ == "__main__":
    print(f"Gegenereerd onderwerp: {get_daily_topic()}")