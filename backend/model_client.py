"""Bounded provider failover for real tool selection; no credentials in traces."""
import asyncio
import os
import time
from dataclasses import dataclass, field
from openai import AsyncOpenAI, APIError, APITimeoutError

PROVIDERS = {
    "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-flash"),
    "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "openai": ("OPENAI_API_KEY", None, "gpt-4.1"),
}

def gemini_keys():
    names = ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3")
    values = os.getenv("GEMINI_API_KEYS", "").split(",") if os.getenv("GEMINI_API_KEYS", "").strip() else [os.getenv(n, "") for n in names]
    return list(dict.fromkeys(v.strip() for v in values if len(v.strip()) >= 20))

def settings():
    provider = os.getenv("LLM_PROVIDER", "gemini").strip()
    if provider not in PROVIDERS:
        raise ValueError("Use gemini, groq, or openai")
    key_name, base, default = PROVIDERS[provider]
    keys = gemini_keys() if provider == "gemini" else [os.getenv(key_name, "").strip()]
    return dict(provider=provider, key_name=key_name, key=keys[0] if keys else "",
                base=base, model=os.getenv("LLM_MODEL", "").strip() or default)

def public_settings():
    s = settings()
    configured = len(s["key"]) >= 20 or (s["provider"] == "gemini" and len(os.getenv("GROQ_API_KEY", "").strip()) >= 20)
    return dict(provider=s["provider"], model=s["model"], configured=configured, key_name=s["key_name"])

@dataclass(frozen=True)
class Route:
    provider: str
    model: str
    slot: int
    key: str = field(repr=False)
    base: str | None = None

def routes():
    s = settings()
    if s["provider"] != "gemini":
        return [Route(s["provider"], s["model"], 1, s["key"], s["base"])] if len(s["key"]) >= 20 else []
    # Retired models may be explicitly configured, but are not defaults.
    fallback = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash-lite").split(",")
    models = list(dict.fromkeys([s["model"], *(m.strip() for m in fallback if m.strip())]))
    pool = [Route("gemini", model, i, key, s["base"])
            for model in models for i, key in enumerate(gemini_keys(), 1)]
    key = os.getenv("GROQ_API_KEY", "").strip()
    if len(key) >= 20:
        pool.append(Route("groq", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip(), 1, key, PROVIDERS["groq"][1]))
    return pool

class ModelPoolExhausted(RuntimeError):
    """Sanitized failure: no raw provider payload or credentials."""

class ModelClient:
    measurement_source = "LIVE_PROVIDER"
    def __init__(self):
        self.pool = routes()
        if not self.pool:
            raise ValueError("Configure a model API key in server environment settings")
        self.clients = {}
        self.attempts = []
        self.last_selection = None
        self.preferred = 0
        # Selection must finish before the 120-second run lease.
        self.deadline_seconds = min(90, max(5, float(os.getenv("LLM_SELECTION_TIMEOUT_SECONDS", "90"))))

    async def choose(self, messages, tools):
        deadline = time.monotonic() + self.deadline_seconds
        self.attempts = []
        self.last_selection = None
        terminal, cooldown = set(), {}
        order = list(range(self.preferred, len(self.pool))) + list(range(self.preferred))
        for round_number in range(3):
            if round_number:
                delay = 2 ** (round_number - 1)
                if time.monotonic() + delay >= deadline:
                    break
                await asyncio.sleep(delay)
            for index in order:
                route = self.pool[index]
                if index in terminal or cooldown.get(index, 0) > time.monotonic():
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                record = dict(provider=route.provider, model=route.model, key_slot=route.slot)
                self.attempts.append(record)
                if index not in self.clients:
                    self.clients[index] = AsyncOpenAI(api_key=route.key, base_url=route.base, timeout=20, max_retries=0)
                try:
                    async with asyncio.timeout(min(20, self.deadline_seconds / (len(self.pool) + 1), remaining)):
                        result = await self.clients[index].chat.completions.create(
                            model=route.model, messages=messages, tools=tools,
                            tool_choice="auto", parallel_tool_calls=False, max_tokens=900)
                    if result.usage is None:
                        raise ValueError("Provider omitted usage; refusing to invent benchmark tokens")
                    record["status"] = "success"
                    self.last_selection = dict(provider=route.provider, model=route.model)
                    self.preferred = index
                    return result.choices[0].message.model_dump(exclude_none=True), result.usage.total_tokens
                except (APIError, TimeoutError) as exc:
                    status = getattr(exc, "status_code", None)
                    timeout = isinstance(exc, (TimeoutError, APITimeoutError))
                    record["status"] = status or ("timeout" if timeout else "network")
                    if status not in (429, 500, 502, 503, 504) and not timeout:
                        terminal.add(index)
                    response = getattr(exc, "response", None)
                    try:
                        retry_after = float(response.headers.get("retry-after", "0")) if response is not None else 0
                    except (ValueError, TypeError):
                        retry_after = 0
                    cooldown[index] = time.monotonic() + min(max(retry_after, 0), 86400)
        summary = "; ".join(f"{a['provider']}/{a['model']} slot {a['key_slot']}: {a['status']}" for a in self.attempts)
        raise ModelPoolExhausted("Configured model pool exhausted within bounded retries. " + summary)

    async def close(self):
        for client in self.clients.values():
            await client.close()
