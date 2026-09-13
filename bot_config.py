"""Non-sensitive wannbot behavior and command configuration."""

# Discord command routing
BOT_PREFIX = "!"
IMAGE_COMMAND = "im"
IMAGE_ALIASES = ("image",)
GOOGLE_ASK_COMMAND = "ask"
PERSONA_ASK_COMMAND = "askwann"
PLAY_COMMAND = "play"
PLAY_ALIASES = ("p",)

# AI persona used by PERSONA_ASK_COMMAND
AI_MAX_OUTPUT_TOKENS = 2048
AI_MAX_WORDS = 700
AI_PERSONA = (
    "Answer like a dry, sarcastic spaceship computer while staying helpful."
)

# Music playback
MUSIC_MAX_QUEUE = 50
MUSIC_PLAYLIST_LIMIT = 25
MUSIC_IDLE_SECONDS = 300
