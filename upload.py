import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"

def get_authenticated_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_FILE.exists():
                print(f"❌ Fout: '{CLIENT_SECRET_FILE.name}' niet gevonden! Volg Stap 4 om deze aan te maken.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_videos():
    youtube = get_authenticated_service()
    if not youtube:
        return

    mp4_files = list(OUTPUT_DIR.glob("video_*.mp4"))
    if not mp4_files:
        print("ℹ️ Geen video's gevonden in de output/ map om te uploaden.")
        return

    print(f"🚀 {len(mp4_files)} video('s) gevonden in output/ map. Upload starten...\n")

    for video_file in mp4_files:
        json_file = video_file.with_suffix(".json")
        
        # Standaard metadata als JSON niet bestaat
        metadata = {
            "title": video_file.stem.replace("video_", "").replace("_", " "),
            "description": "AutoContent video #Shorts\n\n🤖 Note: AI-generated content.",
            "tags": ["Shorts", "Facts"]
        }
        
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        print(f"📤 Uploaden: '{metadata['title']}'...")

        body = {
            "snippet": {
                "title": metadata["title"][:100],
                "description": metadata["description"],
                "tags": metadata.get("tags", []),
                "categoryId": "27"  # Category 27 = Education
            },
            "status": {
                "privacyStatus": "private",  # Keuze: 'private', 'unlisted', of 'public'
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(str(video_file), chunksize=-1, resumable=True, mimetype="video/mp4")

        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            response = request.execute()
            print(f"   ✅ Succesvol geüpload! Video ID: {response.get('id')}\n")
            
            # Verplaats geüploade video naar uploaded/ map
            uploaded_dir = OUTPUT_DIR / "uploaded"
            uploaded_dir.mkdir(exist_ok=True)
            video_file.replace(uploaded_dir / video_file.name)
            if json_file.exists():
                json_file.replace(uploaded_dir / json_file.name)

        except Exception as e:
            print(f"   ❌ Fout bij uploaden van '{video_file.name}': {e}\n")

if __name__ == "__main__":
    upload_videos()