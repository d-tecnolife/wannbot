from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cogs.search.providers import ImageResult, Reference
from cogs.search.search import (
    ImageCarousel,
    Search,
    answer_embed,
    channel_is_nsfw,
    format_sources,
    truncate_answer,
)


def image_result(number: int) -> ImageResult:
    return ImageResult(
        title=f"Image {number}",
        image_url=f"https://images.example/{number}.jpg",
        thumbnail_url=None,
        source_url=f"https://example.com/{number}",
        source="example.com",
    )


def test_channel_nsfw_policy():
    assert channel_is_nsfw(SimpleNamespace(is_nsfw=lambda: True))
    assert not channel_is_nsfw(SimpleNamespace(is_nsfw=lambda: False))
    assert not channel_is_nsfw(SimpleNamespace())


def test_truncate_answer_stays_within_limit_and_labels_truncation():
    text = ("First paragraph. " * 30) + "\n\n" + ("Second paragraph. " * 30)
    result = truncate_answer(text, limit=220)

    assert len(result) <= 220
    assert result.endswith("*Response shortened for Discord.*")
    assert "…" in result


def test_sources_are_limited_and_markdown_safe():
    references = tuple(
        Reference(title=f"[Source {index}]", url=f"https://example.com/{index}")
        for index in range(8)
    )

    rendered = format_sources(references)

    assert rendered.count("\n") == 4
    assert "[Source 1]" in rendered
    assert "[Source 4]" in rendered
    assert "Source 5" not in rendered


def test_answer_embed_labels_persona_and_includes_sources():
    embed = answer_embed(
        "question",
        "answer",
        references=(Reference("Example", "https://example.com"),),
    )
    persona = answer_embed("question", "persona", persona=True)

    assert embed.title == "Google AI Overview"
    assert embed.fields[1].name == "Sources"
    assert persona.title == "Whip and Nae Nae Bot"
    assert len(persona.fields) == 1


@pytest.mark.asyncio
async def test_carousel_wraps_and_is_shared():
    view = ImageCarousel("cats", [image_result(1), image_result(2)])
    interaction = SimpleNamespace(
        response=SimpleNamespace(edit_message=AsyncMock())
    )

    await view._move(interaction, -1)
    assert view.index == 1
    assert interaction.response.edit_message.await_args.kwargs[
        "embed"
    ].footer.text == "Result 2 of 2"

    await view._move(interaction, 1)
    assert view.index == 0


@pytest.mark.asyncio
async def test_carousel_timeout_disables_controls():
    view = ImageCarousel("cats", [image_result(1), image_result(2)])
    view.message = SimpleNamespace(edit=AsyncMock())

    await view.on_timeout()

    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once_with(view=view)


def test_single_result_disables_navigation():
    view = ImageCarousel("cats", [image_result(1)])

    assert all(child.disabled for child in view.children)
    assert view.make_embed().footer.text == "Result 1 of 1"


def test_ask_and_askwann_are_separate_commands():
    assert Search.ask.name == "ask"
    assert Search.ask_wann.name == "askwann"
    assert Search.ask._buckets._cooldown.per == 10
    assert Search.ask_wann._buckets._cooldown.per == 10
