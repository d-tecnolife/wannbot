from unittest.mock import AsyncMock

import pytest

from cogs.search.providers import (
    GeminiClient,
    SerpAPIClient,
    parse_ai_overview,
    parse_image_results,
)


def test_parse_image_results_filters_invalid_items_and_limits_results():
    payload = {
        "images_results": [
            {
                "title": "Original",
                "original": "https://images.example/original.jpg",
                "thumbnail": "https://images.example/thumb.jpg",
                "link": "https://example.com/page",
                "source": "example.com",
            },
            {
                "title": "Thumbnail fallback",
                "original": "data:image/png;base64,bad",
                "thumbnail": "https://images.example/fallback.jpg",
                "link": "https://example.com/other",
            },
            {
                "title": "Missing source page",
                "original": "https://images.example/no-source.jpg",
            },
        ]
    }

    results = parse_image_results(payload, limit=2)

    assert [result.title for result in results] == [
        "Original",
        "Thumbnail fallback",
    ]
    assert results[0].image_url == "https://images.example/original.jpg"
    assert results[1].image_url == "https://images.example/fallback.jpg"
    assert results[1].source == "example.com"


def test_parse_ai_overview_formats_blocks_and_deduplicates_references():
    payload = {
        "ai_overview": {
            "text_blocks": [
                {"type": "heading", "snippet": "Summary"},
                {"type": "paragraph", "snippet": "A concise answer."},
                {
                    "type": "list",
                    "list": [
                        {"snippet": "First point"},
                        {"snippet": "Second point"},
                    ],
                },
            ],
            "references": [
                {"title": "Source A", "link": "https://example.com/a"},
                {"title": "Duplicate", "link": "https://example.com/a"},
                {"source": "example.org", "url": "https://example.org/b"},
                {"title": "Bad", "link": "javascript:alert(1)"},
            ],
        }
    }

    overview = parse_ai_overview(payload)

    assert overview is not None
    assert overview.text == (
        "**Summary**\n\nA concise answer.\n\n• First point\n\n• Second point"
    )
    assert [reference.url for reference in overview.references] == [
        "https://example.com/a",
        "https://example.org/b",
    ]


def test_parse_ai_overview_requires_text():
    assert parse_ai_overview({"ai_overview": {"page_token": "token"}}) is None
    assert parse_ai_overview({}) is None


@pytest.mark.asyncio
async def test_ai_overview_uses_followup_page_token():
    client = object.__new__(SerpAPIClient)
    client._request = AsyncMock(
        side_effect=[
            {"ai_overview": {"page_token": "short-lived-token"}},
            {
                "ai_overview": {
                    "text_blocks": [{"type": "paragraph", "snippet": "Answer"}],
                    "references": [],
                }
            },
        ]
    )

    overview = await client.ai_overview("query", safe=True)

    assert overview is not None
    assert overview.text == "Answer"
    assert client._request.await_count == 2
    assert client._request.await_args_list[0].args[0]["safe"] == "active"
    assert client._request.await_args_list[1].args[0] == {
        "engine": "google_ai_overview",
        "page_token": "short-lived-token",
    }


@pytest.mark.asyncio
async def test_ai_overview_does_not_follow_up_without_token():
    client = object.__new__(SerpAPIClient)
    client._request = AsyncMock(return_value={"organic_results": []})

    overview = await client.ai_overview("query", safe=False)

    assert overview is None
    assert client._request.await_count == 1
    assert client._request.await_args.args[0]["safe"] == "off"


@pytest.mark.asyncio
async def test_gemini_answer_includes_configured_persona():
    response = type(
        "Response",
        (),
        {"output_text": "Persona answer", "status": "completed"},
    )()
    create_interaction = AsyncMock(return_value=response)
    client = object.__new__(GeminiClient)
    client.model = "test-model"
    client.persona = "Speak like a friendly ship computer."
    client.max_output_tokens = 4096
    client.thinking_level = "medium"
    client.max_continuations = 1
    client.client = type(
        "Client",
        (),
        {
            "aio": type(
                "AsyncClient",
                (),
                {
                    "interactions": type(
                        "Interactions",
                        (),
                        {"create": create_interaction},
                    )()
                },
            )()
        },
    )()

    answer = await client.answer("What is a pulsar?")

    assert answer == "Persona answer"
    request = create_interaction.await_args.kwargs
    assert request["input"] == "What is a pulsar?"
    assert request["store"] is False
    assert request["generation_config"]["max_output_tokens"] == 4096
    assert request["generation_config"]["thinking_level"] == "medium"
    assert "Speak like a friendly ship computer." in request["system_instruction"]
    assert "Do not claim to have searched the web" in request["system_instruction"]


@pytest.mark.asyncio
async def test_gemini_continues_an_incomplete_answer_once():
    first = type(
        "Response",
        (),
        {"output_text": "First part.", "status": "incomplete"},
    )()
    second = type(
        "Response",
        (),
        {"output_text": "Second part.", "status": "completed"},
    )()
    create_interaction = AsyncMock(side_effect=[first, second])
    client = object.__new__(GeminiClient)
    client.model = "test-model"
    client.persona = ""
    client.max_output_tokens = 4096
    client.thinking_level = "medium"
    client.max_continuations = 1
    client.client = type(
        "Client",
        (),
        {
            "aio": type(
                "AsyncClient",
                (),
                {
                    "interactions": type(
                        "Interactions",
                        (),
                        {"create": create_interaction},
                    )()
                },
            )()
        },
    )()

    answer = await client.answer("Compare two builds.")

    assert answer == "First part.\n\nSecond part."
    assert create_interaction.await_count == 2
    continuation = create_interaction.await_args_list[1].kwargs["input"]
    assert "Continue the answer" in continuation
    assert "First part." in continuation
