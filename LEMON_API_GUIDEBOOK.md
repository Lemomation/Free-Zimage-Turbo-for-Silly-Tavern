# Lemon Image API Guidebook

Lemon Image API is a local, browser-backed image-generation service. It gives
any application a simple HTTP API for FreeGen, EzMaker, ZImage, RedPanda, and Bing Image
Creator. It runs on your computer, does not require an API key, and returns
generated images as base64-encoded data.

## 1. Start Lemon

Double-click:

```text
startlemon.bat
```

The launcher creates the virtual environment if needed, starts the API, waits
for it to become healthy, and opens the dashboard. The service URL is:

```text
http://127.0.0.1:8000
```

Keep the Lemon server process running while making requests. The first request
for a provider opens a visible browser window and loads that provider's site.
FreeGen may display its normal ads; Bing requires Microsoft sign-in.

## 2. Check the service

Health check:

```http
GET http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok",
  "default_model": "freegen",
  "models": ["freegen", "ezmaker", "zimage", "redpanda", "bing"]
}
```

List models:

```http
GET http://127.0.0.1:8000/v1/models
```

Available model aliases:

| Alias | Provider | Notes |
|---|---|---|
| `freegen` | FreeGen.app | Free provider; advertising must remain available |
| `ezmaker` | EzMaker AI | Free, unlimited & no sign-up; supports 5 aspect ratios |
| `zimage` | ZImage.run | May show a browser application-error page while the site recovers |
| `redpanda` | RedPanda AI | Supports automatic aspect-ratio mapping |
| `bing` | Bing Image Creator | Requires Microsoft login in the visible browser |

## 3. OpenAI-compatible image request

Endpoint:

```http
POST http://127.0.0.1:8000/v1/images/generations
Content-Type: application/json
```

Request body:

```json
{
  "model": "freegen",
  "prompt": "a red panda exploring a glowing jungle at night",
  "size": "1024x1024",
  "n": 1
}
```

Fields:

- `prompt` — required text description.
- `model` — optional provider alias; defaults to `freegen`.
- `size` — optional `WIDTHxHEIGHT`; defaults to `512x512`. Valid dimensions are 64–2048 pixels.
- `n` — optional number of generation requests from 1 to 8; defaults to `1`.

Successful response:

```json
{
  "created": 1786013510,
  "data": [
    { "b64_json": "iVBORw0KGgoAAA..." }
  ]
}
```

The `b64_json` value is base64 image data. Decode it and save it as a PNG or
the image format detected from its bytes.

## 4. Convenience endpoint

For clients that prefer explicit dimensions, use:

```http
POST http://127.0.0.1:8000/generate
Content-Type: application/json
```

```json
{
  "model": "redpanda",
  "prompt": "a quiet mountain village in watercolor",
  "width": 768,
  "height": 1024,
  "n": 1
}
```

Response:

```json
{
  "model": "redpanda",
  "images": ["iVBORw0KGgoAAA..."]
}
```

## 5. Request examples

### PowerShell

```powershell
$body = @{
  model = "zimage"
  prompt = "a cinematic lighthouse on an alien ocean"
  size = "1024x1024"
  n = 1
} | ConvertTo-Json

$response = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/images/generations" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body

[IO.File]::WriteAllBytes(
  "result.png",
  [Convert]::FromBase64String($response.data[0].b64_json)
)
```

### Python

```python
import base64
import requests

response = requests.post(
    "http://127.0.0.1:8000/v1/images/generations",
    json={
        "model": "freegen",
        "prompt": "a tiny lemon-shaped spaceship",
        "size": "768x768",
        "n": 1,
    },
    timeout=180,
)
response.raise_for_status()

image = base64.b64decode(response.json()["data"][0]["b64_json"])
with open("result.png", "wb") as file:
    file.write(image)
```

### JavaScript / Node.js

```javascript
const response = await fetch("http://127.0.0.1:8000/v1/images/generations", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "bing",
    prompt: "a professional product photo of a yellow lemon",
    size: "1024x1024",
    n: 1
  })
});

if (!response.ok) throw new Error(await response.text());
const result = await response.json();
const imageBase64 = result.data[0].b64_json;
```

## 6. Errors and troubleshooting

Common HTTP responses:

- `400 Bad Request` — missing prompt, unknown model, malformed `size`, or invalid `n`.
- `502 Bad Gateway` — the provider website timed out, rejected the prompt, needs login, or failed to return an image.
- `500`/browser errors — check the Lemon server window and the provider browser window.

If the browser does not appear when the first generation starts:

1. Stop any old Lemon or provider processes.
2. Double-click `startlemon.bat` from the project folder.
3. Keep the minimized Lemon server process running.
4. Try the request again.

Provider generation is serialized per browser session, so the first request can
take 5–20 seconds to load a provider and image generation can take up to about
120 seconds. Requests to different providers can run independently.

## 7. SillyTavern compatibility

The unified server preserves the Stable Diffusion-style endpoint:

```http
POST http://127.0.0.1:8000/sdapi/v1/txt2img
```

Set SillyTavern's Stable Diffusion API URL to `http://127.0.0.1:8000`. Existing
standalone provider scripts and their old ports remain available, but they are
not needed when using Lemon Image API.

## 8. Configuration

Optional environment variables:

```text
API_HOST=127.0.0.1
API_PORT=8000
DEFAULT_MODEL=freegen
```

The service intentionally binds to localhost and has no API-key requirement.
Do not expose it to a network without adding authentication and access control.
