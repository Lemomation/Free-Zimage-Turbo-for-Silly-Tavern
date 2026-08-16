"""Current Lemon Image API entry point with all provider fixes enabled."""

import uvicorn

import api_server as _api
import lemon_image_api_fixed as _fixed
from lemon_freegen_ads import install


install(_api.freegen_bridge)
app = _fixed.app


if __name__ == "__main__":
    _api.logger.info("Starting Lemon Image API (all providers) on %s:%s", _api.HOST, _api.PORT)
    uvicorn.run(app, host=_api.HOST, port=_api.PORT)
