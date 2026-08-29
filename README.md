# wannbot

A small Discord bot that posts Google Flights alerts and provides public image and
answer search commands.

## Commands

- `!im <query>` or `!image <query>` searches Google Images and posts a public
  10-result carousel. Anyone can use the Previous and Next buttons. Buttons expire
  after five minutes of inactivity.
- `!ask <query>` shows Google's AI Overview and up to five sources. If Google does
  not return an overview, the bot links to the normal Google results instead.
- `!askwann <query>` asks the configured AI provider using `AI_PERSONA`
  and sends the answer as normal bot text.

The prefix defaults to `!` and can be changed with `BOT_PREFIX` in `bot_config.py`.
Each search command has its own 10-second per-user cooldown. SafeSearch is enabled
except in Discord channels explicitly marked NSFW.

## Configuration

Sensitive and deployment-specific values belong in `.env`:

```dotenv
bot_token=your-discord-bot-token
channel_id=your-flight-alert-channel-id
SERPAPI_API_KEY=your-serpapi-key
AI_API_KEY=your-openrouter-api-key
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=dots-studio/dots-3-note-preview:free

# Optional quota fallback
AI_FALLBACK_API_KEY=your-groq-api-key
AI_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
AI_FALLBACK_MODEL=qwen/qwen3.8-27b
```

Command names, aliases, prefix, persona, output-token budget, and Gmail query
settings live in `bot_config.py`. Change `IMAGE_COMMAND`, `IMAGE_ALIASES`,
`GOOGLE_ASK_COMMAND`, or `PERSONA_ASK_COMMAND` there to rename the commands.
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
