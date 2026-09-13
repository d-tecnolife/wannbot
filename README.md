# wannbot

A small Discord bot that provides public image and answer search commands, an AI
persona, and music playback in voice channels.

## Commands

- `!im <query>` or `!image <query>` searches Google Images and posts a public
  10-result carousel. Anyone can use the Previous and Next buttons. Buttons expire
  after five minutes of inactivity.
- `!ask <query>` shows Google's AI Overview and up to five sources. If Google does
  not return an overview, the bot links to the normal Google results instead.
- `!askwann <query>` asks the configured AI provider using `AI_PERSONA`
  and sends the answer as normal bot text.
- `!play <query or link>` (alias `!p`) joins your voice channel and plays the first
  YouTube search result, or any link yt-dlp supports (YouTube, SoundCloud, Bandcamp,
  and more). Playlist links queue up to `MUSIC_PLAYLIST_LIMIT` tracks.
- `!skip`, `!pause`, `!resume`, `!queue`, `!np`, and `!stop` (alias `!leave`)
  control playback. `!stop` clears the queue and leaves the channel.

The prefix defaults to `!` and can be changed with `BOT_PREFIX` in `bot_config.py`.
Each search command has its own 10-second per-user cooldown. SafeSearch is enabled
except in Discord channels explicitly marked NSFW.

The bot leaves voice after `MUSIC_IDLE_SECONDS` with an empty queue, or when
everyone else leaves its channel.

## Configuration

Sensitive and deployment-specific values belong in `.env`:

```dotenv
bot_token=your-discord-bot-token
SERPAPI_API_KEY=your-serpapi-key
AI_API_KEY=your-openrouter-api-key
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=dots-studio/dots-3-note-preview:free

# Optional quota fallback
AI_FALLBACK_API_KEY=your-groq-api-key
AI_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
AI_FALLBACK_MODEL=qwen/qwen3.8-27b

# Optional Netscape-format cookies file if YouTube demands sign-in
YTDLP_COOKIES_FILE=/app/cookies.txt
```

Command names, aliases, prefix, persona, output-token budget, and music limits live
in `bot_config.py`. Change `IMAGE_COMMAND`, `IMAGE_ALIASES`, `GOOGLE_ASK_COMMAND`,
`PERSONA_ASK_COMMAND`, `PLAY_COMMAND`, or `PLAY_ALIASES` there to rename commands.
`AI_MAX_OUTPUT_TOKENS` and `AI_MAX_WORDS` control persona-answer length. The
defaults use a 2,048-token ceiling and a 700-word maximum. The word maximum is not
a target; the model is instructed to answer as briefly as appropriate without
padding. Restart the bot after changing configuration.

The Discord application must have the Message Content privileged intent enabled.
The SerpAPI free plan currently includes 250 successful searches per month, shared
by image and AI Overview requests. An image command normally uses one search. An AI
Overview normally uses one search but can use a second search when Google returns a
lazy-loading token. The bot reports quota errors and never purchases more searches.

`!askwann` sends the user's query to OpenRouter. When OpenRouter returns HTTP 404
or 429, the bot retries once through the optional Groq fallback. Free-model limits
are shared across OpenRouter models, so changing the OpenRouter model does not add
more free requests. `AI_PERSONA` in `bot_config.py` changes the command's tone;
SerpAPI returns Google's existing AI Overview unchanged for `!ask`.

Music uses discord.py's voice support (including Discord's required DAVE
end-to-end encryption), yt-dlp with its Deno JavaScript runtime for YouTube, and
FFmpeg, all included in the Docker image. Stream URLs are resolved when a track
starts, so queued tracks do not expire. Hosts on datacenter IP ranges may need
`YTDLP_COOKIES_FILE`; residential connections usually do not.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Run the bot with:

```bash
python3 main.py
```

Local playback requires `ffmpeg` on `PATH`.

Logs are written to stdout and include extension startup, command receipt and
completion, provider/model attempts, HTTP status codes, and full tracebacks for
unexpected failures. Query text and API keys are not logged. If a command-like
message is logged as received but never logged as started, check that its name and
prefix match the configured commands. If it is not logged as received at all,
confirm the Discord application's Message Content privileged intent is enabled.
