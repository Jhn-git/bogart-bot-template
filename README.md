# Discord Character Bot Template

A simple Discord bot that wanders between channels on a timer, dropping in-character messages. No commands, no database — just a YAML file full of quotes and a bot token.

---

## Creating Your Discord Bot

Before running anything, you need to create a bot application on Discord. This only takes a few minutes.

### 1. Create an Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** in the top right.
3. Give it a name — this is your character's name as it will appear in servers. You can change it later.
4. Click **Create**.

### 2. Set Up the Bot

1. In the left sidebar, click **Bot**.
2. Click **Reset Token**, then **Yes, do it!** to generate a new token.
3. Click **Copy** to copy the token. **Save this somewhere safe** — you won't be able to see it again. This goes in your `.env` file later.
4. Scroll down to **Privileged Gateway Intents** and enable:
  - **Message Content Intent** — required so the bot can read messages for channel scoring.
5. Click **Save Changes**.

> ⚠️ **Never share your bot token.** Anyone with it can control your bot. If you accidentally leak it (e.g., push it to GitHub), go back to the portal and reset it immediately.

### 3. Invite the Bot to Your Server

1. In the left sidebar, click **OAuth2**.
2. Under **OAuth2 URL Generator**, check the **bot** scope.
3. In the **Bot Permissions** section that appears below, check:
  - ✅ View Channels
  - ✅ Send Messages
  - ✅ Read Message History
4. Copy the **Generated URL** at the bottom.
5. Open that URL in your browser, choose the server you want to add the bot to, and click **Authorize**.

The bot will appear in your server as offline until you run it.

---

## Setup

### 1. Clone the Repo

```bash
git clone <repo-url>
cd bogart-bot-template
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Your Token

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace `your_token_here` with the bot token you copied from the Developer Portal.

### 4. Customize Your Character

Edit `data/quotes.yaml` with your own messages:

```yaml
generic_wandering_messages:
  - "The shadows whisper of adventures yet to come..."
  - "Has anyone seen my lucky coin? I swear I left it here."
  - "What a fine day for mischief!"

# (Optional) Messages for specific channel names
channel_specific_messages:
  general:
    - "Ah, the general channel. Where all great conversations begin."
```

The bot picks randomly from `generic_wandering_messages`, or from a channel-specific list if you've defined one matching that channel's name.

### 5. Run

```bash
python bot/main.py
```

That's it. The bot will wait 60 seconds after startup, then begin its wandering cycle (default: every 12 hours). You should see it come online in your server right away.

**Tip:** For testing, set `DECISION_CYCLE_MINUTES=1` in your `.env` file so you don't have to wait 12 hours to see it post.

---

## Configuration

All settings are optional except the token. Copy `.env.example` to `.env` and uncomment any you want to change:

| Variable | Default | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | *(required)* | Your bot token from the Developer Portal |
| `ALLOWED_GUILD_IDS` | *(all guilds)* | Comma-separated server IDs to restrict posting |
| `QUOTES_FILE` | `data/quotes.yaml` | Path to your quotes file |
| `DECISION_CYCLE_MINUTES` | `720` | Minutes between wandering cycles (12 hours) |
| `MIN_SCORE_THRESHOLD` | `50` | Minimum channel score required to post |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

---

## How the Bot Decides Where to Post

Every cycle, the bot:

1. Skips guilds it already visited in the last 6 hours.
2. Scores every eligible text channel (not NSFW, has permissions).
3. Picks the single highest-scoring channel across all servers.
4. Posts if it meets the minimum score threshold.

Channels are scored on recent activity, author diversity, and how long it's been since anyone (or the bot) posted. Quiet servers accumulate a bonus over time so they don't get forgotten entirely.

---

## Required Discord Permissions

The bot needs these permissions in any channel where it should post:

- **View Channels** — to see text channels
- **Send Messages** — to post wandering messages
- **Read Message History** — to score channels by activity

The bot automatically skips any channel where it's missing permissions. If you want to block the bot from specific channels, just deny it **Send Messages** in that channel's permission overrides.

---

## State

Cooldowns are saved to `data/state.json` automatically and loaded on restart, so the bot remembers where it's been. This file is in `.gitignore` — don't commit it.

---

## Troubleshooting

**Bot is online but never posts**

- Check your `LOG_LEVEL=DEBUG` in `.env` and look at the console output. The bot logs exactly which guilds and channels it evaluates and why it skips them.
- Make sure `DECISION_CYCLE_MINUTES` isn't set too high. Try `1` for testing.
- The bot waits 60 seconds after startup before its first cycle.

**"Privileged intent provided is not enabled"**

- Go back to the [Developer Portal](https://discord.com/developers/applications) → your app → **Bot** → enable **Message Content Intent** → **Save Changes**.

**Bot can't see any channels**

- Make sure the bot role has **View Channels** permission server-wide, or in the specific channels you want it to access.

**Bot posts too often / not often enough**

- Adjust `DECISION_CYCLE_MINUTES` in your `.env`. Lower = more frequent, higher = less frequent.
- Adjust `MIN_SCORE_THRESHOLD` — lower values make the bot less picky about where it posts.