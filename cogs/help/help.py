from __future__ import annotations

import logging
from collections.abc import Iterable

import discord
from discord.ext import commands

import bot_config


HELP_COMMAND = getattr(bot_config, "HELP_COMMAND", "help")
HELP_ALIASES = getattr(bot_config, "HELP_ALIASES", ("commands",))
FIELD_LIMIT = 1024
logger = logging.getLogger("wannbot.help")


def command_usage(prefix: str, command: commands.Command) -> str:
    arguments = command.usage or command.signature
    return f"{prefix}{command.qualified_name} {arguments}".rstrip()


def command_aliases(prefix: str, command: commands.Command) -> str:
    return ", ".join(f"`{prefix}{alias}`" for alias in command.aliases)


def command_summary(prefix: str, command: commands.Command) -> str:
    line = f"`{command_usage(prefix, command)}`"
    if command.aliases:
        line += f" (also {command_aliases(prefix, command)})"
    return f"{line}\n{command.short_doc or 'No description.'}"


def _chunk(entries: list[str], limit: int = FIELD_LIMIT) -> list[str]:
    chunks: list[str] = []
    current = ""
    for entry in entries:
        candidate = f"{current}\n\n{entry}" if current else entry
        if len(candidate) > limit and current:
            chunks.append(current)
            current = entry
        else:
            current = candidate
    if current:
        chunks.append(current[:limit])
    return chunks


def help_embed(prefix: str, cogs: Iterable[commands.Cog]) -> discord.Embed:
    embed = discord.Embed(title="wannbot commands", color=discord.Color.blue())
    for cog in cogs:
        entries = [
            command_summary(prefix, command)
            for command in cog.get_commands()
            if not command.hidden
        ]
        for index, chunk in enumerate(_chunk(entries)):
            name = cog.qualified_name if index == 0 else f"{cog.qualified_name} (cont.)"
            embed.add_field(name=name, value=chunk, inline=False)
    embed.set_footer(text=f"Use {prefix}{HELP_COMMAND} <command> for details on one command.")
    return embed


def command_embed(prefix: str, command: commands.Command) -> discord.Embed:
    embed = discord.Embed(
        title=f"{prefix}{command.qualified_name}",
        description=command.help or "No description.",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Usage", value=f"`{command_usage(prefix, command)}`", inline=False)
    if command.aliases:
        embed.add_field(name="Aliases", value=command_aliases(prefix, command), inline=False)
    return embed


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name=HELP_COMMAND, aliases=HELP_ALIASES, usage="[command]")
    async def show_help(self, ctx: commands.Context, command_name: str | None = None) -> None:
        """List every command, or show details for one command."""
        prefix = ctx.clean_prefix
        if command_name is None:
            await ctx.reply(embed=help_embed(prefix, self.bot.cogs.values()), mention_author=False)
            return

        command = self.bot.get_command(command_name.removeprefix(prefix))
        if command is None or command.hidden:
            await ctx.reply(
                f"No command named `{command_name}`. Use `{prefix}{HELP_COMMAND}` to list commands.",
                mention_author=False,
            )
            return
        await ctx.reply(embed=command_embed(prefix, command), mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
    logger.info("Help cog ready: command=%s", HELP_COMMAND)
