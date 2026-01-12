import time
from collections import defaultdict
from config import DAILY_LIMIT

# -------------------------------
# Flood control (same as before)
# -------------------------------
_users = defaultdict(list)

def is_flood(user_id, limit, seconds):
    now = time.time()
    _users[user_id] = [t for t in _users[user_id] if now - t < seconds]
    if len(_users[user_id]) >= limit:
        return True
    _users[user_id].append(now)
    return False


# -------------------------------
# Daily limit (NEW)
# -------------------------------
_daily = {}
DAY = 86400  # 24 hours

def check_daily(user_id: int) -> bool:
    now = time.time()

    # first time user
    if user_id not in _daily:
        _daily[user_id] = {"count": 1, "time": now}
        return True

    data = _daily[user_id]

    # reset after 24 hours
    if now - data["time"] >= DAY:
        _daily[user_id] = {"count": 1, "time": now}
        return True

    # limit reached
    if data["count"] >= DAILY_LIMIT:
        return False

    data["count"] += 1
    return True
