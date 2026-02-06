from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal

import httpx

from .models import MeetingAnalysisData, Outcome, Sentiment


SCHEMA_VERSION = "1"
PROMPT_VERSION = "1"


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class AgentConfig:
    provider: Literal["openai", "groq"]
    model: str
    api_key: str | None
    base_url: str = OPENAI_BASE_URL


class AnalysisAgent:
    """
    Option A: Single-purpose agent.
    - Input: transcript text
    - Output: MeetingAnalysisData (strict, bounded schema)
    - Constraints: deterministic purpose; JSON-only output; validated by Pydantic
    """

    def __init__(self, cfg: AgentConfig):
        self._cfg = cfg

    async def analyze(self, transcript: str) -> tuple[str, str, str, MeetingAnalysisData]:
        if not self._cfg.api_key:
            raise ValueError(
                "LLM API key required. Set GROQ_API_KEY (free tier: console.groq.com) or OPENAI_API_KEY in .env."
            )
        derived = await self._llm_analyze(transcript)
        return SCHEMA_VERSION, PROMPT_VERSION, self._cfg.model, derived

    def _mock_analyze(self, transcript: str) -> MeetingAnalysisData:
        # Deterministic lightweight extraction (no network) to keep app usable without a key.
        text = transcript.lower()
        topics: list[str] = []
        for kw in ("pricing", "timeline", "security", "integration", "budget", "onboarding", "renewal"):
            if kw in text:
                topics.append(kw)

        objections: list[str] = []
        if "too expensive" in text or "expensive" in text:
            objections.append("pricing concern")
        if "need approval" in text or "talk to my boss" in text:
            objections.append("needs internal approval")

        commitments: list[str] = []
        if "i will" in text or "we will" in text:
            commitments.append("follow-up action stated")

        sentiment: Sentiment = "neutral"
        if any(w in text for w in ("angry", "frustrated", "upset")):
            sentiment = "negative"
        elif any(w in text for w in ("excited", "great", "love", "perfect")):
            sentiment = "positive"

        outcome: Outcome = "unknown"
        if "next step" in text or "send proposal" in text or "schedule" in text:
            outcome = "advanced"
        elif "not interested" in text or "no" in text:
            outcome = "stalled"

        summary = "Mock analysis (no LLM key): extracted basic topics/objections/commitments."
        return MeetingAnalysisData(
            topics=topics[:25],
            objections=objections[:25],
            commitments=commitments[:25],
            sentiment=sentiment,
            outcome=outcome,
            summary=summary,
        )

    async def _llm_analyze(self, transcript: str) -> MeetingAnalysisData:
        """
        Calls OpenAI-compatible Chat Completions (OpenAI or Groq).
        Requires JSON output; we validate into MeetingAnalysisData to bound the AI.
        """
        api_key = self._cfg.api_key
        assert api_key is not None
        base_url = self._cfg.base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        system = (
            "You are an analysis extraction agent. "
            "You must output ONLY valid JSON that matches the required schema. "
            "No prose, no markdown, no extra keys."
        )
        user = (
            "Extract structured sales/coaching signals from the transcript.\n\n"
            "Schema (JSON object):\n"
            "{\n"
            '  \"topics\": string[],\n'
            '  \"objections\": string[],\n'
            '  \"commitments\": string[],\n'
            '  \"sentiment\": \"very_negative\"|\"negative\"|\"neutral\"|\"positive\"|\"very_positive\",\n'
            '  \"outcome\": \"advanced\"|\"stalled\"|\"closed_won\"|\"closed_lost\"|\"unknown\",\n'
            '  \"summary\": string\n'
            "}\n\n"
            "Constraints:\n"
            "- Keep each list <= 10 items\n"
            "- Summary <= 600 characters\n\n"
            "Transcript:\n"
            f"{transcript}"
        )

        payload = {
            "model": self._cfg.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=40) as client:
            try:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                body = e.response.text
                if e.response.status_code == 401:
                    raise ValueError(f"Invalid API key. Check {self._cfg.provider.upper()}_API_KEY.") from e
                if e.response.status_code == 429:
                    raise ValueError(f"{self._cfg.provider} rate limit exceeded. Try again later.") from e
                raise ValueError(f"{self._cfg.provider} API error ({e.response.status_code}): {body[:200]}") from e
            except httpx.RequestError as e:
                raise ValueError(f"Request to {self._cfg.provider} failed: {e}") from e

        content = data["choices"][0]["message"]["content"]
        content = _strip_code_fences(str(content))
        try:
            return MeetingAnalysisData.model_validate_json(content)
        except Exception as e:
            raise ValueError(f"LLM returned invalid schema: {e}. Raw: {content[:300]}") from e


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    # If the model accidentally wraps JSON in ```json ...```, remove fences.
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def default_agent() -> AnalysisAgent:
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return AnalysisAgent(
            AgentConfig(provider="groq", model=model, api_key=groq_key, base_url=GROQ_BASE_URL)
        )
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return AnalysisAgent(
            AgentConfig(provider="openai", model=model, api_key=openai_key, base_url=OPENAI_BASE_URL)
        )
    return AnalysisAgent(AgentConfig(provider="openai", model="mock", api_key=None))

