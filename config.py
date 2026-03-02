import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

OWNER_IDS = list(map(int, os.environ.get("OWNER_IDS", "").split()))

CACHE_TIME = int(os.environ.get("CACHE_TIME", 3600))

RATE_LIMIT = int(os.environ.get("RATE_LIMIT", 3))
RATE_TIME = int(os.environ.get("RATE_TIME", 10))

FORCE_CHANNEL_1 = os.environ.get("FORCE_CHANNEL_1")
FORCE_CHANNEL_2 = os.environ.get("FORCE_CHANNEL_2")

DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", 4))
