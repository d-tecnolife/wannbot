from datetime import datetime

import discord
from discord.ext import commands

from bot_config import BOT_PREFIX
from config import DISCORD_BOT_TOKEN

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"[{datetime.now()}] Logged in as {bot.user}")


async def load_cogs():
    await bot.load_extension("cogs.flight_alerts.flight_alerts")
    await bot.load_extension("cogs.search.search")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
