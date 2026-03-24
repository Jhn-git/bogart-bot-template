"""Entry point for the wandering bot."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure bot/ directory is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from quotes import load_quotes
from wandering import WanderingBot


def main() -> None:
    """Load config and start the bot."""
    load_dotenv()

    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        print("ERROR: DISCORD_TOKEN is not set. Copy .env.example to .env and add your token.")
        sys.exit(1)

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    quotes_path = os.environ.get("QUOTES_FILE", "data/quotes.yaml")
    quotes = load_quotes(quotes_path)

    cycle_minutes = int(os.environ.get("DECISION_CYCLE_MINUTES", "720"))
    min_score = float(os.environ.get("MIN_SCORE_THRESHOLD", "50"))
    startup_delay = int(os.environ.get("STARTUP_DELAY_SECONDS", "60"))

    allowed_guild_ids: list[int] | None = None
    raw_ids = os.environ.get("ALLOWED_GUILD_IDS", "").strip()
    if raw_ids:
        allowed_guild_ids = [int(gid.strip()) for gid in raw_ids.split(",") if gid.strip()]

    bot = WanderingBot(
        quotes=quotes,
        cycle_minutes=cycle_minutes,
        min_score=min_score,
        allowed_guild_ids=allowed_guild_ids,
        startup_delay=startup_delay,
    )
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
