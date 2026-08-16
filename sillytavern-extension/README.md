# 🍋 Lemon Image Bridge — SillyTavern Extension

A native SillyTavern extension that connects directly to the **Lemon Image API** (`http://127.0.0.1:8000`). Generate AI scenes, character visuals, and story art directly from your chat with one click.

---

## Features

- **In-Chat Scene Visualizer (🎨)**: Click the palette icon on any message to generate an illustration of the scene.
- **Visual Model Switcher**: One-click selection between **FreeGen**, **EzMaker**, **ZImage**, **RedPanda**, and **Bing Image Creator**.
- **Aspect Ratio Presets**: Quick buttons for `1:1 (Square)`, `16:9 (Landscape)`, `9:16 (Story/Mobile)`, `4:3`, and `3:4`.
- **Character Context Injection**: Automatically enriches prompts with the active character's appearance and physical tags.
- **Style Presets**: One-click modifiers (Anime 2D, Photorealistic, Cinematic, Cyberpunk, Dark Fantasy, Watercolor).
- **Native Slash Commands**:
  - `/lemon <prompt>` — generates using the active provider and embeds into chat.
  - `/ezmaker <prompt>`, `/freegen <prompt>`, `/bing <prompt>`, `/zimage <prompt>`, `/redpanda <prompt>`.
  - `/lemon-model <model>` — switches the active provider.
  - `/lemon-ratio <ratio>` — changes default aspect ratio.

---

## Installation

### Method 1: Manual Copy (Recommended)
1. Copy the `sillytavern-extension/` folder from this repository.
2. Paste it into your SillyTavern directory at:
   ```text
   SillyTavern/public/scripts/extensions/third-party/lemon-image-bridge
   ```
3. Restart or reload SillyTavern.

### Method 2: Install via SillyTavern UI
1. In SillyTavern, open the top menu -> **Extensions** (stacked cubes icon).
2. Click **Install Extension** -> **Install from URL**.
3. Enter the GitHub repository URL:
   ```text
   https://github.com/Lemomation/Free-Zimage-Turbo-for-Silly-Tavern
   ```
4. Click **Install** and reload SillyTavern.

---

## Getting Started

1. Make sure your local Lemon API is running (double-click **`startlemon.bat`**).
2. In SillyTavern, open the **Extensions** menu -> **Lemon Image Bridge**.
3. The status indicator should show `🟢 ONLINE`.
4. Click the **🎨** icon on any chat message or type `/lemon <prompt>` in the chat bar!
