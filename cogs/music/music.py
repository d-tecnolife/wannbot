from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass
from typing import Any

import discord
import yt_dlp
from discord.ext import commands

import bot_config
from config import YTDLP_COOKIES_FILE


PLAY_COMMAND = getattr(bot_config, "PLAY_COMMAND", "play")
PLAY_ALIASES = getattr(bot_config, "PLAY_ALIASES", ("p",))
PLAY_NOW_COMMAND = getattr(bot_config, "PLAY_NOW_COMMAND", "playnow")
PLAY_NOW_ALIASES = getattr(bot_config, "PLAY_NOW_ALIASES", ("pn",))
SKIP_COMMAND = getattr(bot_config, "SKIP_COMMAND", "skip")
SKIP_ALIASES = getattr(bot_config, "SKIP_ALIASES", ())
PAUSE_COMMAND = getattr(bot_config, "PAUSE_COMMAND", "pause")
PAUSE_ALIASES = getattr(bot_config, "PAUSE_ALIASES", ())
RESUME_COMMAND = getattr(bot_config, "RESUME_COMMAND", "resume")
RESUME_ALIASES = getattr(bot_config, "RESUME_ALIASES", ())
STOP_COMMAND = getattr(bot_config, "STOP_COMMAND", "stop")
STOP_ALIASES = getattr(bot_config, "STOP_ALIASES", ("leave",))
NOW_PLAYING_COMMAND = getattr(bot_config, "NOW_PLAYING_COMMAND", "np")
NOW_PLAYING_ALIASES = getattr(bot_config, "NOW_PLAYING_ALIASES", ())
QUEUE_COMMAND = getattr(bot_config, "QUEUE_COMMAND", "queue")
QUEUE_ALIASES = getattr(bot_config, "QUEUE_ALIASES", ("q",))
CLEAR_COMMAND = getattr(bot_config, "CLEAR_COMMAND", "clear")
CLEAR_ALIASES = getattr(bot_config, "CLEAR_ALIASES", ())
LOOP_COMMAND = getattr(bot_config, "LOOP_COMMAND", "loop")
LOOP_ALIASES = getattr(bot_config, "LOOP_ALIASES", ())
LOOP_QUEUE_COMMAND = getattr(bot_config, "LOOP_QUEUE_COMMAND", "loopqueue")
LOOP_QUEUE_ALIASES = getattr(bot_config, "LOOP_QUEUE_ALIASES", ("lq",))
MAX_QUEUE = getattr(bot_config, "MUSIC_MAX_QUEUE", 50)
PLAYLIST_LIMIT = getattr(bot_config, "MUSIC_PLAYLIST_LIMIT", 25)
IDLE_SECONDS = getattr(bot_config, "MUSIC_IDLE_SECONDS", 300)
QUEUE_DISPLAY_LIMIT = 10

URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v="
logger = logging.getLogger("wannbot.music")


@dataclass(frozen=True)
class Track:
    title: str
    url: str
    duration: int | None
    requester: str


def normalize_query(query: str) -> str:
    """Return a yt-dlp target: links unchanged, anything else as a YouTube search."""
    query = query.strip()
    if query.startswith("<") and query.endswith(">"):
        query = query[1:-1].strip()
    if URL_PATTERN.match(query):
        return query
    return f"ytsearch1:{query}"


def format_duration(seconds: Any) -> str:
    if not isinstance(seconds, (int, float)) or seconds <= 0:
        return "live/unknown"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _entry_url(entry: dict[str, Any]) -> str | None:
    for key in ("webpage_url", "url"):
        value = entry.get(key)
        if isinstance(value, str) and URL_PATTERN.match(value):
            return value
    video_id = entry.get("id")
    if entry.get("ie_key") == "Youtube" and isinstance(video_id, str):
        return YOUTUBE_WATCH_URL + video_id
    return None


def entries_to_tracks(
    info: dict[str, Any], requester: str, limit: int = PLAYLIST_LIMIT
) -> list[Track]:
    entries = info.get("entries")
    candidates = entries if entries is not None else [info]
    tracks: list[Track] = []
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        url = _entry_url(entry)
        if not url:
            continue
        tracks.append(
            Track(
                title=str(entry.get("title") or url)[:200],
                url=url,
                duration=entry.get("duration"),
                requester=requester,
            )
        )
        if len(tracks) == limit:
            break
    return tracks


def _ydl_options(**overrides: Any) -> dict[str, Any]:
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if YTDLP_COOKIES_FILE:
        options["cookiefile"] = YTDLP_COOKIES_FILE
    options.update(overrides)
    return options


