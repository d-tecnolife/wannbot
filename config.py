import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("bot_token")
ALERT_CHANNEL_ID = int(os.getenv("channel_id", "0"))
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
AI_MODEL = os.getenv(
    "AI_MODEL", "cognitivecomputations/dolphin3.0-mistral-24b:free"
)
AI_FALLBACK_API_KEY = os.getenv("AI_FALLBACK_API_KEY") or os.getenv("GROQ_API_KEY")
AI_FALLBACK_BASE_URL = os.getenv(
    "AI_FALLBACK_BASE_URL", "https://api.groq.com/openai/v1"
)
AI_FALLBACK_MODEL = os.getenv("AI_FALLBACK_MODEL", "qwen/qwen3.8-27b")
