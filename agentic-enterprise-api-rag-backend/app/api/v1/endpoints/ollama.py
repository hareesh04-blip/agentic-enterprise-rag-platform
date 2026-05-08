import os
import socket
import urllib.request

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.ollama_client import ollama_client

router = APIRouter(prefix="/ollama")


class GenerateTestRequest(BaseModel):
    prompt: str


class EmbeddingTestRequest(BaseModel):
    text: str


class OllamaHttpxDiagnosticRequest(BaseModel):
    prompt: str = "Reply with OK only."
    text: str = "hello from backend diagnostic"


@router.get("/python-network-debug")
async def python_network_debug():
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    host = "172.16.111.209"
    port = 8080

    results = {
        "base_url": base_url,
        "socket_tcp": None,
        "urllib_root": None,
        "httpx_sync_root": None,
        "httpx_async_root": None,
    }

    try:
        with socket.create_connection((host, port), timeout=10):
            results["socket_tcp"] = "success"
    except Exception as e:
        results["socket_tcp"] = repr(e)

    try:
        with urllib.request.urlopen(base_url + "/", timeout=10) as response:
            results["urllib_root"] = {
                "status": response.status,
                "body": response.read().decode("utf-8", errors="ignore")[:200],
            }
    except Exception as e:
        results["urllib_root"] = repr(e)

    try:
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.get(base_url + "/")
            results["httpx_sync_root"] = {
                "status_code": response.status_code,
                "text": response.text[:200],
            }
    except Exception as e:
        results["httpx_sync_root"] = repr(e)

    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(base_url + "/")
            results["httpx_async_root"] = {
                "status_code": response.status_code,
                "text": response.text[:200],
            }
    except Exception as e:
        results["httpx_async_root"] = repr(e)

    return results


@router.get("/debug-config")
async def ollama_debug_config() -> dict:
    return {
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "llm_model": settings.OLLAMA_LLM_MODEL,
        "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
    }


@router.get("/health")
async def ollama_health() -> dict:
    try:
        return await ollama_client.health_check()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama health check failed: {exc}") from exc


@router.post("/generate-test")
async def ollama_generate_test(payload: GenerateTestRequest) -> dict:
    try:
        response = await ollama_client.generate_test(payload.prompt)
        return {
            "model": response.get("model"),
            "response": response.get("response"),
            "done": response.get("done"),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama generate test failed: {exc}") from exc


@router.post("/embedding-test")
async def ollama_embedding_test(payload: EmbeddingTestRequest) -> dict:
    try:
        response = await ollama_client.embedding_test(payload.text)
        embedding = response.get("embedding") or []
        return {
            "model": response.get("model"),
            "embedding_dimension": len(embedding),
            "first_5_values": embedding[:5],
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama embedding test failed: {exc}") from exc


@router.post("/httpx-diagnostic")
async def ollama_httpx_diagnostic(payload: OllamaHttpxDiagnosticRequest) -> dict:
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    tags_url = f"{base_url}/api/tags"
    embedding_url = f"{base_url}/api/embeddings"
    generate_url = f"{base_url}/api/generate"

    proxy_env = {
        "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
        "NO_PROXY": os.environ.get("NO_PROXY"),
        "http_proxy": os.environ.get("http_proxy"),
        "https_proxy": os.environ.get("https_proxy"),
        "no_proxy": os.environ.get("no_proxy"),
    }

    timeout = httpx.Timeout(
        connect=settings.OLLAMA_TIMEOUT_CONNECT_SECONDS,
        read=settings.OLLAMA_TIMEOUT_READ_SECONDS,
        write=settings.OLLAMA_TIMEOUT_WRITE_SECONDS,
        pool=settings.OLLAMA_TIMEOUT_POOL_SECONDS,
    )

    async def run_attempt(method: str, url: str, request_payload: dict | None, trust_env: bool) -> dict:
        result = {
            "method": method,
            "url": url,
            "trust_env": trust_env,
            "request_payload": request_payload,
            "status_code": None,
            "response_text": None,
            "exception_class": None,
            "exception_message": None,
        }
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=trust_env) as client:
                if method == "GET":
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=request_payload)
                result["status_code"] = response.status_code
                result["response_text"] = response.text[:1000]
        except Exception as exc:
            result["exception_class"] = exc.__class__.__name__
            result["exception_message"] = str(exc)
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                result["status_code"] = exc.response.status_code
                result["response_text"] = exc.response.text[:1000]
            elif isinstance(exc, httpx.RequestError) and exc.request is not None:
                result["url"] = str(exc.request.url)
        return result

    embedding_payload = {
        "model": settings.OLLAMA_EMBEDDING_MODEL,
        "prompt": payload.text,
    }
    generation_payload = {
        "model": settings.OLLAMA_LLM_MODEL,
        "prompt": payload.prompt,
        "stream": False,
    }

    return {
        "resolved_config": {
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
            "generation_model": settings.OLLAMA_LLM_MODEL,
            "timeout_seconds": {
                "connect": settings.OLLAMA_TIMEOUT_CONNECT_SECONDS,
                "read": settings.OLLAMA_TIMEOUT_READ_SECONDS,
                "write": settings.OLLAMA_TIMEOUT_WRITE_SECONDS,
                "pool": settings.OLLAMA_TIMEOUT_POOL_SECONDS,
            },
            "retry_count": settings.OLLAMA_RETRY_COUNT,
            "retry_delay_seconds": settings.OLLAMA_RETRY_DELAY_SECONDS,
        },
        "proxy_env": proxy_env,
        "tests": {
            "trust_env_false": {
                "tags": await run_attempt("GET", tags_url, None, False),
                "embeddings": await run_attempt("POST", embedding_url, embedding_payload, False),
                "generate": await run_attempt("POST", generate_url, generation_payload, False),
            },
            "trust_env_true": {
                "tags": await run_attempt("GET", tags_url, None, True),
                "embeddings": await run_attempt("POST", embedding_url, embedding_payload, True),
                "generate": await run_attempt("POST", generate_url, generation_payload, True),
            },
        },
    }
