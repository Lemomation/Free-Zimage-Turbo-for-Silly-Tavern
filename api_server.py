"""Unified HTTP API for the browser-backed image providers.

This service keeps the existing provider bridges available while exposing a
provider-neutral API that can be used by any client, not just SillyTavern.
"""

import asyncio
import base64
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from bridge_utils import DASHBOARD_HTML, setup_logging
import bing_bridge
import ezmaker_bridge
import freegen_bridge
import zimage_bridge
import main as redpanda_bridge


HOST = os.getenv("API_HOST", "127.0.0.1")
PORT = int(os.getenv("API_PORT", "8000"))
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "freegen").lower()
MAX_N = 8

setup_logging()
logger = logging.getLogger(__name__)


class ProviderAdapter:
    """Normalizes the slightly different provider bridge APIs."""

    def __init__(self, alias: str, label: str, module: Any):
        self.alias = alias
        self.label = label
        self.module = module
        self.manager = module.browser_manager
        self.start_lock = asyncio.Lock()
        self.started = False

    async def ensure_started(self) -> None:
        async with self.start_lock:
            # Existing managers are deliberately lazy: importing a bridge does
            # not open a browser until the first request for that provider.
            if not self.started or not getattr(self.manager, "pw", None):
                await self.manager.start()
                self.started = True

    async def stop(self) -> None:
        if self.started:
            try:
                await self.manager.stop()
            finally:
                self.started = False

    async def _download(self, value: str) -> bytes:
        if value.startswith("data:image"):
            encoded = value.split(",", 1)[1]
            return base64.b64decode(encoded)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(value)
            response.raise_for_status()
            return response.content

    async def generate_once(self, prompt: str, width: int, height: int) -> list[bytes]:
        await self.ensure_started()
        if self.alias == "bing":
            urls = await self.manager.generate_image(prompt, width, height)
            return await asyncio.gather(*(self.manager.download_image(url) for url in urls))

        # ZImage's website currently has no dimension arguments; its manager
        # intentionally accepts only the prompt.
        if self.alias == "zimage":
            result = await self.manager.generate_image(prompt)
        else:
            result = await self.manager.generate_image(prompt, width, height)
        return [await self._download(result)]


PROVIDERS = {
    "freegen": ProviderAdapter("freegen", "FreeGen.app", freegen_bridge),
    "ezmaker": ProviderAdapter("ezmaker", "EzMaker AI", ezmaker_bridge),
    "zimage": ProviderAdapter("zimage", "ZImage.run", zimage_bridge),
    "redpanda": ProviderAdapter("redpanda", "RedPanda AI", redpanda_bridge),
    "bing": ProviderAdapter("bing", "Bing Image Creator / DALL-E 3", bing_bridge),
}


def parse_size(value: Any) -> tuple[int, int]:
    if value is None:
        return 512, 512
    if not isinstance(value, str) or "x" not in value.lower():
        raise ValueError("size must be formatted as WIDTHxHEIGHT, for example 1024x1024")
    left, right = value.lower().split("x", 1)
    try:
        width, height = int(left), int(right)
    except ValueError as exc:
        raise ValueError("size must contain integer dimensions") from exc
    if not (64 <= width <= 2048 and 64 <= height <= 2048):
        raise ValueError("width and height must be between 64 and 2048")
    return width, height


def get_model(value: Any) -> str:
    model = str(value or DEFAULT_MODEL).strip().lower()
    if model not in PROVIDERS:
        raise ValueError(f"Unknown model '{model}'. Available models: {', '.join(PROVIDERS)}")
    return model


async def generate_images(model: str, prompt: str, width: int, height: int, n: int) -> list[bytes]:
    provider = PROVIDERS[model]
    images: list[bytes] = []
    # n represents generation requests. Providers that naturally return a set
    # (currently Bing) contribute that set without being needlessly repeated.
    for _ in range(n):
        images.extend(await provider.generate_once(prompt, width, height))
    return images


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await asyncio.gather(*(provider.stop() for provider in PROVIDERS.values()))


app = FastAPI(title="Unified Local Image Generation API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML


@app.get("/health")
async def health():
    return {"status": "ok", "default_model": DEFAULT_MODEL, "models": list(PROVIDERS)}


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {"id": alias, "object": "model", "owned_by": "local-browser-bridge", "provider": provider.label}
            for alias, provider in PROVIDERS.items()
        ],
    }


@app.post("/v1/images/generations")
async def openai_images(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required and must be a non-empty string")
    try:
        model = get_model(data.get("model"))
        width, height = parse_size(data.get("size"))
        n = int(data.get("n", 1))
        if not 1 <= n <= MAX_N:
            raise ValueError(f"n must be between 1 and {MAX_N}")
        images = await generate_images(model, prompt, width, height, n)
        return {"created": int(time.time()), "data": [{"b64_json": base64.b64encode(image).decode()} for image in images]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Image generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/generate")
async def convenience_generate(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=400, detail="prompt is required and must be a non-empty string")
    try:
        model = get_model(data.get("model"))
        width = int(data.get("width", 512))
        height = int(data.get("height", 512))
        parse_size(f"{width}x{height}")
        n = int(data.get("n", 1))
        if not 1 <= n <= MAX_N:
            raise ValueError(f"n must be between 1 and {MAX_N}")
        images = await generate_images(model, prompt, width, height, n)
        return {"model": model, "images": [base64.b64encode(image).decode() for image in images]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Image generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# Preserve the Stable Diffusion WebUI contract for SillyTavern clients.
@app.post("/sdapi/v1/txt2img")
async def sd_txt2img(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    try:
        model = get_model(data.get("model", DEFAULT_MODEL))
        width, height = parse_size(f"{int(data.get('width', 512))}x{int(data.get('height', 512))}")
        images = await generate_images(model, prompt, width, height, 1)
        return {"images": [base64.b64encode(image).decode() for image in images]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("SillyTavern generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


if __name__ == "__main__":
    logger.info("Starting unified image API on %s:%s", HOST, PORT)
    uvicorn.run(app, host=HOST, port=PORT)
