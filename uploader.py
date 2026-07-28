import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = Path(__file__).resolve().parent

def get_authenticated_service():
    creds = None
    token_file = BASE_DIR / "token.json"
    client_secret_file = BASE_DIR / "client_secret.json"

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret_file.exists():
                raise FileNotFoundError("❌ 'client_secret.json' niet gevonden in je map! Zorg dat het bestand zo heet.")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_short(video_path, title, description, tags):
    print(f"⬆️ Uploaden naar YouTube Shorts gestart: '{title}'...")
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],  # Max 100 karakters
            "description": description,
            "tags": tags,
            "categoryId": "28"  # Science & Technology
        },
        "status": {
            "privacyStatus": "public",
            "selfMade": True
        }
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   ├─ Voortgang: {int(status.progress() * 100)}%")

    print(f"🎉 SUCCES! Video staat live op YouTube Shorts! (Video ID: {response['id']})\n")
    return response['id']

if __name__ == "__main__":
    print("Uploader module geladen.")
