from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from app.schemas import (
    AnalyzeMaterialResponse,
    ScaffoldPlanResponse,
)


ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


class LearningServiceError(Exception):
    """Base error for Keystone learning analysis failures."""


class MissingAPIKeyError(LearningServiceError):
    """Raised when the Anthropic API key is not configured."""


class InvalidAIResponseError(LearningServiceError):
    """Raised when the model does not return Keystone's expected JSON shape."""


class AnthropicLearningService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")).strip()
        self.model = (model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)).strip()
        self.timeout_seconds = timeout_seconds

    async def analyze_material(
        self,
        material: str,
        subject: str | None,
        level: str | None,
    ) -> AnalyzeMaterialResponse:
        prompt = self._analysis_prompt(material=material, subject=subject, level=level)
        response_text = await self._send_message(prompt=prompt, max_tokens=1800)
        return self.parse_analysis_json(response_text)

    async def scaffold_plan(
        self,
        analysis: AnalyzeMaterialResponse,
        ratings: dict[str, str],
    ) -> ScaffoldPlanResponse:
        prompt = self._scaffold_prompt(analysis=analysis, ratings=ratings)
        response_text = await self._send_message(prompt=prompt, max_tokens=1600)
        return self.parse_scaffold_json(response_text)

    async def _send_message(self, prompt: str, max_tokens: int) -> str:
        if not self.api_key:
            raise MissingAPIKeyError("Add ANTHROPIC_API_KEY to run Keystone analysis.")

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise LearningServiceError(
                f"Anthropic returned HTTP {status}. Check the API key, model, and request size."
            ) from exc
        except httpx.HTTPError as exc:
            raise LearningServiceError("Keystone could not reach Anthropic. Try again in a moment.") from exc

        body = response.json()
        try:
            text_blocks = [
                block["text"]
                for block in body["content"]
                if block.get("type") == "text" and isinstance(block.get("text"), str)
            ]
        except (KeyError, TypeError, AttributeError) as exc:
            raise InvalidAIResponseError("Anthropic returned an unexpected message shape.") from exc

        if not text_blocks:
            raise InvalidAIResponseError("Anthropic returned no text content.")

        return "\n".join(text_blocks)

    @classmethod
    def parse_analysis_json(cls, response_text: str) -> AnalyzeMaterialResponse:
        data = cls._load_json_object(response_text)
        try:
            return AnalyzeMaterialResponse.model_validate(data)
        except ValidationError as exc:
            raise InvalidAIResponseError(
                f"Anthropic response was missing required Keystone analysis fields: {exc}"
            ) from exc

    @classmethod
    def parse_scaffold_json(cls, response_text: str) -> ScaffoldPlanResponse:
        data = cls._load_json_object(response_text)
        try:
            return ScaffoldPlanResponse.model_validate(data)
        except ValidationError as exc:
            raise InvalidAIResponseError(
                f"Anthropic response was missing required Keystone scaffold fields: {exc}"
            ) from exc

    @staticmethod
    def _load_json_object(response_text: str) -> dict[str, Any]:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1:
            cleaned = cleaned[first_brace : last_brace + 1]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise InvalidAIResponseError("Anthropic must return structured JSON for Keystone.") from exc

        if not isinstance(data, dict):
            raise InvalidAIResponseError("Anthropic must return a JSON object for Keystone.")
        return data

    @staticmethod
    def _analysis_prompt(material: str, subject: str | None, level: str | None) -> str:
        subject_line = subject or "college STEM"
        level_line = level or "college"
        return f"""
You are Keystone AI, an educational scaffolding assistant for college STEM students.

Analyze the pasted material and return only JSON with exactly these top-level keys:
- target_concepts: 3-5 concepts directly taught or required by the material.
- prerequisites: 4-7 foundational concepts that could block comprehension.
- familiarity_checks: one short self-check prompt for each prerequisite.

Rules:
- Use stable kebab-case ids.
- Every prerequisite.supports value must reference a target_concepts id.
- Evidence must quote or paraphrase short phrases from the pasted material.
- Do not include markdown, commentary, or extra keys.

JSON shape:
{{
  "target_concepts": [
    {{"id": "chain-rule", "title": "Chain rule", "summary": "One sentence.", "evidence": ["short evidence"]}}
  ],
  "prerequisites": [
    {{
      "id": "function-composition",
      "title": "Function composition",
      "why_it_matters": "One sentence explaining the blocker.",
      "supports": ["chain-rule"],
      "evidence": ["short evidence"]
    }}
  ],
  "familiarity_checks": [
    {{"concept_id": "function-composition", "prompt": "How comfortable are you ...?"}}
  ]
}}

Subject: {subject_line}
Level: {level_line}
Material:
\"\"\"{material}\"\"\"
""".strip()

    @staticmethod
    def _scaffold_prompt(analysis: AnalyzeMaterialResponse, ratings: dict[str, str]) -> str:
        return f"""
You are Keystone AI. Use the prior concept analysis plus student familiarity ratings to rank likely foundational blockers.

Return only JSON with exactly these top-level keys:
- gaps: 2-5 ranked blockers, highest severity first.
- study_sequence: 3-6 concrete study actions in the order the student should take them.
- confidence_notes: 1-3 short caveats about evidence quality.

Rules:
- Prioritize prerequisites rated unknown or weak.
- Use severity values only: high, medium, low.
- Every gap.concept_id must reference a prerequisite id from the analysis.
- Do not include markdown, commentary, or extra keys.

JSON shape:
{{
  "gaps": [
    {{
      "concept_id": "function-composition",
      "title": "Function composition",
      "severity": "high",
      "why_it_blocks_learning": "One sentence.",
      "next_step": "One concrete next step."
    }}
  ],
  "study_sequence": ["Action one.", "Action two."],
  "confidence_notes": ["Based on one pasted excerpt and self-ratings."]
}}

Analysis JSON:
{analysis.model_dump_json()}

Student ratings JSON:
{json.dumps(ratings, sort_keys=True)}
""".strip()
