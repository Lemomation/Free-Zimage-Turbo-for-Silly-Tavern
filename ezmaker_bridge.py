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
from bridge_utils import find_browser_executable, setup_logging, DASHBOARD_HTML, clear_ads

# --- Configuration ---
TARGET_URL = "https://ezmaker.ai/ai-image-generator/#playground"
HOST = "127.0.0.1"
PORT = 8004
MAX_PROMPT_LENGTH = 1000

setup_logging()
logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()
        self.latest_image_url = None

    async def _setup_page(self):
        self.page = await self.context.new_page()

        async def on_response(res):
            if "api-v1.ezmaker.ai/aitools/of/check-status" in res.url:
                try:
                    data = await res.json()
                    if data.get("data", {}).get("status") == 2:
                        rel_path = data["data"]["result_image"]
                        self.latest_image_url = f"https://temp.ezmaker.ai/{rel_path}"
                        logger.info(f"Captured completed task image: {self.latest_image_url}")
                except Exception:
                    pass

        self.page.on("response", on_response)
        logger.info(f"Navigating to {TARGET_URL}...")
        await self.page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_selector("textarea.el-textarea__inner", timeout=30000)
        logger.info("EzMaker Browser ready.")
        await self.check_errors()

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
                await self._setup_page()
            except Exception as e:
                logger.error(f"Failed to launch EzMaker browser: {e}")
                raise e

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()

    async def check_errors(self):
        """Checks for application errors and reloads if found."""
        try:
            content = await self.page.content()
            if "Application error" in content or "client-side exception" in content:
                logger.warning("Detected application error on EzMaker. Reloading page...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
        except Exception:
            pass

    async def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> str:
        async with self.lock:
            # Auto-Revive Logic
            if not self.browser or not self.browser.is_connected():
                logger.info("Browser closed or disconnected. Reviving EzMaker...")
                await self.stop()
                await self.start()
            elif not self.page or self.page.is_closed():
                logger.info("Page closed. Reopening EzMaker...")
                await self._setup_page()

            # Ad clearing
            await clear_ads(self.page, logger)

            try:
                if len(prompt) > MAX_PROMPT_LENGTH:
                    prompt = prompt[:MAX_PROMPT_LENGTH]

                await self.check_errors()

                logger.info(f"Generating image ({width}x{height}) for prompt: {prompt[:50]}...")
                if "ezmaker.ai" not in self.page.url:
                    await self.page.goto(TARGET_URL, wait_until="domcontentloaded")
                    await self.page.wait_for_selector("textarea.el-textarea__inner", timeout=30000)

                # Aspect Ratio Mapping: 1:1, 16:9, 9:16, 4:3, 3:4
                ratio = width / height
                if ratio > 1.5:
                    target_ratio = "16:9"
                elif ratio > 1.2:
                    target_ratio = "4:3"
                elif ratio > 0.8:
                    target_ratio = "1:1"
                elif ratio > 0.6:
                    target_ratio = "3:4"
                else:
                    target_ratio = "9:16"

                logger.info(f"Mapping {width}x{height} (ratio {ratio:.2f}) to EzMaker ratio: {target_ratio}")
                try:
                    ratio_btn = await self.page.query_selector(f"button.ratio-item:has-text('{target_ratio}')")
                    if ratio_btn:
                        await ratio_btn.click()
                except Exception as e:
                    logger.warning(f"Could not select aspect ratio '{target_ratio}': {e}")

                # Capture previous image url to detect new generation completion
                old_src = await self.page.evaluate("""() => {
                    const btn = document.querySelector('button.generate-btn');
                    const btnResult = btn ? btn.getAttribute('result-image') : null;
                    if (btnResult) return btnResult;
                    const img = document.querySelector('.task-image img, .tasks-list img');
                    return img ? img.src : null;
                }""")
                if old_src == self.latest_image_url:
                    self.latest_image_url = None

                prompt_selector = "textarea.el-textarea__inner"
                await self.page.wait_for_selector(prompt_selector, timeout=15000)
                await self.page.click(prompt_selector)
                await self.page.keyboard.press("Control+A")
                await self.page.keyboard.press("Backspace")
                await self.page.fill(prompt_selector, prompt)

                generate_btn = await self.page.wait_for_selector("button.generate-btn", timeout=15000)
                await generate_btn.click()
                logger.info("Generation request sent to EzMaker. Waiting for completion...")

                # Clear any popups/ads after clicking generate
                await asyncio.sleep(0.5)
                await clear_ads(self.page, logger)

                image_url = None
                timeout_seconds = 180  # allow up to 3 minutes for queue processing
                for i in range(timeout_seconds):
                    if self.latest_image_url and self.latest_image_url != old_src:
                        image_url = self.latest_image_url
                        break

                    # Fallback to DOM detection
                    dom_result = await self.page.evaluate("""(oldSrc) => {
                        const btn = document.querySelector('button.generate-btn');
                        const btnImg = btn ? btn.getAttribute('result-image') : null;
                        if (btnImg && btnImg !== oldSrc && btnImg.includes('temp.ezmaker.ai')) {
                            return btnImg;
                        }
                        const completedTask = document.querySelector('.task-item:has(.completed) .task-image img, .tasks-list .task-item .task-image img');
                        if (completedTask && completedTask.src && completedTask.src !== oldSrc && completedTask.src.includes('temp.ezmaker.ai')) {
                            return completedTask.src;
                        }
                        return null;
                    }""", old_src)

                    if dom_result:
                        image_url = dom_result
                        break

                    if i % 10 == 0 and i > 0:
                        logger.info(f"Still waiting for EzMaker generation ({i}/{timeout_seconds}s)...")

                    await asyncio.sleep(1)

                if not image_url:
                    await self.page.screenshot(path="error_debug.png")
                    raise Exception("EzMaker generation timed out or failed to produce an image.")

                logger.info(f"EzMaker generation complete: {image_url}")
                return image_url

            except Exception as e:
                logger.error(f"EzMaker generation error: {e}")
                try:
                    await self.page.reload()
                except Exception:
                    pass
                raise e

browser_manager = BrowserManager()

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_manager.start()
    yield
    await browser_manager.stop()

app = FastAPI(title="EzMaker AI Playwright Bridge", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML

@app.get("/sdapi/v1/options")
async def sd_options():
    return {"sd_model_checkpoint": "EzMaker-AI-Turbo"}

@app.get("/sdapi/v1/samplers")
@app.get("/sdapi/v1/schedulers")
@app.get("/sdapi/v1/sd-models")
@app.get("/sdapi/v1/sd-vae")
@app.get("/sdapi/v1/sd-modules")
@app.get("/sdapi/v1/upscalers")
@app.get("/sdapi/v1/latent-upscale-modes")
async def sd_dummy():
    return []

@app.post("/sdapi/v1/txt2img")
async def txt2img(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    width = int(data.get("width", 512))
    height = int(data.get("height", 512))

    try:
        image_data_or_url = await browser_manager.generate_image(prompt, width, height)

        if image_data_or_url.startswith("data:image"):
            img_base64 = image_data_or_url.split(",", 1)[1]
        else:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(image_data_or_url)
                resp.raise_for_status()
                img_base64 = base64.b64encode(resp.content).decode("utf-8")

        return {"images": [img_base64]}
    except Exception as e:
        logger.error(f"Error in txt2img: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting EzMaker bridge on port {PORT}...")
    uvicorn.run(app, host=HOST, port=PORT)
