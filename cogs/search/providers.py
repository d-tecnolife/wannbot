from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class ProviderError(RuntimeError):
    """An expected error returned by an external search provider."""

    def __init__(self, message: str, *, code: str = "upstream"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ImageResult:
    title: str
    image_url: str
    thumbnail_url: str | None
    source_url: str
    source: str


@dataclass(frozen=True)
class Reference:
    title: str
    url: str


@dataclass(frozen=True)
class AIOverview:
    text: str
    references: tuple[Reference, ...]


@dataclass(frozen=True)
class ChatProvider:
    name: str
    api_key: str | None
    base_url: str
    model: str

    @property
    def endpoint(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_image_results(payload: dict[str, Any], *, limit: int = 10) -> list[ImageResult]:
    results: list[ImageResult] = []
    for item in payload.get("images_results") or []:
        if not isinstance(item, dict):
            continue

        original = item.get("original")
        thumbnail = item.get("thumbnail")
        source_url = item.get("link")
        image_url = original if _is_http_url(original) else thumbnail

        if not _is_http_url(image_url) or not _is_http_url(source_url):
            continue

        source = str(item.get("source") or urlparse(source_url).netloc)
        results.append(
            ImageResult(
                title=str(item.get("title") or "Image result"),
                image_url=image_url,
                thumbnail_url=thumbnail if _is_http_url(thumbnail) else None,
                source_url=source_url,
                source=source,
            )
        )
        if len(results) == limit:
            break
    return results


def _append_text_block(block: Any, output: list[str], *, list_item: bool = False) -> None:
    if isinstance(block, str):
        text = block.strip()
        if text:
            output.append(f"• {text}" if list_item else text)
        return
    if not isinstance(block, dict):
        return

    snippet = block.get("snippet")
    block_type = block.get("type")
    if isinstance(snippet, str) and snippet.strip():
        text = snippet.strip()
        if block_type == "heading":
            output.append(f"**{text}**")
        elif list_item:
            output.append(f"• {text}")
        else:
            output.append(text)

    for key in ("list", "list_items", "items"):
        children = block.get(key)
        if isinstance(children, list):
            for child in children:
                _append_text_block(child, output, list_item=True)


def parse_ai_overview(payload: dict[str, Any]) -> AIOverview | None:
    overview = payload.get("ai_overview")
    if not isinstance(overview, dict):
        return None

    parts: list[str] = []
    for block in overview.get("text_blocks") or []:
        _append_text_block(block, parts)
    if not parts:
        return None

    references: list[Reference] = []
    seen_urls: set[str] = set()
    for item in overview.get("references") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("link") or item.get("url")
        if not _is_http_url(url) or url in seen_urls:
            continue
        seen_urls.add(url)
        references.append(
            Reference(
                title=str(item.get("title") or item.get("source") or urlparse(url).netloc),
                url=url,
            )
        )

    return AIOverview(text="\n\n".join(parts), references=tuple(references))


class SerpAPIClient:
    def __init__(self, api_key: str | None):
        self.api_key = api_key
        timeout = aiohttp.ClientTimeout(total=25)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        await self.session.close()

    async def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("SerpAPI is not configured.", code="configuration")

        request_params = {**params, "api_key": self.api_key, "output": "json"}
        try:
            async with self.session.get(SERPAPI_ENDPOINT, params=request_params) as response:
                if response.status in {401, 403}:
                    raise ProviderError(
                        "The SerpAPI credential was rejected.", code="authentication"
                    )
                if response.status == 429:
                    raise ProviderError(
                        "The SerpAPI free-tier limit has been reached.", code="quota"
                    )
                if response.status >= 400:
                    raise ProviderError(
                        f"SerpAPI returned HTTP {response.status}.", code="upstream"
                    )
                payload = await response.json(content_type=None)
        except TimeoutError as exc:
            raise ProviderError("SerpAPI timed out.", code="timeout") from exc
        except aiohttp.ClientError as exc:
            raise ProviderError("Could not reach SerpAPI.", code="network") from exc
        except (TypeError, ValueError) as exc:
            raise ProviderError("SerpAPI returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ProviderError("SerpAPI returned an invalid response.")
        if payload.get("error"):
            message = str(payload["error"])
            code = "quota" if "limit" in message.lower() else "upstream"
            raise ProviderError(message, code=code)
        return payload

    async def image_search(self, query: str, *, safe: bool) -> list[ImageResult]:
        payload = await self._request(
            {
                "engine": "google_images",
                "q": query,
                "safe": "active" if safe else "off",
            }
        )
        return parse_image_results(payload)

    async def ai_overview(self, query: str, *, safe: bool) -> AIOverview | None:
        payload = await self._request(
            {
                "engine": "google",
                "q": query,
                "safe": "active" if safe else "off",
            }
        )
        overview = parse_ai_overview(payload)
        if overview:
            return overview

        raw_overview = payload.get("ai_overview")
        if not isinstance(raw_overview, dict) or not raw_overview.get("page_token"):
            return None

        followup = await self._request(
            {
                "engine": "google_ai_overview",
                "page_token": raw_overview["page_token"],
            }
        )
        return parse_ai_overview(followup)


class AIClient:
    def __init__(
        self,
        providers: tuple[ChatProvider, ...],
        persona: str = "",
        max_output_tokens: int = 2048,
        max_words: int = 700,
    ):
        self.providers = providers
        self.persona = persona
        self.max_output_tokens = max_output_tokens
        self.max_words = max_words
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self) -> None:
        await self.session.close()

    async def answer(self, query: str) -> str:
        providers = tuple(provider for provider in self.providers if provider.api_key)
        if not providers:
            raise ProviderError("The AI provider is not configured.", code="configuration")

        system_instruction = (
            "Answer the user's question directly and stay focused, but include enough "
            "detail to fully answer comparisons and calculations. Do not claim to have "
            "searched the web and do not invent citations. Finish every answer cleanly "
            f"and never intentionally stop mid-sentence. Never exceed {self.max_words} "
            "words. This is only a maximum, not a target: answer as briefly as appropriate "
            "and never add padding to approach the limit."
        )
        if self.persona:
            system_instruction += (
                "\n\nAdopt the following persona while preserving accuracy and following "
                f"the preceding requirements:\n{self.persona}"
            )

        for index, provider in enumerate(providers):
            try:
                return await self._answer(provider, query, system_instruction)
            except ProviderError as exc:
                if exc.code not in {"configuration", "quota"} or index == len(
                    providers
                ) - 1:
                    raise

        raise ProviderError("No AI provider could generate an answer.")

    async def _answer(
        self, provider: ChatProvider, query: str, system_instruction: str
    ) -> str:
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": query},
            ],
            "max_completion_tokens": self.max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with self.session.post(
                provider.endpoint, json=payload, headers=headers
            ) as response:
                if response.status in {401, 403}:
                    raise ProviderError(
                        "The AI provider rejected the configured API key.",
                        code="authentication",
                    )
                if response.status == 404:
                    raise ProviderError(
                        f"AI model {provider.model!r} is not available from {provider.name}.",
                        code="configuration",
                    )
                if response.status == 429:
                    raise ProviderError(
                        "The AI provider's free-tier or rate limit has been reached.",
                        code="quota",
                    )
                if response.status >= 400:
                    raise ProviderError(
                        f"The AI provider returned HTTP {response.status}.",
                        code="upstream",
                    )
                result = await response.json(content_type=None)
        except TimeoutError as exc:
            raise ProviderError("The AI provider timed out.", code="timeout") from exc
        except aiohttp.ClientError as exc:
            raise ProviderError("Could not reach the AI provider.", code="network") from exc
        except (TypeError, ValueError) as exc:
            raise ProviderError("The AI provider returned invalid JSON.") from exc

        try:
            choice = result["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("The AI provider returned an invalid response.") from exc
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("The AI provider returned no usable answer.")
        if choice.get("finish_reason") == "length":
            raise ProviderError(
                "The AI model hit its output limit before finishing. Try a narrower question.",
                code="output_limit",
            )
        return text.strip()
