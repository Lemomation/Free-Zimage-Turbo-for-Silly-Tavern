# Lemon Image API

Lemon Image API is the project-wide name for the local browser-backed image
generation service. Start it with `start_lemon_api.bat` and call
`http://127.0.0.1:8000` without an API key.

The OpenAI-compatible endpoint is:

```text
POST /v1/images/generations
```

Use `GET /v1/models` to list the available provider aliases:
`freegen`, `ezmaker`, `zimage`, `redpanda`, and `bing`.
