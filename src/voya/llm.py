"""LLM harness: one client interface, provider adapters, and the safety rails.

- `LLMClient.complete_json()` is the only way the app talks to a model.
- `OpenRouterClient` speaks OpenRouter's OpenAI-compatible chat API.
- `FakeLLM` replays scripted replies; tests and the no-key mode use it.
- `Harness` wraps any client with a per-task cost cap, per-user daily and
  global monthly caps (kill switch), retries on retryable errors only, a
  circuit breaker, and a trace span per call.

The model never receives secrets, exact coordinates or user IDs, and its
output is always parsed and validated by code before use.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

import httpx

from voya import obs
from voya.store import Store

D = Decimal


class LLMError(Exception):
    def __init__(self, msg: str, retryable: bool = False) -> None:
        super().__init__(msg)
        self.retryable = retryable


class BudgetExceeded(Exception):
    pass


@dataclass
class LLMResult:
    data: dict
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Decimal = D(0)


class LLMClient(Protocol):
    name: str

    def complete_json(
        self, system: str, user: str, schema_hint: str, max_tokens: int = 600
    ) -> LLMResult: ...


class OpenRouterClient:
    """OpenRouter chat completions (OpenAI-compatible). Key from OPENROUTER_API_KEY."""

    name = "openrouter"
    URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.model = model
        self._key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.timeout = timeout
        # Fallback price if the provider doesn't report cost ($ per 1M tokens).
        self.in_price = D(os.environ.get("VOYA_LLM_PRICE_IN_PER_M", "1.00"))
        self.out_price = D(os.environ.get("VOYA_LLM_PRICE_OUT_PER_M", "4.00"))

    def complete_json(
        self, system: str, user: str, schema_hint: str, max_tokens: int = 600
    ) -> LLMResult:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": system + "\nReply with one JSON object only. Schema: " + schema_hint,
                },
                {"role": "user", "content": user},
            ],
            "usage": {"include": True},
        }
        try:
            r = httpx.post(
                self.URL,
                json=body,
                timeout=self.timeout,
                headers={"Authorization": f"Bearer {self._key}", "X-Title": "VOYA"},
            )
        except httpx.TransportError as e:
            raise LLMError(f"network: {type(e).__name__}", retryable=True) from e
        if r.status_code in (408, 409, 429) or r.status_code >= 500:
            raise LLMError(f"status {r.status_code}", retryable=True)
        if r.status_code >= 400:
            raise LLMError(f"status {r.status_code}", retryable=False)
        payload = r.json()
        try:
            text = payload["choices"][0]["message"]["content"]
            data = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise LLMError("unparseable model output", retryable=False) from e
        usage = payload.get("usage") or {}
        tin, tout = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
        cost = usage.get("cost")
        usd = (
            D(str(cost))
            if cost is not None
            else (self.in_price * tin + self.out_price * tout) / D(1_000_000)
        )
        return LLMResult(data, payload.get("model", self.model), tin, tout, usd)


@dataclass
class FakeLLM:
    """Scripted replies, in order. An exception in the script is raised instead."""

    script: list[dict | Exception] = field(default_factory=list)
    name: str = "fake"
    cost_per_call: Decimal = D("0.001")
    calls: list[str] = field(default_factory=list)

    def complete_json(
        self, system: str, user: str, schema_hint: str, max_tokens: int = 600
    ) -> LLMResult:
        self.calls.append(user)
        if not self.script:
            raise LLMError("fake: no scripted reply", retryable=False)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResult(item, "fake-model", 100, 20, self.cost_per_call)


@dataclass
class Limits:
    task_usd: Decimal = D(os.environ.get("VOYA_TASK_BUDGET_USD", "0.15"))
    user_day_usd: Decimal = D(os.environ.get("VOYA_USER_DAILY_BUDGET_USD", "1.50"))
    month_usd: Decimal = D(os.environ.get("VOYA_MONTHLY_BUDGET_USD", "30"))
    max_retries: int = 2
    breaker_failures: int = 5
    breaker_open_s: float = 60.0


class Harness:
    """Every model call goes through here."""

    def __init__(
        self, client: LLMClient | None, store: Store, limits: Limits | None = None
    ) -> None:
        self.client = client
        self.store = store
        self.limits = limits or Limits()
        self._failures = 0
        self._open_until = 0.0

    @property
    def available(self) -> bool:
        return self.client is not None and time.monotonic() >= self._open_until

    def _scopes(self, user_scope: str) -> list[tuple[str, Decimal]]:
        now = datetime.now(UTC)
        return [
            (f"month:{now:%Y-%m}", self.limits.month_usd),
            (f"user:{user_scope}:{now:%Y-%m-%d}", self.limits.user_day_usd),
        ]

    def call(
        self,
        system: str,
        user: str,
        schema_hint: str,
        user_scope: str,
        task_spent: Decimal,
        estimate_usd: Decimal = D("0.01"),
    ) -> LLMResult:
        if self.client is None:
            raise LLMError("no model configured", retryable=False)
        if not self.available:
            raise LLMError("circuit open", retryable=False)
        if task_spent + estimate_usd > self.limits.task_usd:
            raise BudgetExceeded("task budget")
        for scope, cap in self._scopes(user_scope):
            if self.store.ai_spent(scope) + estimate_usd > cap:
                raise BudgetExceeded(scope.split(":")[0] + " budget")
        attempt = 0
        while True:
            with obs.span("llm.call", provider=self.client.name, attempt=attempt) as sp:
                try:
                    res = self.client.complete_json(system, user, schema_hint)
                except LLMError as e:
                    sp.update(error=str(e), retryable=e.retryable)
                    self._failures += 1
                    if self._failures >= self.limits.breaker_failures:
                        self._open_until = time.monotonic() + self.limits.breaker_open_s
                        obs.event("breaker.open", seconds=self.limits.breaker_open_s)
                    if e.retryable and attempt < self.limits.max_retries:
                        attempt += 1
                        time.sleep(min(2.0, 0.2 * 2**attempt) * random.random())
                        continue
                    raise
                sp.update(
                    model=res.model,
                    input_tokens=res.input_tokens,
                    output_tokens=res.output_tokens,
                    cost_usd=str(res.cost_usd),
                )
            self._failures = 0
            for scope, _ in self._scopes(user_scope):
                self.store.add_ai_spend(scope, res.cost_usd)
            return res


def client_from_env() -> LLMClient | None:
    if os.environ.get("OPENROUTER_API_KEY"):
        return OpenRouterClient(model=os.environ.get("VOYA_LLM_MODEL_HELPER", "openrouter/auto"))
    return None
