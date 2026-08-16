# Unified API

Run `start_api.bat` and send requests to `http://127.0.0.1:8000`.
No API key is required. The first request for a provider opens its browser
session; Bing requires Microsoft sign-in.

## OpenAI-compatible request

```powershell
$body = @{ model = "zimage"; prompt = "a red panda in a spacesuit"; size = "1024x1024"; n = 1 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/v1/images/generations -Method Post -ContentType "application/json" -Body $body
```

Supported model aliases are `freegen`, `ezmaker`, `zimage`, `redpanda`, and `bing`.
The response contains base64-encoded images in `data[].b64_json`.

`GET /v1/models` lists the available aliases. `DEFAULT_MODEL` can be set in
the environment to select the default when `model` is omitted.

## Convenience request

`POST /generate` accepts `prompt`, `model`, `width`, `height`, and `n`, and
returns base64 strings in an `images` array.
