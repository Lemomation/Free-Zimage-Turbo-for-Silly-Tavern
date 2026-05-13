import asyncio
import logging
import base64
import os
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from bridge_utils import find_browser_executable, setup_logging, DASHBOARD_HTML

# --- Configuration ---
TARGET_URL = "https://zimage.run/"
HOST = "127.0.0.1"
PORT = 8001
MAX_PROMPT_LENGTH = 600

setup_logging()
logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()

    async def start(self):
        if not self.pw:
            self.pw = await async_playwright().start()
            executable = find_browser_executable()
            try:
                self.browser = await self.pw.chromium.launch(
                    executable_path=executable,
                    headless=False, 
                    args=["--disable-blink-features=AutomationControlled"] 
                )
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                self.page = await self.context.new_page()
                logger.info(f"Navigating to {TARGET_URL}...")
                await self.page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
                logger.info("ZImage Browser ready.")
                await self.check_errors()
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise e

    async def stop(self):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()

    async def check_errors(self):
        """Checks for Next.js application errors and reloads if found."""
        try:
            content = await self.page.content()
            if "Application error" in content or "client-side exception" in content:
                logger.warning("Detected Next.js application error. Reloading page...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
        except:
            pass

    async def generate_image(self, prompt: str) -> str:
        async with self.lock:
            # --- v1.1 Auto-Revive Logic ---
            if not self.browser or not self.browser.is_connected():
                logger.info("Browser closed or disconnected. Reviving...")
                await self.stop()
                await self.start()
            elif not self.page or self.page.is_closed():
                logger.info("Tab closed. Reopening...")
                self.page = await self.context.new_page()
                await self.page.goto(TARGET_URL, wait_until="domcontentloaded")
                
            try:
                # Truncate prompt if too long
                if len(prompt) > MAX_PROMPT_LENGTH:
                    logger.warning(f"Prompt exceeds {MAX_PROMPT_LENGTH} chars. Trimming...")
                    prompt = prompt[:MAX_PROMPT_LENGTH]
                
                # Check for errors before starting
                await self.check_errors()
                
                logger.info(f"Generating image for prompt: {prompt[:50]}...")
                if self.page.url != TARGET_URL:
                    await self.page.goto(TARGET_URL, wait_until="domcontentloaded")

                prompt_selector = "textarea#z-image-prompt"
                await self.page.wait_for_selector(prompt_selector, timeout=10000)
                
                # Robust Clearing
                await self.page.click(prompt_selector)
                await self.page.keyboard.press("Control+A")
                await self.page.keyboard.press("Backspace")
                
                # Fill and Trigger
                await self.page.fill(prompt_selector, prompt)
                await self.page.dispatch_event(prompt_selector, "input")
                await self.page.dispatch_event(prompt_selector, "change")
                
                generate_button = "button:has-text('Generate Images (Free)')"
                await self.page.click(generate_button)
                logger.info("Generation request sent. Waiting for completion...")
                
                image_url = None
                timeout_seconds = 120
                old_img = await self.page.query_selector('img[src*="/generated/"]')
                old_src = await old_img.get_attribute("src") if old_img else ""

                for i in range(timeout_seconds):
                    img_element = await self.page.query_selector('img[src*="/generated/"]')
                    if img_element:
                        src = await img_element.get_attribute("src")
                        if src and ("/generated/" in src) and (src != old_src):
                            image_url = src
                            break
                    await asyncio.sleep(1)

                if not image_url:
                    img_element = await self.page.query_selector('img[src*="files.zimage.run"]')
                    if img_element: image_url = await img_element.get_attribute("src")

                if not image_url: raise Exception("Generation timed out or image not found.")
                return image_url
            except Exception as e:
                logger.error(f"Generation error: {e}")
                try: await self.page.reload()
                except: pass
                raise e

browser_manager = BrowserManager()

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_manager.start()
    yield
    await browser_manager.stop()

app = FastAPI(title="ZImage Playwright Bridge", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML

@app.get("/sdapi/v1/options")
async def sd_options(): return {"sd_model_checkpoint": "ZImage-Run-Turbo"}

@app.get("/sdapi/v1/samplers")
@app.get("/sdapi/v1/schedulers")
@app.get("/sdapi/v1/sd-models")
@app.get("/sdapi/v1/sd-vae")
@app.get("/sdapi/v1/sd-modules")
@app.get("/sdapi/v1/upscalers")
@app.get("/sdapi/v1/latent-upscale-modes")
async def sd_dummy(): return []

@app.post("/sdapi/v1/txt2img")
async def txt2img(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    try:
        image_url = await browser_manager.generate_image(prompt)
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url)
            img_base64 = base64.b64encode(resp.content).decode("utf-8")
        return {"images": [img_base64]}
    except Exception as e:
        logger.error(f"Error in txt2img: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting ZImage bridge on port {PORT}...")
    uvicorn.run(app, host=HOST, port=PORT)
