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
TARGET_URL = "https://freegen.app/"
HOST = "127.0.0.1"
PORT = 8002
MAX_PROMPT_LENGTH = 1000  # FreeGen supports longer prompts

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
                logger.info("FreeGen Browser ready.")
                await self.check_errors()
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise e

    async def stop(self):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()

    async def check_errors(self):
        """Checks for application errors and reloads if found."""
        try:
            content = await self.page.content()
            if "Application error" in content or "client-side exception" in content:
                logger.warning("Detected application error. Reloading page...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
        except:
            pass

    async def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> str:
        async with self.lock:
            # --- v1.2 Auto-Revive & Ad-Shield Logic ---
            if not self.browser or not self.browser.is_connected():
                await self.stop()
                await self.start()
            elif not self.page or self.page.is_closed():
                self.page = await self.context.new_page()
                await self.page.goto(TARGET_URL, wait_until="domcontentloaded")
            
            # Aggressive Ad Clearing
            await clear_ads(self.page, logger)
                
            try:
                if len(prompt) > MAX_PROMPT_LENGTH:
                    prompt = prompt[:MAX_PROMPT_LENGTH]
                
                await self.check_errors()
                
                logger.info(f"Generating image ({width}x{height}) for prompt: {prompt[:50]}...")
                if self.page.url != TARGET_URL:
                    await self.page.goto(TARGET_URL, wait_until="domcontentloaded")

                # --- NEW v1.2: Aspect Ratio Selection ---
                ratio = width / height
                # Closest match mapping
                if ratio > 1.5: target_ratio = "16:9"
                elif ratio > 1.2: target_ratio = "4:3"
                elif ratio > 0.8: target_ratio = "1:1"
                elif ratio > 0.6: target_ratio = "3:4"
                else: target_ratio = "9:16"
                
                logger.info(f"Mapping {width}x{height} (ratio {ratio:.2f}) to FreeGen ratio: {target_ratio}")
                try:
                    # Select the ratio from the dropdown
                    await self.page.select_option("select", target_ratio)
                except Exception as e:
                    logger.warning(f"Could not set aspect ratio: {e}")

                # 1. Capture the 'Before' state
                old_img = await self.page.query_selector('.rounded-lg img, div.relative img')
                old_src = await old_img.get_attribute("src") if old_img else ""

                prompt_selector = "textarea#prompt"
                await self.page.wait_for_selector(prompt_selector, timeout=10000)
                
                # Robust Clearing & Filling
                await self.page.click(prompt_selector)
                await self.page.keyboard.press("Control+A")
                await self.page.keyboard.press("Backspace")
                await self.page.fill(prompt_selector, prompt)
                
                generate_button = "button#generateBtn"
                await self.page.click(generate_button)
                logger.info("Generation request sent. Waiting...")
                
                # Ensure no ads appeared after interaction
                await asyncio.sleep(0.5)
                await clear_ads(self.page, logger)

                image_data_or_url = None
                for i in range(90):
                    image_data_or_url = await self.page.evaluate("""
                        (oldSrc) => {
                            const images = Array.from(document.querySelectorAll('img'));
                            const found = images.find(img => {
                                const src = img.src || '';
                                if (src.includes('assets.freegen.app')) return false;
                                if (src.includes('placeholder')) return false;
                                const isNew = (src !== oldSrc);
                                const isResult = src.startsWith('blob:') || src.startsWith('data:image') || src.includes('freegen.app/api/');
                                const isLarge = img.naturalWidth > 150 || img.width > 150;
                                return isNew && isResult && isLarge;
                            });
                            return found ? found.src : null;
                        }
                    """, old_src)
                    
                    if image_data_or_url: break
                    await asyncio.sleep(1)

                if not image_data_or_url: 
                    await self.page.screenshot(path="error_debug.png")
                    raise Exception("Generation timed out.")
                
                if image_data_or_url.startswith("blob:"):
                    return await self.page.evaluate("""
                        async (url) => {
                            const response = await fetch(url);
                            const blob = await response.blob();
                            return new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                        }
                    """, image_data_or_url)

                return image_data_or_url
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

app = FastAPI(title="FreeGen Playwright Bridge v1.2", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML

@app.get("/sdapi/v1/options")
async def sd_options(): return {"sd_model_checkpoint": "FreeGen-Turbo-v1.2"}

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
    width = data.get("width", 512)
    height = data.get("height", 512)
    
    try:
        image_data_or_url = await browser_manager.generate_image(prompt, width, height)
        
        if image_data_or_url.startswith("data:image"):
            img_base64 = image_data_or_url.split(",")[1]
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_data_or_url)
                img_base64 = base64.b64encode(resp.content).decode("utf-8")
        
        return {"images": [img_base64]}
    except Exception as e:
        logger.error(f"Error in txt2img: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting FreeGen bridge on port {PORT}...")
    uvicorn.run(app, host=HOST, port=PORT)
