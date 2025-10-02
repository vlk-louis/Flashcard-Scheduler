from datetime import timedelta
from django.utils import timezone
import structlog
from ..data.repos import (
    get_existing_idempotent,
    get_or_create_schedule_for_update,
    persist_review,
)
from ..domain.logic import schedule_next
from ..utils.time import to_jst_iso

logger = structlog.get_logger()

def record_review(user_id, card_id, rating: int, idempotency_key: str):
    logger.info("review_received",
        user_id=str(user_id),
        card_id=str(card_id),
        rating=rating,
        idempotency_key=idempotency_key,
    )

    # Fast path: return previous result if same idempotency_key
    existing = get_existing_idempotent(user_id, card_id, idempotency_key)
    if existing:
        logger.info("idempotent_reuse",
            user_id=str(user_id),
            card_id=str(card_id),
            next_review_utc=existing.next_review_at.isoformat(),
            next_review_jst=to_jst_iso(existing.next_review_at),
        )
        return existing.next_review_at, existing.next_interval_seconds, True

    # Serialize schedule update per (user, card)
    sched = get_or_create_schedule_for_update(user_id, card_id)
    is_first = (sched.last_interval_seconds == 0)

    next_interval = schedule_next(rating, sched.last_interval_seconds, is_first)
    now = timezone.now()
    next_dt = now + timedelta(seconds=next_interval)

    # Update schedule state
    sched.last_interval_seconds = next_interval
    sched.next_review_at = next_dt
    sched.streak = 0 if rating == 0 else (sched.streak + 1)
    sched.save(update_fields=["last_interval_seconds", "next_review_at", "streak"])

    # Persist log
    log, was_idempotent = persist_review(
        user_id, card_id, rating, idempotency_key, next_dt, next_interval
    )

    logger.info("review_scheduled",
        user_id=str(user_id),
        card_id=str(card_id),
        interval_seconds=next_interval,
        next_review_utc=log.next_review_at.isoformat(),
        next_review_jst=to_jst_iso(log.next_review_at),
    )

    return log.next_review_at, log.next_interval_seconds, was_idempotent