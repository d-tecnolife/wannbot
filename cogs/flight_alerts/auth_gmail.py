import os

from config import GMAIL_SCOPES
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
credentials_json = os.path.join(root_dir, "credentials.json")
token_json = os.path.join(root_dir, "token.json")


def authenticate_gmail():
    creds = Credentials.from_authorized_user_file(token_json, GMAIL_SCOPES)
    service = build("gmail", "v1", credentials=creds)
    return service
