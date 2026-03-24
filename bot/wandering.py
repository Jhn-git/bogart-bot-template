"""Wandering loop: timer, guild/channel selection, and state persistence."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Any

import discord
from discord.ext import commands

from scoring import apply_guild_silence_bonus, score_channel
from quotes import get_quote

logger = logging.getLogger(__name__)

STATE_FILE = Path("data/state.json")
GUILD_COOLDOWN = 21600   # 6 hours — minimum gap between visits to the same guild


class WanderingBot(commands.Bot):
    """A Discord bot that wanders between channels, posting in-character quotes on a timer."""

    def __init__(
        self,
        quotes: dict,
        cycle_minutes: int = 720,
        min_score: float = 50.0,
        allowed_guild_ids: list[int] | None = None,
        startup_delay: int = 60,
    ) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.quotes = quotes
        self.cycle_seconds = cycle_minutes * 60
        self.min_score = min_score
        self.startup_delay = startup_delay
        self.allowed_guild_ids: set[int] | None = set(allowed_guild_ids) if allowed_guild_ids else None

        # Timestamps of last bot post per channel (channel_id -> unix timestamp)
        self.channel_last_bot_post: dict[int, float] = {}
        # Timestamps of last bot visit per guild (guild_id -> unix timestamp)
        self.guild_last_visit: dict[int, float] = {}

        self._load_state()

    # --- State persistence ---

    def _load_state(self) -> None:
        """Load persisted cooldown state from disk."""
        if not STATE_FILE.exists():
            return
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            self.guild_last_visit = {int(k): v for k, v in data.get("guild_last_visit", {}).items()}
            self.channel_last_bot_post = {int(k): v for k, v in data.get("channel_last_bot_post", {}).items()}
            logger.info(
                "Loaded state: %d guild(s), %d channel(s) tracked",
                len(self.guild_last_visit),
                len(self.channel_last_bot_post),
            )
        except Exception as e:
            logger.warning("Could not load state: %s", e)

    def _save_state(self) -> None:
        """Persist cooldown state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "guild_last_visit": {str(k): v for k, v in self.guild_last_visit.items()},
                "channel_last_bot_post": {str(k): v for k, v in self.channel_last_bot_post.items()},
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("State saved.")
        except Exception as e:
            logger.warning("Could not save state: %s", e)

    # --- Discord events ---

    async def on_ready(self) -> None:
        """Called when the bot connects and its cache is populated."""
        logger.info("Logged in as %s (id=%d)", self.user, self.user.id)
        logger.info("Connected to %d guild(s)", len(self.guilds))
        logger.info("First wandering cycle starts in %ds.", self.startup_delay)
        asyncio.ensure_future(self._wandering_loop())

    # --- Main loop ---

    async def _wandering_loop(self) -> None:
        """Sleep, run a cycle, sleep again — forever until shutdown."""
        await asyncio.sleep(self.startup_delay)
        while not self.is_closed():
            await self._run_cycle()
            jitter = random.uniform(-0.15, 0.15)
            sleep_time = self.cycle_seconds * (1 + jitter)
            logger.info("Next cycle in %.0f minutes.", sleep_time / 60)
            await asyncio.sleep(sleep_time)

    async def _run_cycle(self) -> None:
        """Run one wandering decision cycle.

        Iterates all guilds, scores eligible channels, picks the best one, and
        posts a quote if the score meets the threshold.
        """
        logger.info("Running wandering cycle...")
        now = time.time()

        guilds = list(self.guilds)
        if self.allowed_guild_ids:
            guilds = [g for g in guilds if g.id in self.allowed_guild_ids]

        best_channel: discord.TextChannel | None = None
        best_score = 0.0

        for guild in guilds:
            last_visit = self.guild_last_visit.get(guild.id)
            if last_visit is not None and (now - last_visit) < GUILD_COOLDOWN:
                logger.debug("Skipping guild '%s' (cooldown active)", guild.name)
                continue

            for channel in guild.text_channels:
                if channel.is_nsfw():
                    continue
                perms = channel.permissions_for(guild.me)
                if not (perms.view_channel and perms.send_messages and perms.read_message_history):
                    continue

                raw_score = await score_channel(channel, self.user.id, self.channel_last_bot_post)
                if raw_score <= 0.0:
                    continue

                score = apply_guild_silence_bonus(raw_score, last_visit)
                logger.debug("  #%s: %.1f", channel.name, score)

                if score > best_score:
                    best_score = score
                    best_channel = channel

        if best_channel is None:
            logger.info("No eligible channels found this cycle.")
            return

        if best_score < self.min_score:
            logger.info(
                "Best channel #%s scored %.1f (threshold: %.1f) — skipping.",
                best_channel.name,
                best_score,
                self.min_score,
            )
            return

        quote = get_quote(self.quotes, best_channel.name)
        try:
            await best_channel.send(quote)
            logger.info(
                "Posted to #%s in '%s': %r",
                best_channel.name,
                best_channel.guild.name,
                quote,
            )
            self.guild_last_visit[best_channel.guild.id] = now
            self.channel_last_bot_post[best_channel.id] = now
            self._save_state()
        except discord.HTTPException as e:
            logger.error("Failed to post to #%s: %s", best_channel.name, e)

    # --- Shutdown ---

    async def close(self) -> None:
        """Clean shutdown: save state before disconnecting."""
        logger.info("Shutting down — saving state...")
        self._save_state()
        await super().close()
