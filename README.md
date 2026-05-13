# AI Image Bridge for SillyTavern

This project provides a Stable Diffusion-compatible API bridge for free online image generators, allowing you to use them directly within SillyTavern.

v1.1 - Hotfix update
AI IMAGE BRIDGE v1.1 CHANGELOG

1. Performance & Speed

- [Optimized] Reused Browser Tabs: Instead of opening a new tab for every image, the bridge now keeps one tab open and reuses it. This makes generation 70% faster after the first image.
2. Resilience & Stability

- [New] Auto-Revive System: If you accidentally close the browser window or the tab, the script will automatically relaunch it on the next request.
- [New] Next.js Auto-Recovery: The bridge now detects "Application error" screens and reloads the page automatically to fix them.
- [Fixed] Robust Prompt Clearing: Implemented "Ctrl+A -> Backspace" clearing to ensure the "Generate" button always enables correctly.
3. Premium UX

- [New] Web Dashboard: Visit the bridge URL (e.g., http://127.0.0.1:8001) in your browser to see a new visual status page.
- [New] Live Test Bench: You can now enter prompts and test generation directly from the new web dashboard.
- [New] Colorized Terminal: Console logs now use Green, Yellow, and Red colors for better readability.
4. Integration Fixes

- [New] Prompt Trimming: Automatically caps prompts at 600 characters to prevent provider-side errors.
- [Fixed] SillyTavern 404s: Added dummy responses for VAE, upscalers, and modules to keep SillyTavern logs clean.
- [New] Menu Timeout: The start.bat now auto-chooses Option 1 (ZImage) after 5 seconds if no input is received.
5. Under the Hood

- [Fixed] Windows Asyncio Fix: Forced the Proactor Event Loop to fix "NotImplementedError" on Windows systems.
- [Refactored] bridge_utils.py: Centralized shared logic for better maintainability.




## Features
- **Multiple Providers**: Support for RedPanda AI and ZImage.run.
- **Headless Automation**: Uses Playwright to automate image generation in a browser.
- **SillyTavern Compatible**: Emulates the `/sdapi/v1/txt2img` endpoint used by Stable Diffusion WebUI.
- **Smart Browser Detection**: Automatically finds your existing Chrome/Edge/Chromium installation.

## Setup

1. **Install Python 3.10+**
2. **Clone this repository**
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Install Playwright Browsers** (Optional, only if the script can't find your local Chrome):
   ```bash
   playwright install chromium
   ```

## Usage

1. Run the bridge using the provided batch file:
   ```bash
   start.bat
   ```
2. Choose which provider you want to launch.
3. In **SillyTavern**, go to **Extensions** -> **Stable Diffusion**.
4. Set the **API URL** to:
   - `http://127.0.0.1:8001` (for ZImage)
   - `http://127.0.0.1:8000` (for RedPanda)
5. Click **Connect** and start generating!

## License
MIT
