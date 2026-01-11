import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
CACHE_TIME = 3600  # 1 hour
RATE_LIMIT = 3     # requests
RATE_TIME = 10     # seconds
