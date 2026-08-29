from __future__ import annotations

from urllib.parse import quote_plus

import discord
from discord.ext import commands

import bot_config
from bot_config import (
    GOOGLE_ASK_COMMAND,
    IMAGE_ALIASES,
    IMAGE_COMMAND,
    PERSONA_ASK_COMMAND,
)
from config import (
    AI_API_KEY,
    AI_BASE_URL,
    AI_FALLBACK_API_KEY,
    AI_FALLBACK_BASE_URL,
    AI_FALLBACK_MODEL,
    AI_MODEL,
    SERPAPI_API_KEY,
)

from .providers import (
    AIClient,
    ChatProvider,
    ImageResult,
    ProviderError,
    Reference,
    SerpAPIClient,
)


EMBED_BODY_LIMIT = 3500
SOURCES_FIELD_LIMIT = 900
MESSAGE_LIMIT = 2000


def channel_is_nsfw(channel) -> bool:
    checker = getattr(channel, "is_nsfw", None)
    return bool(checker and checker())


def truncate_answer(text: str, limit: int = EMBED_BODY_LIMIT) -> str:
    if len(text) <= limit:
        return text

    suffix = "\n\n*Response shortened for Discord.*"
    available = limit - len(suffix)
    candidate = text[:available]
    paragraph_break = candidate.rfind("\n\n")
    if paragraph_break >= available // 2:
        candidate = candidate[:paragraph_break]
    else:
        word_break = candidate.rfind(" ")
        if word_break > 0:
            candidate = candidate[:word_break]
    return candidate.rstrip() + "…" + suffix


def split_message(text: str, limit: int = MESSAGE_LIMIT) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > limit:
        candidate = remaining[:limit]
        split_at = candidate.rfind("\n\n")
        if split_at < limit // 2:
            split_at = candidate.rfind("\n")
        if split_at < limit // 2:
            split_at = candidate.rfind(" ")
        if split_at <= 0:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def format_sources(references: tuple[Reference, ...], limit: int = 5) -> str:
    lines: list[str] = []
    length = 0
    for index, reference in enumerate(references[:limit], start=1):
        title = reference.title.replace("[", "").replace("]", "")[:100]
        line = f"{index}. [{title}]({reference.url})"
        if length + len(line) + 1 > SOURCES_FIELD_LIMIT:
            break
        lines.append(line)
        length += len(line) + 1
    return "\n".join(lines)


def answer_embed(
    query: str,
    answer: str,
    *,
    references: tuple[Reference, ...] = (),
) -> discord.Embed:
    embed = discord.Embed(
        title="Google AI Overview",
        description=truncate_answer(answer),
        color=discord.Color.blue(),
    )
    embed.add_field(name="Query", value=query[:1024], inline=False)
    sources = format_sources(references)
    if sources:
        embed.add_field(name="Sources", value=sources, inline=False)
    embed.timestamp = discord.utils.utcnow()
    return embed


class ImageCarousel(discord.ui.View):
    def __init__(self, query: str, results: list[ImageResult]):
        super().__init__(timeout=300)
        self.query = query
        self.results = results
        self.index = 0
        self.message: discord.Message | None = None

        if len(results) < 2:
            for child in self.children:
                child.disabled = True

    def make_embed(self) -> discord.Embed:
        result = self.results[self.index]
        embed = discord.Embed(
            title=result.title[:256],
            url=result.source_url,
            description=f"Images for **{self.query[:500]}**\nSource: {result.source[:200]}",
            color=discord.Color.blue(),
        )
        embed.set_image(url=result.image_url)
        embed.set_footer(text=f"Result {self.index + 1} of {len(self.results)}")
        return embed

    async def _move(self, interaction: discord.Interaction, amount: int) -> None:
        self.index = (self.index + amount) % len(self.results)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._move(interaction, -1)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await self._move(interaction, 1)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if not self.message:
            return
        try:
            await self.message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass


