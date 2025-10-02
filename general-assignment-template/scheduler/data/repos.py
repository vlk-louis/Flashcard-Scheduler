from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import CardSchedule, ReviewLog

def get_or_create_schedule_for_update(user_id, card_id):
    """
    Fetch schedule row and lock it for update to avoid races.
    Create if missing.
    """
    with transaction.atomic():
        try:
            # Lock existing
            sched = (CardSchedule.objects
                     .select_for_update()
                     .get(user_id=user_id, card_id=card_id))
        except CardSchedule.DoesNotExist:
            sched = CardSchedule.objects.create(
                user_id=user_id, card_id=card_id,
                streak=0, last_interval_seconds=0, next_review_at=timezone.now()
            )
            # Lock the just-created row
            sched = (CardSchedule.objects
                     .select_for_update()
                     .get(pk=sched.pk))
        return sched

def get_existing_idempotent(user_id, card_id, idem_key):
    return ReviewLog.objects.filter(
        user_id=user_id, card_id=card_id, idempotency_key=idem_key
    ).first()

def persist_review(user_id, card_id, rating, idem_key, next_review_at, next_interval_seconds):
    """
    Insert ReviewLog; if a concurrent duplicate slips in, return the existing one.
    """
    try:
        return ReviewLog.objects.create(
            user_id=user_id, card_id=card_id, rating=rating,
            idempotency_key=idem_key, next_review_at=next_review_at,
            next_interval_seconds=next_interval_seconds
        ), False
    except IntegrityError:
        # Duplicate idempotency key safeguard
        existing = get_existing_idempotent(user_id, card_id, idem_key)
        return existing, True