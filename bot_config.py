"""Non-sensitive wannbot behavior and command configuration."""

# Discord command routing
BOT_PREFIX = "!"
IMAGE_COMMAND = "im"
IMAGE_ALIASES = ("image",)
GOOGLE_ASK_COMMAND = "ask"
PERSONA_ASK_COMMAND = "askwann"

# Gemini persona used by PERSONA_ASK_COMMAND
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_THINKING_LEVEL = "medium"
GEMINI_MAX_CONTINUATIONS = 1
GEMINI_PERSONA = (
    "Answer like a dry, sarcastic spaceship computer while staying helpful."
)

# Google Flights alert behavior
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.modify",)
GMAIL_QUERY = "is:unread from:noreply-travel@google.com"