class Search(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        serpapi: SerpAPIClient,
        ai: AIClient,
    ):
        self.bot = bot
        self.serpapi = serpapi
        self.ai = ai

    async def cog_unload(self) -> None:
        await self.serpapi.close()
        await self.ai.close()

    @commands.command(name=IMAGE_COMMAND, aliases=IMAGE_ALIASES)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def image_search(self, ctx: commands.Context, *, query: str) -> None:
        """Search Google Images and show a public, shared carousel."""
        async with ctx.typing():
            results = await self.serpapi.image_search(
                query, safe=not channel_is_nsfw(ctx.channel)
            )

        if not results:
            await ctx.reply(
                f'No usable images were found for "{query}".',
                mention_author=False,
            )
            return

        view = ImageCarousel(query, results)
        view.message = await ctx.reply(
            embed=view.make_embed(),
            view=view,
            mention_author=False,
        )

    @commands.command(name=GOOGLE_ASK_COMMAND)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ask(self, ctx: commands.Context, *, query: str) -> None:
        """Show Google's AI Overview."""
        async with ctx.typing():
            overview = await self.serpapi.ai_overview(
                query, safe=not channel_is_nsfw(ctx.channel)
            )

        if not overview:
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            await ctx.reply(
                "Google did not return an AI Overview for that query.\n"
                f"[Search Google instead]({search_url})",
                mention_author=False,
            )
            return

        await ctx.reply(
            embed=answer_embed(
                query,
                overview.text,
                references=overview.references,
            ),
            mention_author=False,
        )

    @commands.command(name=PERSONA_ASK_COMMAND)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ask_wann(self, ctx: commands.Context, *, query: str) -> None:
        """Ask the configured AI provider using the wannbot persona."""
        async with ctx.typing():
            answer = await self.ai.answer(query)

        for chunk in split_message(answer):
            await ctx.send(chunk)

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = ctx.clean_prefix
            await ctx.reply(
                f"Please include a query. Example: `{prefix}{ctx.command.name} red pandas`",
                mention_author=False,
            )
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(
                f"That command is cooling down. Try again in {error.retry_after:.1f}s.",
                mention_author=False,
                delete_after=min(error.retry_after, 10),
            )
            return
        if isinstance(error, ProviderError):
            query = str(ctx.kwargs.get("query", "")).strip()
            search_url = (
                f"https://www.google.com/search?q={quote_plus(query)}"
                if query and ctx.command and ctx.command.name == "ask"
                else None
            )
            message = str(error)
            if search_url:
                message += f"\n[Search Google instead]({search_url})"
            await ctx.reply(message, mention_author=False)
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    serpapi = SerpAPIClient(SERPAPI_API_KEY)
    persona = getattr(
        bot_config,
        "AI_PERSONA",
        getattr(
            bot_config,
            "GROQ_PERSONA",
            getattr(bot_config, "GEMINI_PERSONA", ""),
        ),
    )
    ai = AIClient(
        (
            ChatProvider("OpenRouter", AI_API_KEY, AI_BASE_URL, AI_MODEL),
            ChatProvider(
                "Groq",
                AI_FALLBACK_API_KEY,
                AI_FALLBACK_BASE_URL,
                AI_FALLBACK_MODEL,
            ),
        ),
        persona,
        getattr(
            bot_config,
            "AI_MAX_OUTPUT_TOKENS",
            getattr(
                bot_config,
                "GROQ_MAX_OUTPUT_TOKENS",
                getattr(bot_config, "GEMINI_MAX_OUTPUT_TOKENS", 2048),
            ),
        ),
        getattr(
            bot_config,
            "AI_MAX_WORDS",
            getattr(
                bot_config,
                "GROQ_MAX_WORDS",
                getattr(bot_config, "GEMINI_MAX_WORDS", 700),
            ),
        ),
    )
    await bot.add_cog(Search(bot, serpapi, ai))
