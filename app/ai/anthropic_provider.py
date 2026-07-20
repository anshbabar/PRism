"""Real review provider: Claude via the Anthropic SDK.

Enabled with ``LLM_PROVIDER=anthropic``. Uses structured outputs
(``output_config.format`` with ``REVIEW_JSON_SCHEMA``) so the model returns JSON
matching our schema, plus adaptive thinking. The ``anthropic`` package is
imported lazily so the mock/test path never requires it.

Requires a recent ``anthropic`` SDK (for ``output_config``) and credentials via
``ANTHROPIC_API_KEY`` (or an ``ant auth login`` profile). This path is exercised
only when a real key is configured.
"""

from __future__ import annotations

import json
from typing import Any

from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.provider import ReviewInput
from app.ai.schema import REVIEW_JSON_SCHEMA
from app.core.config import Settings


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model = settings.llm_model

    def generate_review(self, req: ReviewInput) -> dict[str, Any]:
        import anthropic  # lazy: only needed for the real provider

        # Typed as Any to insulate this call from SDK type drift; the request
        # shape follows the current Messages API (structured outputs).
        client: Any = anthropic.Anthropic(api_key=self._settings.anthropic_api_key or None)

        response = client.messages.create(
            model=self.model,
            max_tokens=self._settings.llm_max_tokens,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"format": {"type": "json_schema", "schema": REVIEW_JSON_SCHEMA}},
            messages=[{"role": "user", "content": build_user_prompt(req)}],
        )

        text = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            None,
        )
        if not text:
            raise ValueError("Anthropic response contained no text block")
        return json.loads(text)
