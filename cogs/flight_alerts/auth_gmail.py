import os
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from bot_config import GMAIL_SCOPES

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
credentials_json = os.path.join(root_dir, "credentials.json")
token_json = os.path.join(root_dir, "token.json")
logger = logging.getLogger("wannbot.gmail")


def authenticate_gmail():
    creds = Credentials.from_authorized_user_file(token_json, GMAIL_SCOPES)
    if creds and not creds.valid:
        try:
            logger.info("Gmail token expired; refreshing")
            creds.refresh(Request())
            logger.info("Gmail token refreshed successfully")
        except Exception:
            logger.exception("Gmail token refresh failed")
            raise
        try:
            with open(token_json, "w") as token:
                token.write(creds.to_json())
        except OSError:
            logger.warning(
                "Gmail token refreshed in memory but could not be saved to %s; "
                "mount that file writable to persist it",
                token_json,
                exc_info=True,
            )
    if not creds:
        raise Exception("GMAIL AUTH: Credentials invalid, please reauthenticate")
    service = build("gmail", "v1", credentials=creds)
    return service
