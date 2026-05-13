import os
import shutil
import logging
import sys
import asyncio
from pathlib import Path

# --- Terminal Colors ---
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def find_browser_executable():
    """Scans the system for existing Chrome or Chromium installations."""
    env_path = os.getenv("CHROME_PATH")
    if env_path and os.path.exists(env_path): return env_path
    
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        pw_dir = Path(local_app_data) / "ms-playwright"
        if pw_dir.exists():
            matches = list(pw_dir.glob("**/chrome.exe")) + list(pw_dir.glob("**/chromium.exe"))
            if matches: return str(matches[0])
    
    std_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for p in std_paths:
        if os.path.exists(p): return p
            
    for cmd in ["chrome", "chromium"]:
        path = shutil.which(cmd)
        if path: return path
    return None

def setup_logging():
    class CustomFormatter(logging.Formatter):
        format_str = "%(asctime)s - %(levelname)s - %(message)s"
        FORMATS = {
            logging.DEBUG: Colors.CYAN + format_str + Colors.RESET,
            logging.INFO: Colors.GREEN + format_str + Colors.RESET,
            logging.WARNING: Colors.YELLOW + format_str + Colors.RESET,
            logging.ERROR: Colors.RED + format_str + Colors.RESET,
            logging.CRITICAL: Colors.BOLD + Colors.RED + format_str + Colors.RESET
        }
        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
            return formatter.format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)

def fix_windows_loop():
    if sys.platform == 'win32':
        try:
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except: pass

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Image Bridge Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --secondary: #a855f7;
            --bg: #0f172a;
            --card: rgba(30, 41, 59, 0.7);
            --text: #f8fafc;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at top left, #1e1b4b, #0f172a);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-x: hidden;
        }
        .container {
            width: 100%;
            max-width: 800px;
            background: var(--card);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.8s ease-out;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        
        header { text-align: center; margin-bottom: 40px; }
        .badge {
            display: inline-block;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            padding: 6px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }
        h1 { font-size: 32px; font-weight: 700; background: linear-gradient(90deg, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .status-card {
            display: flex;
            align-items: center;
            gap: 12px;
            background: rgba(0, 0, 0, 0.2);
            padding: 12px 20px;
            border-radius: 16px;
            margin-bottom: 30px;
            border-left: 4px solid #22c55e;
        }
        .pulse {
            width: 10px; height: 10px; background: #22c55e; border-radius: 50%;
            box-shadow: 0 0 0 rgba(34, 197, 94, 0.4);
            animation: pulse 2s infinite;
        }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); } 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }

        .test-bench { display: flex; flex-direction: column; gap: 20px; }
        textarea {
            width: 100%;
            height: 120px;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 20px;
            color: #fff;
            font-family: inherit;
            font-size: 16px;
            resize: none;
            transition: border-color 0.3s;
        }
        textarea:focus { outline: none; border-color: var(--primary); }
        
        button {
            width: 100%;
            padding: 16px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 16px;
            color: #fff;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.5); }
        button:active { transform: translateY(0); }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

        .result-area {
            margin-top: 40px;
            text-align: center;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px dashed rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.1);
        }
        .result-area img { max-width: 100%; height: auto; display: block; border-radius: 12px; }
        .placeholder-text { color: #64748b; font-style: italic; }

        .loader {
            width: 48px; height: 48px; border: 5px solid #FFF; border-bottom-color: var(--primary);
            border-radius: 50%; display: inline-block; box-sizing: border-box;
            animation: rotation 1s linear infinite;
        }
        @keyframes rotation { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        footer { margin-top: 30px; text-align: center; font-size: 14px; color: #64748b; }
        footer a { color: var(--primary); text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="badge">V1.1 Hotfix</div>
            <h1 id="title">AI Image Bridge</h1>
        </header>

        <div class="status-card">
            <div class="pulse"></div>
            <div>
                <strong>Bridge Status:</strong> <span id="status">ACTIVE</span><br>
                <small id="provider-info" style="color: #94a3b8">Ready for SillyTavern connections</small>
            </div>
        </div>

        <div class="test-bench">
            <textarea id="prompt" placeholder="Enter a prompt to test the generator..."></textarea>
            <button id="gen-btn">
                <span id="btn-text">✨ Generate Image</span>
                <div id="btn-loader" class="loader" style="display: none; width: 20px; height: 20px; border-width: 2px;"></div>
            </button>
        </div>

        <div id="result-container" class="result-area">
            <span class="placeholder-text">Generated image will appear here...</span>
        </div>

        <footer>
            Built for SillyTavern | <a href="https://github.com/Lemomation/Free-Zimage-Turbo-for-Silly-Tavern" target="_blank">Documentation</a>
        </footer>
    </div>

    <script>
        const genBtn = document.getElementById('gen-btn');
        const btnText = document.getElementById('btn-text');
        const btnLoader = document.getElementById('btn-loader');
        const promptInput = document.getElementById('prompt');
        const resultContainer = document.getElementById('result-container');

        // Set Provider Name
        const port = window.location.port;
        document.getElementById('title').innerText = port === '8001' ? 'ZImage Bridge' : 'RedPanda Bridge';
        document.getElementById('provider-info').innerText = port === '8001' ? 'Provider: ZImage.run' : 'Provider: RedPanda AI';

        genBtn.onclick = async () => {
            const prompt = promptInput.value.trim();
            if (!prompt) return alert('Please enter a prompt!');

            genBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'inline-block';
            resultContainer.innerHTML = '<div class="loader"></div>';

            try {
                const response = await fetch('/sdapi/v1/txt2img', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt })
                });
                const data = await response.json();
                
                if (data.images && data.images.length > 0) {
                    resultContainer.innerHTML = `<img src="data:image/png;base64,${data.images[0]}" alt="Result">`;
                } else {
                    throw new Error('No image returned');
                }
            } catch (err) {
                resultContainer.innerHTML = `<span style="color: #ef4444">Error: ${err.message}</span>`;
            } finally {
                genBtn.disabled = false;
                btnText.style.display = 'inline-block';
                btnLoader.style.display = 'none';
            }
        };
    </script>
</body>
</html>
"""
