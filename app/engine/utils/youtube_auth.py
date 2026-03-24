import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pathlib import Path
from config import OUTPUT_DIR


def get_youtube_client():
    creds = None

    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.force-ssl'
    ]

    SECRET_FILE_NAME = "client_secret.json"
    TOKEN_FILE_NAME = "token.pickle"

    # Use the synced directory in PROD, or project root in LOCAL
    if os.getenv("APP_ENV") == "production":
        base_path = Path(OUTPUT_DIR) # This will be /tmp/assets
    else:
        base_path = Path(__file__).resolve().parent.parent

    secret_path = base_path / SECRET_FILE_NAME
    token_path = base_path / TOKEN_FILE_NAME

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secret_path), SCOPES
            )
            creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)