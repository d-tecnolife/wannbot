import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("bot_token")
ALERT_CHANNEL_ID = int(os.getenv("channel_id")

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
GMAIL_QUERY = 'is:unread from:googleflights-noreply@google.com'
