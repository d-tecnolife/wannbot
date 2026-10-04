import bot_config
from cogs.help.help import Help, _chunk, command_embed, help_embed
from cogs.music.music import Music
from cogs.search.search import Search


def cogs():
    return [Search(None, None, None), Music(None), Help(None)]


def test_help_embed_lists_every_configured_command_with_usage_and_aliases():
    embed = help_embed("?", cogs())
    text = "\n".join(field.value for field in embed.fields)
    for prefix in (
        "IMAGE",
        "GOOGLE_ASK",
        "PERSONA_ASK",
        "PLAY",
        "PLAY_NOW",
        "SKIP",
        "PAUSE",
        "RESUME",
        "STOP",
        "NOW_PLAYING",
        "QUEUE",
        "CLEAR",
        "LOOP",
        "LOOP_QUEUE",
        "HELP",
    ):
        assert f"`?{getattr(bot_config, f'{prefix}_COMMAND')}" in text
        for alias in getattr(bot_config, f"{prefix}_ALIASES"):
            assert f"`?{alias}`" in text
    assert f"`?{bot_config.PLAY_COMMAND} <search or link>`" in text
    assert [field.name for field in embed.fields] == ["Search", "Music", "Help"]
    assert all(len(field.value) <= 1024 for field in embed.fields)


def test_command_embed_shows_usage_and_aliases():
    play = next(
        command for command in Music(None).get_commands() if command.name == bot_config.PLAY_COMMAND
    )
    embed = command_embed("!", play)
    fields = {field.name: field.value for field in embed.fields}
    assert fields["Usage"] == f"`!{bot_config.PLAY_COMMAND} <search or link>`"
    assert embed.description


def test_chunk_splits_long_sections():
    chunks = _chunk(["a" * 600, "b" * 600, "c" * 10])
    assert len(chunks) == 2
    assert all(len(chunk) <= 1024 for chunk in chunks)
