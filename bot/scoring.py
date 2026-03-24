"""Channel scoring algorithm for the wandering bot."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import discord

logger = logging.getLogger(__name__)

_24H = timedelta(hours=24)
_BOT_RECENT_THRESHOLD = 7200  # 2 hours in seconds


async def score_channel(
    channel: discord.TextChannel,
    bot_id: int,
    channel_last_bot_post: dict[int, float],
) -> float:
    """Score a text channel based on recent activity.

    Scoring order (as specified):
    1. Activity base + message bonus + diversity
    2. × human preference multiplier
    3. × bot-was-recent penalty
    4. + loneliness bonus
    5. Floor at 1.0

    Returns 0.0 if the channel history cannot be read.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - _24H

    recent_messages: list[discord.Message] = []
    last_message_time: datetime | None = None

    try:
        async for msg in channel.history(limit=15):
            if last_message_time is None:
                last_message_time = msg.created_at
            if msg.created_at >= cutoff:
                recent_messages.append(msg)
    except discord.Forbidden:
        logger.debug("No permission to read history in #%s", channel.name)
        return 0.0
    except discord.HTTPException as e:
        logger.warning("HTTP error reading #%s: %s", channel.name, e)
        return 0.0

    count = len(recent_messages)

    # --- Activity base ---
    if count >= 10:
        base = 30.0
    elif count >= 5:
        base = 20.0
    elif count >= 1:
        base = 10.0
    else:
        base = 0.0

    # Message bonus (+1 per recent message, capped at 15)
    msg_bonus = min(float(count), 15.0)

    # Diversity bonus (+3 per unique human author)
    unique_humans = {m.author.id for m in recent_messages if not m.author.bot}
    diversity = len(unique_humans) * 3.0

    subtotal = base + msg_bonus + diversity

    # --- Human preference multiplier ---
    if count > 0:
        bot_count = sum(1 for m in recent_messages if m.author.bot)
        bot_ratio = bot_count / count
        if bot_ratio < 0.5:
            human_mult = 1.5
        elif bot_ratio <= 0.75:
            human_mult = 1.2
        else:
            human_mult = 0.8
    else:
        human_mult = 1.0

    subtotal *= human_mult

    # --- Bot-was-recent penalty ---
    last_bot_ts = channel_last_bot_post.get(channel.id)
    if last_bot_ts is not None and (now.timestamp() - last_bot_ts) < _BOT_RECENT_THRESHOLD:
        subtotal *= 0.5

    # --- Loneliness bonus (added after multipliers) ---
    if count == 0:
        loneliness = 20.0  # dead channel flat bonus
    elif last_message_time is not None:
        age_hours = (now - last_message_time).total_seconds() / 3600
        if age_hours > 6:
            loneliness = 30.0
        elif age_hours > 3:
            loneliness = 15.0
        elif age_hours > 1:
            loneliness = 5.0
        else:
            loneliness = 0.0
    else:
        loneliness = 0.0

    return max(subtotal + loneliness, 1.0)


def apply_guild_silence_bonus(score: float, last_visit_ts: float | None) -> float:
    """Add a silence bonus based on days since the bot last visited a guild.

    +5 points per day of silence, capped at +50 (10 days).
    Resets when the bot posts to that guild.
    """
    if last_visit_ts is None:
        return score + 50.0  # Never visited — maximum bonus

    days_silent = (time.time() - last_visit_ts) / 86400
    bonus = min(days_silent * 5.0, 50.0)
    return score + bonus
