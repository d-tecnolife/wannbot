import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("bot_token")
ALERT_CHANNEL_ID = int(os.getenv("channel_id", "0"))
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_PERSONA = os.getenv("GEMINI_PERSONA", "").strip()

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
GMAIL_QUERY = "is:unread from:noreply-travel@google.com"
