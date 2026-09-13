"""Non-sensitive wannbot behavior and command configuration."""

# Discord command routing
BOT_PREFIX = "!"
IMAGE_COMMAND = "im"
IMAGE_ALIASES = ("image",)
GOOGLE_ASK_COMMAND = "ask"
GOOGLE_ASK_ALIASES = ()
PERSONA_ASK_COMMAND = "askwann"
PERSONA_ASK_ALIASES = ()
HELP_COMMAND = "help"
HELP_ALIASES = ("commands",)

# Music command routing
PLAY_COMMAND = "play"
PLAY_ALIASES = ("p",)
SKIP_COMMAND = "skip"
SKIP_ALIASES = ()
PAUSE_COMMAND = "pause"
PAUSE_ALIASES = ()
RESUME_COMMAND = "resume"
RESUME_ALIASES = ()
STOP_COMMAND = "stop"
STOP_ALIASES = ("leave",)
NOW_PLAYING_COMMAND = "np"
NOW_PLAYING_ALIASES = ()
QUEUE_COMMAND = "queue"
QUEUE_ALIASES = ("q",)

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
