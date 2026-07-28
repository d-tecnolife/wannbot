# wannbot

A small Discord bot that posts Google Flights alerts and provides public image and
answer search commands.

## Commands

- `!im <query>` or `!image <query>` searches Google Images and posts a public
  10-result carousel. Anyone can use the Previous and Next buttons. Buttons expire
  after five minutes of inactivity.
- `!ask <query>` shows Google's AI Overview and up to five sources. If Google does
  not return an overview, the bot uses Gemini and clearly labels the answer as
  ungrounded.

The prefix defaults to `!` and can be changed with `BOT_PREFIX`. Each search command
has its own 10-second per-user cooldown. SafeSearch is enabled except in Discord
channels explicitly marked NSFW.

## Configuration

Create a `.env` file or provide the following environment variables:

```dotenv
bot_token=your-discord-bot-token
channel_id=your-flight-alert-channel-id
BOT_PREFIX=!
SERPAPI_API_KEY=your-serpapi-key
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash
```

The Discord application must have the Message Content privileged intent enabled.
The SerpAPI free plan currently includes 250 successful searches per month, shared
by image and AI Overview requests. An image command normally uses one search. An AI
Overview normally uses one search but can use a second search when Google returns a
lazy-loading token. The bot reports quota errors and never purchases more searches.

Gemini is only used when Google does not return an AI Overview. Free-tier Gemini
content may be used by Google to improve its products.

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