def _extract(target: str, **overrides: Any) -> dict[str, Any]:
    with yt_dlp.YoutubeDL(_ydl_options(**overrides)) as ydl:
        return ydl.extract_info(target, download=False)


async def find_tracks(query: str, requester: str) -> list[Track]:
    info = await asyncio.to_thread(
        _extract, normalize_query(query), extract_flat="in_playlist"
    )
    return entries_to_tracks(info or {}, requester)


async def resolve_stream(url: str) -> str:
    info = await asyncio.to_thread(_extract, url)
    stream_url = (info or {}).get("url")
    if not isinstance(stream_url, str):
        raise yt_dlp.utils.DownloadError("No playable audio stream was found.")
    return stream_url


LOOP_OFF = "off"
LOOP_TRACK = "track"
LOOP_QUEUE = "queue"


class GuildPlayer:
    loop_mode = LOOP_OFF
    skip_requested = False

    def __init__(self, cog: Music, guild: discord.Guild, channel: discord.abc.Messageable):
        self.cog = cog
        self.guild = guild
        self.channel = channel
        self.queue: deque[Track] = deque()
        self.current: Track | None = None
        self._wakeup = asyncio.Event()
        self.task = asyncio.create_task(self._run())

    def add(self, tracks: list[Track], *, front: bool = False) -> list[Track]:
        added = tracks[: max(MAX_QUEUE - len(self.queue), 0)]
        if front:
            self.queue.extendleft(reversed(added))
        else:
            self.queue.extend(added)
        if added:
            self._wakeup.set()
        return added

    def clear(self) -> int:
        cleared = len(self.queue)
        self.queue.clear()
        return cleared

    def request_skip(self, voice: discord.VoiceClient) -> None:
        """Stop the current track and move on even when it is being looped."""
        self.skip_requested = True
        voice.stop()

    def requeue_finished(self, track: Track) -> None:
        """Put a finished track back according to the loop mode."""
        skipped, self.skip_requested = self.skip_requested, False
        if self.loop_mode == LOOP_TRACK and not skipped:
            self.queue.appendleft(track)
        elif self.loop_mode == LOOP_QUEUE:
            self.queue.append(track)

    async def _next_track(self) -> Track:
        while not self.queue:
            self._wakeup.clear()
            await self._wakeup.wait()
        return self.queue.popleft()

    async def _run(self) -> None:
        try:
            while True:
                try:
                    track = await asyncio.wait_for(self._next_track(), IDLE_SECONDS)
                except asyncio.TimeoutError:
                    await self.channel.send("The queue has been empty for a while. Leaving voice.")
                    return

                voice = self.guild.voice_client
                if not isinstance(voice, discord.VoiceClient) or not voice.is_connected():
                    return

                try:
                    stream_url = await resolve_stream(track.url)
                except yt_dlp.utils.DownloadError as exc:
                    logger.warning("Track resolve failed: guild=%s error=%s", self.guild.id, exc)
                    await self.channel.send(f"Could not play **{track.title}**. Skipping.")
                    continue

                finished = asyncio.Event()
                loop = asyncio.get_running_loop()

                def after(error: Exception | None) -> None:
                    if error:
                        logger.error("Playback failed: guild=%s error=%s", self.guild.id, error)
                    loop.call_soon_threadsafe(finished.set)

                self.current = track
                self.skip_requested = False
                voice.play(
                    discord.FFmpegOpusAudio(
                        stream_url, before_options=FFMPEG_BEFORE_OPTIONS, options="-vn"
                    ),
                    after=after,
                )
                logger.info("Playback started: guild=%s", self.guild.id)
                await self.channel.send(
                    f"Now playing: **{track.title}** [{format_duration(track.duration)}] "
                    f"requested by {track.requester}"
                )
                await finished.wait()
                self.current = None
                self.requeue_finished(track)
        finally:
            self.current = None
            self.queue.clear()
            voice = self.guild.voice_client
            if voice:
                await voice.disconnect(force=True)
            if self.cog.players.get(self.guild.id) is self:
                del self.cog.players[self.guild.id]

    def stop(self) -> None:
        self.queue.clear()
        self.task.cancel()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    async def cog_unload(self) -> None:
        for player in list(self.players.values()):
            player.stop()

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    def _voice(self, ctx: commands.Context) -> discord.VoiceClient | None:
        voice = ctx.voice_client
        return voice if isinstance(voice, discord.VoiceClient) else None

    async def _enqueue(
        self, ctx: commands.Context, query: str, *, front: bool
    ) -> tuple[GuildPlayer, list[Track], bool] | None:
        """Look up tracks, join the caller's voice channel, and queue them."""
        author_voice = getattr(ctx.author, "voice", None)
        if not author_voice or not author_voice.channel:
            await ctx.reply("Join a voice channel first.", mention_author=False)
            return None

        async with ctx.typing():
            try:
                tracks = await find_tracks(query, ctx.author.display_name)
            except yt_dlp.utils.DownloadError as exc:
                logger.warning("Track lookup failed: guild=%s error=%s", ctx.guild.id, exc)
                await ctx.reply("Could not load that link or search.", mention_author=False)
                return None

        if not tracks:
            await ctx.reply("No playable results were found.", mention_author=False)
            return None

        voice = self._voice(ctx)
        if voice is None:
            await author_voice.channel.connect(self_deaf=True)
        elif voice.channel != author_voice.channel:
            await voice.move_to(author_voice.channel)

        player = self.players.get(ctx.guild.id)
        if player is None or player.task.done():
            player = GuildPlayer(self, ctx.guild, ctx.channel)
            self.players[ctx.guild.id] = player

        was_busy = player.current is not None or bool(player.queue)
        added = player.add(tracks, front=front)
        if not added:
            await ctx.reply(f"The queue is full ({MAX_QUEUE} tracks).", mention_author=False)
            return None
        return player, added, was_busy

    @commands.command(name=PLAY_COMMAND, aliases=PLAY_ALIASES, usage="<search or link>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Join your voice channel and play a YouTube search result or a link.

        Links can be YouTube, SoundCloud, Bandcamp, or any site yt-dlp supports.
        Playlist links queue several tracks.
        """
        queued = await self._enqueue(ctx, query, front=False)
        if queued is None:
            return
        _, added, was_busy = queued
        if len(added) > 1:
            await ctx.reply(f"Queued {len(added)} tracks.", mention_author=False)
        elif was_busy:
            await ctx.reply(f"Queued **{added[0].title}**.", mention_author=False)

    @commands.command(name=PLAY_NOW_COMMAND, aliases=PLAY_NOW_ALIASES, usage="<search or link>")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play_now(self, ctx: commands.Context, *, query: str) -> None:
        """Play a search result or link right away, skipping the queue.

        The current track is skipped and the rest of the queue plays afterwards.
        Playlist links put all their tracks at the front, in order.
        """
        queued = await self._enqueue(ctx, query, front=True)
        if queued is None:
            return
        player, added, _ = queued
        voice = self._voice(ctx)
        if voice and (voice.is_playing() or voice.is_paused()):
            player.request_skip(voice)
        if len(added) > 1:
            await ctx.reply(
                f"Playing {len(added)} tracks now, ahead of the queue.", mention_author=False
            )

    @commands.command(name=SKIP_COMMAND, aliases=SKIP_ALIASES)
    async def skip(self, ctx: commands.Context) -> None:
        """Skip the current track and play the next one."""
        voice = self._voice(ctx)
        if not voice or not (voice.is_playing() or voice.is_paused()):
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        player = self.players.get(ctx.guild.id)
        if player:
            player.request_skip(voice)
        else:
            voice.stop()
        await ctx.message.add_reaction("⏭️")

    @commands.command(name=PAUSE_COMMAND, aliases=PAUSE_ALIASES)
    async def pause(self, ctx: commands.Context) -> None:
        """Pause playback."""
        voice = self._voice(ctx)
        if not voice or not voice.is_playing():
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        voice.pause()
        await ctx.message.add_reaction("⏸️")

    @commands.command(name=RESUME_COMMAND, aliases=RESUME_ALIASES)
    async def resume(self, ctx: commands.Context) -> None:
        """Resume paused playback."""
        voice = self._voice(ctx)
        if not voice or not voice.is_paused():
            await ctx.reply("Playback is not paused.", mention_author=False)
            return
        voice.resume()
        await ctx.message.add_reaction("▶️")

    @commands.command(name=STOP_COMMAND, aliases=STOP_ALIASES)
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback, clear the queue, and leave voice."""
        player = self.players.get(ctx.guild.id)
        if player:
            player.stop()
        elif ctx.voice_client:
            await ctx.voice_client.disconnect(force=True)
        else:
            await ctx.reply("I am not in a voice channel.", mention_author=False)
            return
        await ctx.message.add_reaction("⏹️")

    @commands.command(name=CLEAR_COMMAND, aliases=CLEAR_ALIASES)
    async def clear_queue(self, ctx: commands.Context) -> None:
        """Remove every queued track but keep the current one playing."""
        player = self.players.get(ctx.guild.id)
        if not player or not player.queue:
            await ctx.reply("The queue is already empty.", mention_author=False)
            return
        cleared = player.clear()
        await ctx.reply(
            f"Cleared {cleared} queued track{'s' if cleared != 1 else ''}.", mention_author=False
        )

    async def _toggle_loop(self, ctx: commands.Context, mode: str, on: str, off: str) -> None:
        player = self.players.get(ctx.guild.id)
        if not player or (not player.current and not player.queue):
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        player.loop_mode = LOOP_OFF if player.loop_mode == mode else mode
        await ctx.reply(on if player.loop_mode == mode else off, mention_author=False)

    @commands.command(name=LOOP_COMMAND, aliases=LOOP_ALIASES)
    async def loop(self, ctx: commands.Context) -> None:
        """Toggle looping the current track until you skip it or turn loop off."""
        await self._toggle_loop(
            ctx, LOOP_TRACK, "🔂 Looping the current track.", "Loop is off."
        )

    @commands.command(name=LOOP_QUEUE_COMMAND, aliases=LOOP_QUEUE_ALIASES)
    async def loop_queue(self, ctx: commands.Context) -> None:
        """Toggle looping the whole queue; finished tracks go to the back."""
        await self._toggle_loop(ctx, LOOP_QUEUE, "🔁 Looping the queue.", "Queue loop is off.")

    @commands.command(name=NOW_PLAYING_COMMAND, aliases=NOW_PLAYING_ALIASES)
    async def now_playing(self, ctx: commands.Context) -> None:
        """Show the track that is playing now."""
        player = self.players.get(ctx.guild.id)
        if not player or not player.current:
            await ctx.reply("Nothing is playing.", mention_author=False)
            return
        track = player.current
        await ctx.reply(
            f"Now playing: **{track.title}** [{format_duration(track.duration)}] "
            f"requested by {track.requester}\n<{track.url}>",
            mention_author=False,
        )

    @commands.command(name=QUEUE_COMMAND, aliases=QUEUE_ALIASES)
    async def show_queue(self, ctx: commands.Context) -> None:
        """Show the current track and what is queued next."""
        player = self.players.get(ctx.guild.id)
        if not player or (not player.current and not player.queue):
            await ctx.reply("The queue is empty.", mention_author=False)
            return
        lines = []
        if player.current:
            lines.append(f"Now: **{player.current.title}**")
        if player.loop_mode == LOOP_TRACK:
            lines.append("Loop: current track")
        elif player.loop_mode == LOOP_QUEUE:
            lines.append("Loop: queue")
        for index, track in enumerate(list(player.queue)[:QUEUE_DISPLAY_LIMIT], start=1):
            lines.append(f"{index}. {track.title} [{format_duration(track.duration)}]")
        remaining = len(player.queue) - QUEUE_DISPLAY_LIMIT
        if remaining > 0:
            lines.append(f"...and {remaining} more")
        await ctx.reply("\n".join(lines), mention_author=False)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        voice = member.guild.voice_client
        if not isinstance(voice, discord.VoiceClient) or before.channel != voice.channel:
            return
        if any(not other.bot for other in voice.channel.members):
            return
        player = self.players.get(member.guild.id)
        if player:
            player.stop()
        else:
            await voice.disconnect(force=True)

    async def cog_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            prefix = ctx.clean_prefix
            await ctx.reply(
                f"Please include a search or link. Example: `{prefix}{PLAY_COMMAND} lofi beats`",
                mention_author=False,
            )
            return
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.reply("Music commands only work in servers.", mention_author=False)
            return
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(
                f"That command is cooling down. Try again in {error.retry_after:.1f}s.",
                mention_author=False,
                delete_after=min(error.retry_after, 10),
            )
            return
        original = getattr(error, "original", error)
        logger.error(
            "Unexpected music command failure: command=%s message=%s",
            ctx.command,
            ctx.message.id,
            exc_info=(type(original), original, original.__traceback__),
        )
        await ctx.reply("Something went wrong with that music command.", mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
    logger.info(
        "Music cog ready: commands=%s",
        ",".join(
            (
                PLAY_COMMAND,
                PLAY_NOW_COMMAND,
                SKIP_COMMAND,
                PAUSE_COMMAND,
                RESUME_COMMAND,
                STOP_COMMAND,
                NOW_PLAYING_COMMAND,
                QUEUE_COMMAND,
                CLEAR_COMMAND,
                LOOP_COMMAND,
                LOOP_QUEUE_COMMAND,
            )
        ),
    )
