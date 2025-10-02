from .enums import Rating
from ..config import MAX_INTERVAL_SECONDS, RETRY_SECONDS, FIRST_INTERVAL, GROWTH

def schedule_next(rating: int, last_interval_seconds: int, is_first: bool) -> int:
    # rating is validated earlier
    if rating == Rating.DONT_REMEMBER:
        return RETRY_SECONDS

    if is_first:
        return min(FIRST_INTERVAL[int(rating)], MAX_INTERVAL_SECONDS)

    proposed = int(last_interval_seconds * GROWTH[int(rating)])
    # Monotonic for correct answers (never shrink)
    return max(min(proposed, MAX_INTERVAL_SECONDS), last_interval_seconds)