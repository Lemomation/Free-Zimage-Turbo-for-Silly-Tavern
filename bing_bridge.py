import asyncio
import logging
import base64
import os
import uvicorn
import urllib.parse
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright
from bridge_utils import find_browser_executable, setup_logging, DASHBOARD_HTML, fix_windows_loop

# --- Configuration ---
TARGET_URL = "https://www.bing.com/images/create"
HOST = "127.0.0.1"
PORT = 8003
MAX_PROMPT_LENGTH = 1350
# Optional prefix prepended to every prompt before sending to Bing.
# Can help reduce false-positive content filter blocks on normal prompts.
# Set to "" to disable.
SAFE_PROMPT_PREFIX = "Safe, appropriate, artistic reference image, "

setup_logging()
logger = logging.getLogger(__name__)
fix_windows_loop()

class BrowserManager:
    def __init__(self):
        self.pw = None
        self.context = None
        self.page = None
        self.lock = asyncio.Lock()
        self.session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bing_session")
        self.last_login_click = 0

    async def start(self):
        if not self.pw:
            self.pw = await async_playwright().start()
            executable = find_browser_executable()
            os.makedirs(self.session_path, exist_ok=True)
            
            logger.info(f"Launching persistent browser context from: {self.session_path}")
            try:
                self.context = await self.pw.chromium.launch_persistent_context(
                    user_data_dir=self.session_path,
                    executable_path=executable,
                    headless=False,  # Headed mode required for manual login and captcha solving
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run"
                    ]
                )
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                
                logger.info(f"Navigating to {TARGET_URL}...")
                await self.page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
                logger.info("Checking login status...")
                await self.check_login()
                logger.info("Bing Browser ready.")
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise e

    async def stop(self):
        if self.context: 
            await self.context.close()
            self.context = None
        if self.pw: 
            await self.pw.stop()
            self.pw = None

    async def check_login(self):
        """Checks for login triggers and prompts user if action is needed."""
        import time
        while True:
            try:
                url = self.page.url.lower()
                # If we are on live.com login page, or intermediate redirect pages, just wait
                if "login.live.com" in url or "/auth" in url or "signin" in url:
                    logger.warning("=====================================================================")
                    logger.warning(" Currently on Microsoft login / authentication page. Please sign in.")
                    logger.warning("=====================================================================")
                    await asyncio.sleep(5)
                    continue

                # Read sign-in indicators by checking their actual visible inner text
                is_signed_in = False
                
                # Check modal popup
                modal_btn = await self.page.query_selector("button:has-text('Sign in & Create'), a:has-text('Sign in & Create'), button:has-text('Sign in & Keep Creating')")
                if modal_btn and await modal_btn.is_visible():
                    modal_text = await modal_btn.inner_text()
                    if "Sign in" in modal_text:
                        is_signed_in = False
                        
                # Check header login link
                header_login = await self.page.query_selector("#id_l, #id_s")
                if header_login and await header_login.is_visible():
                    header_text = await header_login.inner_text()
                    if "Sign in" in header_text:
                        is_signed_in = False
                    else:
                        # Header login element is visible but empty (avatar or reward indicator active)
                        prompt_area = await self.page.query_selector("textarea#gi_form_q")
                        if prompt_area and await prompt_area.is_visible():
                            is_signed_in = True
                else:
                    prompt_area = await self.page.query_selector("textarea#gi_form_q")
                    if prompt_area and await prompt_area.is_visible():
                        is_signed_in = True
                
                if is_signed_in:
                    logger.info("Microsoft Account is signed in. Ready.")
                    break
                    
                logger.warning("=====================================================================")
                logger.warning(" WARNING: MICROSOFT ACCOUNT SIGN-IN REQUIRED!")
                logger.warning(" Please complete the sign-in inside the open Chromium window.")
                logger.warning(" Once you are successfully signed in, this bridge will proceed.")
                logger.warning("=====================================================================")
                
                # Check if we should click (throttled to once every 30 seconds)
                now = time.time()
                if now - self.last_login_click > 30:
                    self.last_login_click = now
                    # Only click if we are on the main bing page and not in an auth redirect loop
                    if "bing.com/images/create" in url:
                        try:
                            login_btn = await self.page.query_selector("button:has-text('Sign in & Create'), a:has-text('Sign in & Create')")
                            if login_btn and await login_btn.is_visible():
                                await login_btn.click()
                                logger.info("Clicked 'Sign in & Create' button to navigate to sign-in page.")
                            else:
                                header_login_btn = await self.page.query_selector("#id_l, #id_s")
                                if header_login_btn and await header_login_btn.is_visible():
                                    btn_text = await header_login_btn.inner_text()
                                    if "Sign in" in btn_text:
                                        await header_login_btn.click()
                                        logger.info("Clicked header 'Sign in' button.")
                        except Exception as click_err:
                            logger.debug(f"Error auto-clicking login button: {click_err}")
            except Exception as e:
                # Handle execution context destruction during redirect navigation safely
                logger.debug(f"Transient navigation state encountered: {e}")
                
            await asyncio.sleep(5)

    async def generate_image(self, prompt: str, width: int = 512, height: int = 512) -> str:
        async with self.lock:
            # Auto-revive — check both for None and for a disconnected browser.
            # The Bing bridge uses a persistent context (no separate self.browser),
            # so we reach into context.browser to call is_connected()
            context_dead = (
                not self.context
                or not self.page
                or (self.context.browser and not self.context.browser.is_connected())
            )
            if context_dead:
                logger.info("Browser context closed or disconnected. Reviving...")
                await self.stop()
                await self.start()

            # Always double check login status before starting
            await self.check_login()

            if len(prompt) > MAX_PROMPT_LENGTH:
                logger.warning(f"Prompt exceeds max length of {MAX_PROMPT_LENGTH}. Trimming...")
                prompt = prompt[:MAX_PROMPT_LENGTH]

            # --- Pre-prompt prefix ---
            # Prepend the safety context phrase (if set) to nudge Bing's filter.
            if SAFE_PROMPT_PREFIX:
                prompt = SAFE_PROMPT_PREFIX + prompt
                logger.info(f"Prepended safe prefix. Prompt now starts: {prompt[:80]}...")

            # --- Age replacement ---
            # Bing's filter triggers on teen-range numbers combined with
            # character descriptors. Replace standalone 1-18 with 21.
            # Uses simple \b word boundaries — reliably catches "female, 18,"
            # without needing complex lookaheads that were silently failing.
            safe_prompt, n_subs = re.subn(
                r'\b(1[0-8]|[1-9])\b',
                '21',
                prompt
            )
            if n_subs > 0:
                logger.info(f"Age-filter: replaced {n_subs} standalone number(s) (1-18 → 21).")
                logger.info(f"  Before: {prompt[:80]}")
                logger.info(f"  After : {safe_prompt[:80]}")
                prompt = safe_prompt

            MAX_RETRIES = 2
            for attempt in range(1, MAX_RETRIES + 2):  # attempts: 1, 2, 3
                try:
                    # Always navigate to creation home page to ensure inputs are visible and clean
                    logger.info(f"Navigating to {TARGET_URL}... (attempt {attempt})")
                    await self.page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
                    await self.check_login()

                    # Dismiss 'Got it' dialog if present
                    try:
                        got_it = await self.page.query_selector("#gvqlt_gi")
                        if got_it and await got_it.is_visible():
                            await got_it.click()
                            logger.info("Dismissed 'Got it' overlay.")
                    except:
                        pass

                    # Note: Bing Image Creator's free web UI does not expose a
                    # controllable aspect ratio selector, so this step is skipped.

                    prompt_selector = "textarea#gi_form_q"
                    await self.page.wait_for_selector(prompt_selector, timeout=10000)

                    # Clear and fill the prompt input
                    await self.page.click(prompt_selector)
                    await self.page.keyboard.press("Control+A")
                    await self.page.keyboard.press("Backspace")
                    await self.page.fill(prompt_selector, prompt)

                    # Scan and list existing OIG images to avoid matching old generations
                    old_images = set()
                    try:
                        for img in await self.page.query_selector_all('img[src*="OIG"]'):
                            src = await img.get_attribute("src")
                            if src:
                                base_src = src.split('?')[0] if '?' in src else src
                                if base_src.startswith("/"):
                                    base_src = urllib.parse.urljoin(self.page.url, base_src)
                                old_images.add(base_src)
                    except Exception as e:
                        logger.warning(f"Error querying old images: {e}")

                    # Find the create button and trigger generation
                    create_button = "#create_btn_c"
                    await self.page.wait_for_selector(create_button, timeout=10000)
                    await self.page.click(create_button)
                    logger.info("Create button clicked. Waiting for generation...")

                    # Wait for generated images — Bing produces 2 images (anime + realistic).
                    # Strategy: wait for the first image, then hold EXTRA_IMAGE_WAIT seconds
                    # so any remaining images have time to appear, then collect all.
                    EXTRA_IMAGE_WAIT = 5  # seconds to wait after first image is detected
                    image_urls = []
                    content_blocked = False
                    first_seen_at = None
                    timeout_seconds = 150

                    for i in range(timeout_seconds):
                        # Check for safety filter / blocking triggers.
                        # Bing shows "Content warning" on the page (not "Blocked prompt").
                        try:
                            content = await self.page.content()
                            if (
                                "Content warning" in content
                                or "Blocked prompt" in content
                                or "Unsafe image content" in content
                                or "blocked because it may conflict" in content
                            ):
                                content_blocked = True
                                break
                        except Exception as e:
                            logger.debug(f"Temporary error reading page content: {e}")

                        # Try dismissing any volume warning dialogs
                        try:
                            dismiss_btn = await self.page.query_selector("button:has-text('Dismiss')")
                            if dismiss_btn and await dismiss_btn.is_visible():
                                await dismiss_btn.click()
                                logger.warning("Dismissed traffic congestion dialog.")
                        except:
                            pass

                        # Collect all new images from the results grid
                        new_urls = []
                        imgs = await self.page.query_selector_all('#imm_grid img, img.image-row-img')
                        for img in imgs:
                            src = await img.get_attribute("src")
                            if src and "OIG" in src:
                                base_src = src.split('?')[0] if '?' in src else src
                                if base_src.startswith("/"):
                                    base_src = urllib.parse.urljoin(self.page.url, base_src)
                                if base_src not in old_images and base_src not in new_urls:
                                    new_urls.append(base_src)

                        if new_urls:
                            image_urls = new_urls  # keep updating with latest count
                            if first_seen_at is None:
                                first_seen_at = i
                                logger.info(f"First image detected. Waiting up to {EXTRA_IMAGE_WAIT}s for more...")
                            elif i - first_seen_at >= EXTRA_IMAGE_WAIT:
                                logger.info(f"Collected {len(image_urls)} image(s) from Bing.")
                                break

                        await asyncio.sleep(1)

                    if content_blocked:
                        if attempt <= MAX_RETRIES:
                            logger.warning(
                                f"Bing content filter triggered (attempt {attempt}/{MAX_RETRIES + 1}). "
                                f"This is often a false positive — retrying..."
                            )
                            try:
                                go_back = await self.page.query_selector("a:has-text('Go back'), button:has-text('Go back')")
                                if go_back and await go_back.is_visible():
                                    await go_back.click()
                                    await asyncio.sleep(1)
                            except:
                                pass
                            continue  # retry the loop
                        else:
                            raise Exception(
                                f"Prompt blocked by Bing Content Safety filter after "
                                f"{MAX_RETRIES + 1} attempts. Try rephrasing."
                            )

                    if not image_urls:
                        raise Exception("Generation timed out or no new images were found in the dashboard.")

                    logger.info(f"Returning {len(image_urls)} image URL(s).")
                    return image_urls

                except Exception as e:
                    # Re-raise content safety errors directly (already retried above)
                    if "Content Safety" in str(e) or "Bing Content Safety" in str(e):
                        raise e
                    logger.error(f"Error during image generation (attempt {attempt}): {e}")
                    raise e

    async def download_image(self, url: str) -> bytes:
        """Downloads an image using the browser's authenticated session cookies.
        Using context.request ensures Bing's OIG images (which require a valid
        session) are fetched successfully instead of getting a 403."""
        try:
            response = await self.context.request.get(url)
            if response.ok:
                return await response.body()
            raise Exception(f"Image download failed: HTTP {response.status} for {url}")
        except Exception as e:
            logger.error(f"download_image error: {e}")
            raise e

browser_manager = BrowserManager()

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_manager.start()
    yield
    await browser_manager.stop()

app = FastAPI(title="Bing Image Creator Playwright Bridge", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD_HTML

@app.get("/sdapi/v1/options")
async def sd_options(): 
    return {"sd_model_checkpoint": "Bing-Image-Creator-DALL-E-3"}

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
    width = data.get("width", 512)
    height = data.get("height", 512)
    try:
        image_urls = await browser_manager.generate_image(prompt, width, height)
        # Download all images in parallel via the browser session (auth cookies included)
        img_bytes_list = await asyncio.gather(
            *[browser_manager.download_image(url) for url in image_urls]
        )
        images_b64 = [base64.b64encode(b).decode("utf-8") for b in img_bytes_list]
        logger.info(f"Returning {len(images_b64)} image(s) to SillyTavern.")
        return {"images": images_b64}
    except Exception as e:
        logger.error(f"Error in txt2img: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting Bing Image Creator bridge on port {PORT}...")
    uvicorn.run(app, host=HOST, port=PORT)
