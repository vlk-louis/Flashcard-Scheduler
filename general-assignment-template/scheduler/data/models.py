from django.db import models
from django.utils import timezone

class CardSchedule(models.Model):
    user_id = models.UUIDField()
    card_id = models.UUIDField()
    streak = models.PositiveIntegerField(default=0)
    last_interval_seconds = models.PositiveIntegerField(default=0)
    next_review_at = models.DateTimeField(default=timezone.now)  # UTC

    class Meta:
        unique_together = (("user_id", "card_id"),)
        indexes = [
            models.Index(fields=["user_id", "next_review_at"]),
        ]

class ReviewLog(models.Model):
    user_id = models.UUIDField()
    card_id = models.UUIDField()
    rating = models.SmallIntegerField()
    idempotency_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)
    next_review_at = models.DateTimeField()
    next_interval_seconds = models.PositiveIntegerField()

    class Meta:
        unique_together = (("user_id", "card_id", "idempotency_key"),)
        indexes = [
            models.Index(fields=["user_id", "card_id", "created_at"]),
        ]