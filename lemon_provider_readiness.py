"""Reliability fixes for first-request provider UI startup races."""

import asyncio
import logging
from types import MethodType


logger = logging.getLogger(__name__)
ERROR_MARKERS = ("application error", "client-side exception")


async def _wait_for_ui(manager, url, prompt_selector, provider, attempts=3):
    """Wait until a provider's hydrated UI is visible, reloading error pages."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            page = manager.page
            if not page or page.is_closed():
                raise RuntimeError("provider page is not open")

            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            content = (await page.content()).lower()
            if any(marker in content for marker in ERROR_MARKERS):
                logger.warning("%s returned an application-error page; reloading (%s/%s)", provider, attempt, attempts)
                await page.reload(wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)
                continue

            await page.wait_for_selector(prompt_selector, state="visible", timeout=20000)
            # Give React/Next.js a moment to attach input and click handlers.
            await asyncio.sleep(1.5)
            content = (await page.content()).lower()
            if any(marker in content for marker in ERROR_MARKERS):
                raise RuntimeError("application error appeared during page initialization")
            return
        except Exception as exc:
            last_error = exc
            logger.warning("%s UI was not ready (%s/%s): %s", provider, attempt, attempts, exc)
            if attempt < attempts:
                try:
                    await manager.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                except Exception:
                    pass
                await asyncio.sleep(3)

    raise RuntimeError(f"{provider} did not become ready after {attempts} attempts: {last_error}")


def _patch_zimage(module):
    manager = module.browser_manager
    original_start = manager.start
    original_generate = manager.generate_image

    async def start(self):
        await original_start()
        await _wait_for_ui(self, module.TARGET_URL, "textarea#z-image-prompt", "ZImage")

    async def generate(self, prompt):
        await _wait_for_ui(self, module.TARGET_URL, "textarea#z-image-prompt", "ZImage")
        try:
            return await original_generate(prompt)
        except Exception as exc:
            content = (await self.page.content()).lower() if self.page and not self.page.is_closed() else ""
            if not any(marker in content for marker in ERROR_MARKERS):
                raise
            logger.warning("ZImage failed on its application-error page; recovering and retrying once: %s", exc)
            await self.page.goto(module.TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await _wait_for_ui(self, module.TARGET_URL, "textarea#z-image-prompt", "ZImage")
            return await original_generate(prompt)

    manager.start = MethodType(start, manager)
    manager.generate_image = MethodType(generate, manager)


def _patch_redpanda(module):
    manager = module.browser_manager
    original_start = manager.start
    original_generate = manager.generate_image
    selector = "textarea[placeholder*='prompt'], textarea[placeholder*='Enter'], #input-prompt, textarea"

    async def start(self):
        await original_start()
        await _wait_for_ui(self, module.REDPANDA_URL, selector, "RedPanda")

    async def generate(self, prompt, width=512, height=512):
        await _wait_for_ui(self, module.REDPANDA_URL, selector, "RedPanda")
        try:
            return await original_generate(prompt, width, height)
        except Exception as exc:
            # The bridge reloads after any failure. Wait for that fresh page and
            # retry once; this specifically covers the first-request hydration race.
            logger.warning("RedPanda first attempt failed; waiting for its UI and retrying once: %s", exc)
            await _wait_for_ui(self, module.REDPANDA_URL, selector, "RedPanda")
            return await original_generate(prompt, width, height)

    manager.start = MethodType(start, manager)
    manager.generate_image = MethodType(generate, manager)


def install(zimage_module, redpanda_module):
    """Install the fixes once for the unified Lemon process."""
    if getattr(zimage_module.browser_manager, "_lemon_readiness_installed", False):
        return
    _patch_zimage(zimage_module)
    _patch_redpanda(redpanda_module)
    zimage_module.browser_manager._lemon_readiness_installed = True
    redpanda_module.browser_manager._lemon_readiness_installed = True
