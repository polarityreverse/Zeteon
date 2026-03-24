import os
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config_lambda import TOKEN_PICKLE, CLIENT_SECRET_JSON

def get_youtube_client():
    """
    Returns an authorized YouTube API client using the baked-in pickle file.
    """
    credentials = None

    # 1. Load the token from the baked-in pickle file
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            credentials = pickle.load(token)

    # 2. If credentials are expired, refresh them
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # This requires the client_secret.json to be present in the Docker image
            credentials.refresh(Request())
        else:
            raise Exception(
                "YouTube Token is invalid or missing. "
                "Please generate a new token.pickle locally and rebuild the Docker image."
            )

    # 3. Build the service
    return build("youtube", "v3", credentials=credentials)