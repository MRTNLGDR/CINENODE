from __future__ import annotations

from typing import Any
import httpx

from .base import EngineAdapter, EngineInfo
from .common import validate_engine_url


class OllamaEngine(EngineAdapter):
    info=EngineInfo("ollama","Ollama",("chat","models"))
    def __init__(self,url: str="http://127.0.0.1:11434",allow_private: bool=False):
        self.url=validate_engine_url(url,allow_private)
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response=await client.get(f"{self.url}/api/tags"); response.raise_for_status()
            return {"ok":True,"models":response.json().get("models",[])}
        except Exception as exc:
            return {"ok":False,"error":str(exc)}
    async def chat(self,prompt: str,params: dict[str,Any])->Any:
        model=str(params.get("model",""))
        if not model: raise ValueError("Ollama model is required")
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600))) as client:
            response=await client.post(f"{self.url}/api/chat",json={"model":model,"stream":False,"messages":[{"role":"user","content":prompt}],"options":params.get("options",{})}); response.raise_for_status()
        return response.json()["message"]["content"]


class OpenAICompatibleEngine(EngineAdapter):
    info=EngineInfo("openai-compatible","OpenAI-compatible local server",("chat","models"))
    def __init__(self,url: str="http://127.0.0.1:1234/v1",api_key: str="local",allow_private: bool=False):
        self.url=validate_engine_url(url,allow_private); self.api_key=api_key
    @property
    def headers(self)->dict[str,str]: return {"Authorization":f"Bearer {self.api_key}"}
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3,headers=self.headers) as client:
                response=await client.get(f"{self.url}/models"); response.raise_for_status()
            return {"ok":True,"models":response.json().get("data",[])}
        except Exception as exc: return {"ok":False,"error":str(exc)}
    async def chat(self,prompt: str,params: dict[str,Any])->Any:
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600)),headers=self.headers) as client:
            response=await client.post(f"{self.url}/chat/completions",json={"model":params.get("model","local-model"),"messages":[{"role":"user","content":prompt}],"temperature":params.get("temperature",0.7)}); response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class ComfyUIEngine(EngineAdapter):
    info=EngineInfo("comfyui","ComfyUI",("workflow",))
    def __init__(self,url: str="http://127.0.0.1:8188",allow_private: bool=False): self.url=validate_engine_url(url,allow_private)
    async def probe(self)->dict[str,Any]:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response=await client.get(f"{self.url}/system_stats"); response.raise_for_status()
            return {"ok":True,"system":response.json()}
        except Exception as exc: return {"ok":False,"error":str(exc)}
    async def run_workflow(self,workflow: dict[str,Any],params: dict[str,Any])->Any:
        async with httpx.AsyncClient(timeout=float(params.get("timeout",600))) as client:
            response=await client.post(f"{self.url}/prompt",json={"prompt":workflow,"client_id":params.get("client_id","cinenode")}); response.raise_for_status()
        return response.json()


class MockEngine(EngineAdapter):
    info=EngineInfo("mock","Deterministic test engine",("chat","workflow"))
    async def probe(self)->dict[str,Any]: return {"ok":True,"deterministic":True}
    async def chat(self,prompt: str,params: dict[str,Any])->Any: return f"mock:{prompt}"
    async def run_workflow(self,workflow: dict[str,Any],params: dict[str,Any])->Any: return {"workflow":workflow,"params":params}
