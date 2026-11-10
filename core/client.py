"""Valkey client wrapper."""

import valkey
from .config import config


_client: valkey.Valkey | None = None


def get_client() -> valkey.Valkey:
    """Get or create a Valkey client connection."""
    global _client
    
    if _client is None:
        _client = valkey.Valkey(
            host=config.host,
            port=config.port,
            password=config.password,
            decode_responses=True,  # Return strings, not bytes (except for vectors)
        )
        # Verify connection and module
        _client.ping()
        _verify_search_module(_client)
    
    return _client


def get_binary_client() -> valkey.Valkey:
    """Get a client that doesn't decode responses (needed for binary vector data)."""
    return valkey.Valkey(
        host=config.host,
        port=config.port,
        password=config.password,
        decode_responses=False,
    )


def _verify_search_module(client: valkey.Valkey) -> None:
    """Verify valkey-search module is loaded."""
    modules = client.execute_command("MODULE", "LIST")
    search_loaded = any(
        mod[1] == b"search" or mod[1] == "search"
        for mod in modules
        if isinstance(mod, (list, tuple)) and len(mod) >= 2
    )
    if not search_loaded:
        raise RuntimeError(
            "valkey-search module not loaded. "
            "Start Valkey with: --loadmodule /path/to/valkeysearch.so"
        )


def close_client() -> None:
    """Close the client connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
