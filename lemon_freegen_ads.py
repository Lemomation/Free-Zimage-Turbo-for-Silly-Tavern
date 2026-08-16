"""FreeGen compatibility: preserve the ads required by its free service."""


def install(freegen_module):
    """Replace only FreeGen's imported ad cleaner with a harmless no-op."""
    async def keep_ads(page, provider_logger):
        return False

    freegen_module.clear_ads = keep_ads
