import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("bot_token")
ALERT_CHANNEL_ID = int(os.getenv("channel_id", "0"))
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
