"""HTTPS settings shared by the API clients."""
from __future__ import annotations

import functools
import ssl


@functools.lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    """Verify servers against certifi's CA bundle when it is available.

    A frozen app (PyInstaller on macOS in particular) cannot see the system's
    certificate store, so the default context fails with
    CERTIFICATE_VERIFY_FAILED. certifi ships its own bundle and the
    PyInstaller hook packs it with the app.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()
