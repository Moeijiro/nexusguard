"""Run the bot: ``python -m app.bot``."""

from __future__ import annotations

import logging
import sys

from app.core.config import settings


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    if not settings.discord_bot_token:
        print("DISCORD_BOT_TOKEN isn't set. The dashboard's demo mode doesn't need the bot; "
              "to protect a real server, add the token to backend/.env.", file=sys.stderr)
        return 1
    from app.bot.client import NexusGuardBot

    NexusGuardBot().run(settings.discord_bot_token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
