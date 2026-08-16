"""Lemon Image API with provider readiness recovery installed."""

import uvicorn

import api_server as _api
import lemon_image_api as _dashboard
from lemon_provider_readiness import install


install(_api.zimage_bridge, _api.redpanda_bridge)
app = _dashboard.app


if __name__ == "__main__":
    _api.logger.info("Starting Lemon Image API (all providers) on %s:%s", _api.HOST, _api.PORT)
    uvicorn.run(app, host=_api.HOST, port=_api.PORT)
