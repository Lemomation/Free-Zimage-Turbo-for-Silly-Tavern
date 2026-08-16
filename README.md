# AI Image Bridge for SillyTavern

This project provides a Stable Diffusion-compatible API bridge for free online image generators, allowing you to use them directly within SillyTavern.

<p align="center">
  <img src="https://files.catbox.moe/iqy01o.png" width="48%" alt="In-chat UI 1" />
  <img src="https://files.catbox.moe/m9cn6k.png" width="48%" alt="In-chat UI 2" />
</p>

## Changelog

### v1.3 — EzMaker AI & Unified Lemon API Update

1. **New Provider: EzMaker AI**
   - [New] Added **EzMaker AI** bridge on Port `8004` (Fast, unlimited, no sign-up required).
   - [New] Automatic aspect ratio support for 5 sizes: `1:1`, `16:9`, `9:16`, `4:3`, and `3:4`.
2. **Unified Lemon API & OpenAI Compatibility**
   - [New] Unified API server on Port `8000` supporting all 5 providers through a single endpoint.
   - [New] Standard **OpenAI-compatible endpoints** (`POST /v1/images/generations` and `GET /v1/models`) for direct integration with OpenAI client SDKs and third-party tools.
   - [New] One-click launcher **`startlemon.bat`** that auto-starts the background server and opens the browser test dashboard.
   - [New] Single-port Web UI dashboard with model switcher dropdown.

### v1.2 — Launcher Fix

1. **Critical Fix: Python Detection**
   - [Fixed] `start.bat` no longer picks up unrelated virtual environments (e.g. `hermes-agent\venv`) as the system Python. Now uses the Windows Python Launcher (`py -3`) first, which always finds the correct system Python.
   - [Fixed] Resolved a CMD parser crash caused by nested `if` blocks and inline Python commands containing parentheses. Rewrote the entire launcher to use a flat `goto`-based flow.
   - [Fixed] The `.venv` is now correctly created from the real system Python, ensuring all dependencies install into the right environment.

### v1.1 — Hotfix Update

1. **Performance & Speed**
   - [Optimized] Reused Browser Tabs: Instead of opening a new tab for every image, the bridge now keeps one tab open and reuses it. This makes generation 70% faster after the first image.
2. **Resilience & Stability**
   - [New] Auto-Revive System: If you accidentally close the browser window or the tab, the script will automatically relaunch it on the next request.
   - [New] Next.js Auto-Recovery: The bridge now detects "Application error" screens and reloads the page automatically to fix them.
   - [Fixed] Robust Prompt Clearing: Implemented "Ctrl+A -> Backspace" clearing to ensure the "Generate" button always enables correctly.
3. **Premium UX**
   - [New] Web Dashboard: Visit the bridge URL (e.g., http://127.0.0.1:8001) in your browser to see a new visual status page.
   - [New] Live Test Bench: You can now enter prompts and test generation directly from the new web dashboard.
   - [New] Colorized Terminal: Console logs now use Green, Yellow, and Red colors for better readability.
4. **Integration Fixes**
   - [New] Prompt Trimming: Automatically caps prompts at 600 characters to prevent provider-side errors.
   - [Fixed] SillyTavern 404s: Added dummy responses for VAE, upscalers, and modules to keep SillyTavern logs clean.
   - [New] Menu Timeout: The start.bat now auto-chooses Option 1 (ZImage) after 5 seconds if no input is received.
5. **Under the Hood**
   - [Fixed] Windows Asyncio Fix: Forced the Proactor Event Loop to fix "NotImplementedError" on Windows systems.
   - [Refactored] bridge_utils.py: Centralized shared logic for better maintainability.

## Features
- **Multiple Providers**: Support for **FreeGen.app**, **EzMaker AI**, **ZImage.run**, **RedPanda AI**, and **Bing Image Creator** (DALL-E 3).
- **Dedicated SillyTavern Extension**: Included in [`sillytavern-extension/`](sillytavern-extension/) with in-chat 🎨 scene visualizer, one-click model switcher, slash commands, and style presets.
- **Headless & Headed Automation**: Uses Playwright to automate image generation in a browser. (Bing bridge runs headed to allow you to log in to your Microsoft Account).
- **OpenAI & SillyTavern Compatible**: Exposes `/v1/images/generations` and emulates the `/sdapi/v1/txt2img` endpoint used by Stable Diffusion WebUI.
- **Smart Browser Detection**: Automatically finds your existing Chrome/Edge/Chromium installation.
- **Aggressive Ad-Shielding**: Automatically blocks ads, popups, and Google Vignette overlays to ensure smooth, uninterrupted generation.
- **Aspect Ratio Mapping**: Automatically detects width and height requests and maps them to the provider's available aspect ratios.

## Dedicated SillyTavern Extension

To use the dedicated in-chat extension:
1. Copy the `sillytavern-extension` folder into your SillyTavern directory at:
   `SillyTavern/public/scripts/extensions/third-party/lemon-image-bridge`
2. Start the server with `startlemon.bat`.
3. In SillyTavern, open Extensions -> **Lemon Image Bridge** to access live provider switching, style presets, and click the 🎨 icon on any message to generate visuals!

## Setup & Usage

1. **Install Python 3.10+** (make sure to check the box **"Add Python to PATH"** during installation).
2. **Run the launcher**:
   - Double-click **`start.bat`** (or run it from your terminal).

![Terminal Screenshot](https://files.catbox.moe/oqq00o.png)

The launcher will automatically:
- Create a local Python virtual environment (`.venv`) to keep your system clean.
- Install all required dependencies (`FastAPI`, `Playwright`, etc.) within that environment.
- Scan for an existing Google Chrome or Microsoft Edge installation (and automatically download Chromium as a fallback only if neither is found).
- Open the interactive menu to select your provider.

## Usage Details
2. Choose the provider you want to run:
   - **[1] FreeGen Bridge** (Port 8002) - Fastest & unlimited.
   - **[2] EzMaker Bridge** (Port 8004) - Unlimited & no sign-up required.
   - **[3] ZImage Bridge** (Port 8001) - Standard speed.
   - **[4] RedPanda Bridge** (Port 8000) - Standard speed.
   - **[5] Bing Bridge** (Port 8003) - DALL-E 3. (Requires logging into your Microsoft Account in the browser window that opens. Session cookies are saved locally in the ignored `.bing_session` folder so you stay signed in).
3. In **SillyTavern**, go to **Extensions** -> **Stable Diffusion**.
4. Set the **API URL** depending on the provider you launched:
   - `http://127.0.0.1:8002` (for FreeGen)
   - `http://127.0.0.1:8004` (for EzMaker)
   - `http://127.0.0.1:8001` (for ZImage)
   - `http://127.0.0.1:8000` (for RedPanda / Unified API)
   - `http://127.0.0.1:8003` (for Bing)

![Extension settings](https://files.catbox.moe/8ajbpq.png)

5. Click **Connect** and start generating!

## Web Dashboard

Each bridge includes a built-in web dashboard and live test bench. Once you launch a provider, you can open its localhost API URL in your web browser (e.g., `http://127.0.0.1:8002` for FreeGen, `http://127.0.0.1:8004` for EzMaker, `http://127.0.0.1:8001` for ZImage, `http://127.0.0.1:8000` for RedPanda/Lemon, or `http://127.0.0.1:8003` for Bing) to check connection status, monitor console logs, or test image generation directly.

![Web Dashboard Screenshot](https://files.catbox.moe/s4hidm.png)

## License
MIT
