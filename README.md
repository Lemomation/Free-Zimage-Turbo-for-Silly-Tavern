# AI Image Bridge for SillyTavern

This project provides a Stable Diffusion-compatible API bridge for free online image generators, allowing you to use them directly within SillyTavern.

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
