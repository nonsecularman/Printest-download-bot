import time
from collections import defaultdict

_users = defaultdict(list)

def is_flood(user_id, limit, seconds):
    now = time.time()
    _users[user_id] = [t for t in _users[user_id] if now - t < seconds]
    if len(_users[user_id]) >= limit:
        return True
    _users[user_id].append(now)
    return False
