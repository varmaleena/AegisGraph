"""Deterministic provider failure tests; no network requests or real API keys."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from openai import RateLimitError, InternalServerError, NotFoundError, APITimeoutError
from backend import model_client as m

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for name in ("LLM_MODEL","GROQ_MODEL","GEMINI_API_KEYS","GEMINI_API_KEY","GEMINI_API_KEY_2",
                 "GEMINI_API_KEY_3","GROQ_API_KEY","OPENAI_API_KEY","GEMINI_FALLBACK_MODELS"):
        monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv("LLM_PROVIDER","gemini")

def error(cls,status=429,retry=None):
    req=httpx.Request("POST","https://provider.invalid")
    if cls is APITimeoutError:return cls(request=req)
    response=httpx.Response(status,request=req,headers={"retry-after":str(retry)} if retry else {})
    return cls("secret-provider-payload",response=response,body={})

def response():
    msg=SimpleNamespace(model_dump=lambda **kw:{"role":"assistant","tool_calls":[{"id":"test"}]})
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)],usage=SimpleNamespace(total_tokens=42))

def fake(monkeypatch,effects):
    calls=[];closed=[]
    class Client:
        def __init__(self,api_key,base_url,**kw):
            self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
            self.key=api_key
        async def create(self,**kw):
            calls.append((self.key,kw["model"]))
            item=effects.pop(0)
            if isinstance(item,Exception):raise item
            return item
        async def close(self):closed.append(self.key)
    monkeypatch.setattr(m,"AsyncOpenAI",Client)
    monkeypatch.setattr(m.asyncio,"sleep",AsyncMock())
    return calls,closed

def test_rotation_model_fallback_and_groq(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS","a"*24+","+"b"*24)
    monkeypatch.setenv("GROQ_API_KEY","c"*24)
    calls,closed=fake(monkeypatch,[error(RateLimitError),error(InternalServerError,503),
        error(APITimeoutError),error(InternalServerError,500),response()])
    async def execute():
        client=m.ModelClient();message,tokens=await client.choose([],[])
        assert tokens==42 and client.last_selection==dict(provider="groq",model="openai/gpt-oss-120b")
        assert len(client.attempts)==5
        assert all("key" not in a for a in client.attempts)
        await client.close()
    asyncio.run(execute())
    assert [model for key,model in calls]==["gemini-2.5-flash"]*2+["gemini-2.5-flash-lite"]*2+["openai/gpt-oss-120b"]
    assert len(closed)==5

def test_bounded_backoff_and_sanitized_exhaustion(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","a"*24)
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS","")
    calls,_=fake(monkeypatch,[error(RateLimitError) for _ in range(3)])
    async def execute():
        client=m.ModelClient()
        with pytest.raises(m.ModelPoolExhausted) as exc:await client.choose([],[])
        assert "secret-provider-payload" not in str(exc.value) and "a"*24 not in str(exc.value)
        await client.close()
    asyncio.run(execute())
    assert len(calls)==3
    assert [c.args[0] for c in m.asyncio.sleep.call_args_list]==[1,2]

def test_retry_after_and_retired_model_skip(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","a"*24)
    calls,_=fake(monkeypatch,[error(RateLimitError,retry=60),error(NotFoundError,404)])
    async def execute():
        client=m.ModelClient()
        with pytest.raises(m.ModelPoolExhausted):await client.choose([],[])
        await client.close()
    asyncio.run(execute())
    assert len(calls)==2  # no immediate retry of throttled or unsupported routes

def test_legacy_key_variables_deduplicate_and_keep_secrets_private(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY","a"*24)
    monkeypatch.setenv("GEMINI_API_KEY_2","a"*24)
    monkeypatch.setenv("GEMINI_API_KEY_3","b"*24)
    assert m.gemini_keys()==["a"*24,"b"*24]
    assert m.public_settings()["configured"]
    assert "a"*24 not in repr(m.routes()) and "a"*24 not in str(m.public_settings())

def test_explicit_groq_never_calls_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER","groq")
    monkeypatch.setenv("GROQ_API_KEY","c"*24)
    monkeypatch.setenv("GEMINI_API_KEY","a"*24)
    assert [(r.provider,r.model) for r in m.routes()]==[("groq","openai/gpt-oss-120b")]
