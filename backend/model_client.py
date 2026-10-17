"""Provider-configurable real tool calling. No scripted production fallback."""
import os
from openai import AsyncOpenAI

PROVIDERS={
 "gemini":("GEMINI_API_KEY","https://generativelanguage.googleapis.com/v1beta/openai/","gemini-3.8-flash"),
 "groq":("GROQ_API_KEY","https://api.groq.com/openai/v1","llama-3.3-70b-versatile"),
 "openai":("OPENAI_API_KEY",None,"gpt-4.1"),
}
def settings():
    provider=os.getenv("LLM_PROVIDER","gemini")
    if provider not in PROVIDERS:raise ValueError("Use gemini, groq, or openai")
    key,base,model=PROVIDERS[provider]
    return dict(provider=provider,key_name=key,key=os.getenv(key,""),base=base,model=os.getenv("LLM_MODEL") or model)

def public_settings():
    s=settings()
    return dict(provider=s["provider"],model=s["model"],configured=len(s["key"].strip())>=20,key_name=s["key_name"])

class ModelClient:
    measurement_source="LIVE_PROVIDER"
    def __init__(self):
        s=settings()
        if len(s["key"].strip())<20:raise ValueError(f"Add {s['key_name']} to local .env. No model fallback is used.")
        self.client=AsyncOpenAI(api_key=s["key"],base_url=s["base"],timeout=60,max_retries=0)
        self.model=s["model"]
    async def choose(self,messages,tools):
        result=await self.client.chat.completions.create(model=self.model,messages=messages,tools=tools,
            tool_choice="auto",parallel_tool_calls=False,max_tokens=900)
        if result.usage is None:raise ValueError("Provider omitted usage; refusing to invent benchmark tokens")
        return result.choices[0].message.model_dump(exclude_none=True),result.usage.total_tokens
    async def close(self):await self.client.close()