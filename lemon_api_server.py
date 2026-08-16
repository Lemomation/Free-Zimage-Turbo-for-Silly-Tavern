"""Branded entry point for Lemon Image API.

The implementation lives in api_server.py; this wrapper keeps the original
entry point available while presenting the public Lemon Image API branding.
"""

import uvicorn

import api_server as _api


# Reuse the configured FastAPI application and all provider routing.
app = _api.app
app.title = "Lemon Image API"

# The shared dashboard is provider-aware, so only the generic branding needs
# replacing here. The route function in api_server resolves this module global
# at request time.
_api.DASHBOARD_HTML = (
    _api.DASHBOARD_HTML
    .replace("AI Image Bridge Dashboard", "Lemon Image API Dashboard")
    .replace("AI Image Bridge", "Lemon Image API")
    .replace("Built for SillyTavern", "Local image generation API")
)


if __name__ == "__main__":
    _api.logger.info("Starting Lemon Image API on %s:%s", _api.HOST, _api.PORT)
    uvicorn.run(app, host=_api.HOST, port=_api.PORT)
