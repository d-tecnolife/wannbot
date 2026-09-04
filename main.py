import logging

import discord
from discord.ext import commands

from bot_config import BOT_PREFIX
from config import DISCORD_BOT_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("wannbot")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)


@bot.event
async def on_ready():
    logger.info(
        "Discord ready: user=%s id=%s guilds=%d message_content=%s",
        bot.user,
        bot.user.id if bot.user else None,
        len(bot.guilds),
        bot.intents.message_content,
    )


@bot.listen("on_message")
async def log_command_candidate(message: discord.Message) -> None:
    """Log command-like messages without recording potentially private query text."""
    if message.author.bot or not message.content.startswith(BOT_PREFIX):
        return
    command_name = message.content[len(BOT_PREFIX) :].split(maxsplit=1)[0]
    logger.info(
        "Command candidate received: command=%s user=%s guild=%s channel=%s query_chars=%d",
        command_name or "<empty>",
        message.author.id,
        message.guild.id if message.guild else "dm",
        message.channel.id,
        max(0, len(message.content) - len(BOT_PREFIX) - len(command_name)),
    )


@bot.before_invoke
async def log_command_start(ctx: commands.Context) -> None:
    logger.info("Command started: command=%s message=%s", ctx.command, ctx.message.id)


@bot.after_invoke
async def log_command_complete(ctx: commands.Context) -> None:
    logger.info("Command finished: command=%s message=%s", ctx.command, ctx.message.id)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if ctx.command and ctx.command.has_error_handler():
        return
    cog = ctx.cog
    if cog and cog.has_error_handler():
        return
    original = getattr(error, "original", error)
    if isinstance(error, commands.CommandNotFound):
        logger.warning("Unknown command: message=%s", ctx.message.id)
        return
    logger.error(
        "Unhandled command failure: command=%s message=%s",
        ctx.command,
        ctx.message.id,
        exc_info=(type(original), original, original.__traceback__),
    )


async def load_cogs():
    for extension in ("cogs.flight_alerts.flight_alerts", "cogs.search.search"):
        logger.info("Loading extension: %s", extension)
        await bot.load_extension(extension)
        logger.info("Extension loaded: %s", extension)


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
