import asyncio
from collections import deque

import bot_config
from cogs.music.music import (
    GuildPlayer,
    Music,
    Track,
    entries_to_tracks,
    format_duration,
    normalize_query,
)


def test_normalize_query_keeps_links_and_strips_embed_brackets():
    assert normalize_query("https://youtu.be/abc") == "https://youtu.be/abc"
    assert normalize_query("<https://soundcloud.com/a/b>") == "https://soundcloud.com/a/b"


def test_normalize_query_searches_plain_text():
    assert normalize_query("  daft punk one more time ") == "ytsearch1:daft punk one more time"


def test_format_duration():
    assert format_duration(65) == "1:05"
    assert format_duration(3725) == "1:02:05"
    assert format_duration(None) == "live/unknown"
    assert format_duration(0) == "live/unknown"


def test_entries_to_tracks_single_video():
    info = {"title": "Song", "webpage_url": "https://www.youtube.com/watch?v=x", "duration": 90}
    assert entries_to_tracks(info, "alice") == [
        Track("Song", "https://www.youtube.com/watch?v=x", 90, "alice")
    ]


def test_entries_to_tracks_flat_playlist_skips_bad_entries_and_limits():
    info = {
        "entries": [
            None,
            {"title": "No url"},
            {"title": "Flat", "id": "abc", "ie_key": "Youtube"},
            {"title": "Two", "url": "https://soundcloud.com/a/two"},
            {"title": "Three", "url": "https://soundcloud.com/a/three"},
        ]
    }
    tracks = entries_to_tracks(info, "bob", limit=2)
    assert [track.url for track in tracks] == [
        "https://www.youtube.com/watch?v=abc",
        "https://soundcloud.com/a/two",
    ]


def test_entries_to_tracks_empty_search():
    assert entries_to_tracks({"entries": []}, "carol") == []


def test_music_commands_use_bot_config_names_and_aliases():
    commands = {command.name: tuple(command.aliases) for command in Music(None).get_commands()}
    for prefix in (
        "PLAY",
        "PLAY_NOW",
        "SKIP",
        "PAUSE",
        "RESUME",
        "STOP",
        "NOW_PLAYING",
        "QUEUE",
        "CLEAR",
    ):
        name = getattr(bot_config, f"{prefix}_COMMAND")
        assert commands[name] == tuple(getattr(bot_config, f"{prefix}_ALIASES"))


def queue_player(titles):
    player = GuildPlayer.__new__(GuildPlayer)
    player.queue = deque(track(title) for title in titles)
    player._wakeup = asyncio.Event()
    return player


def track(title):
    return Track(title, f"https://example.com/{title}", None, "tester")


def test_add_front_places_tracks_ahead_of_queue_in_order():
    player = queue_player(["old1", "old2"])
    player.add([track("new1"), track("new2")], front=True)
    assert [item.title for item in player.queue] == ["new1", "new2", "old1", "old2"]


def test_clear_empties_queue_and_reports_count():
    player = queue_player(["a", "b", "c"])
    assert player.clear() == 3
    assert not player.queue
