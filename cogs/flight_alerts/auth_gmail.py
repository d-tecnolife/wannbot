import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GMAIL_SCOPES

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
credentials_json = os.path.join(root_dir, "credentials.json")
token_json = os.path.join(root_dir, "token.json")


def authenticate_gmail():
    creds = Credentials.from_authorized_user_file(token_json, GMAIL_SCOPES)
    if creds and not creds.valid:
        try:
            print(f"[{datetime.now()}] GMAIL AUTH: Token expired, refreshing..")
            creds.refresh(Request())
            print(f"{datetime.now()}] GMAIL AUTH: Token refreshed successfully.")
            with open(token_json, "w") as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"[{datetime.now()}] GMAIL AUTH: Token refresh failed: {e}")
            raise
    if not creds:
        raise Exception("GMAIL AUTH: Credentials invalid, please reauthenticate")
    service = build("gmail", "v1", credentials=creds)
    return service
