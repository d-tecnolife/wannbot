"""Non-sensitive wannbot behavior and command configuration."""

# Discord command routing
BOT_PREFIX = "!"
IMAGE_COMMAND = "im"
IMAGE_ALIASES = ("image",)
GOOGLE_ASK_COMMAND = "ask"
PERSONA_ASK_COMMAND = "askwann"

# AI persona used by PERSONA_ASK_COMMAND
AI_MAX_OUTPUT_TOKENS = 2048
AI_MAX_WORDS = 700
AI_PERSONA = (
    "Answer like a dry, sarcastic spaceship computer while staying helpful."
)

# Google Flights alert behavior
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.modify",)
GMAIL_QUERY = "is:unread from:noreply-travel@google.com"
