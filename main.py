import discord
from discord.ext import commands

from config import DISCORD_BOT_TOKEN

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


# Load the flight alerts cog
async def load_cogs():
    await bot.load_extension("cogs.flight_alerts.flight_alerts")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
