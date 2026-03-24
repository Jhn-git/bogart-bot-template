"""Quote loading and retrieval for the wandering bot."""

import logging
import random

import yaml

logger = logging.getLogger(__name__)


def load_quotes(path: str) -> dict:
    """Load quotes from a YAML file.

    Returns a dict with at least ``generic_wandering_messages``. Falls back to
    a single ``"..."`` entry if the file is missing or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError("quotes.yaml must be a YAML mapping")
        if "generic_wandering_messages" not in data:
            raise ValueError("quotes.yaml must contain 'generic_wandering_messages'")
        logger.info("Loaded quotes from %s", path)
        return data
    except Exception as e:
        logger.warning("Failed to load quotes from %s: %s — using fallback", path, e)
        return {"generic_wandering_messages": ["..."]}


def get_quote(quotes: dict, channel_name: str) -> str:
    """Return a quote appropriate for the given channel name.

    Checks ``channel_specific_messages`` first; falls back to
    ``generic_wandering_messages``. Returns ``"..."`` on any error.
    """
    try:
        channel_specific: dict = quotes.get("channel_specific_messages", {})
        if channel_name in channel_specific:
            pool: list = channel_specific[channel_name]
            if pool:
                return random.choice(pool)

        generic: list = quotes.get("generic_wandering_messages", [])
        if generic:
            return random.choice(generic)
    except Exception as e:
        logger.warning("Failed to get quote: %s", e)

    return "..."
