import pytest
import logging
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import uuid

logger = logging.getLogger(__name__)

# Helpers

def make_review(client, user_id, card_id, rating, idem_key):
    url = reverse("review")
    payload = {
        "user_id": str(user_id),
        "card_id": str(card_id),
        "rating": rating,
        "idempotency_key": idem_key,
    }
    resp = client.post(url, data=payload, content_type="application/json")
    data = resp.json()
    logger.info(
        "POST /reviews rating=%s (%s) → status=%s interval=%s idempotent=%s",
        rating,
        {0: "分からない", 1: "分かる", 2: "簡単"}[rating],
        resp.status_code,
        data.get("interval_seconds"),
        data.get("idempotent"),
    )
    return resp


def get_due_cards(client, user_id, until):
    url = reverse("due-cards", kwargs={"user_id": str(user_id)})
    resp = client.get(url, {"until": until.isoformat()})
    data = resp.json()
    logger.info(
        "GET /due-cards until=%s → status=%s card_count=%s",
        until.isoformat(),
        resp.status_code,
        len(data["card_ids"]),
    )
    return resp


# Tests

@pytest.mark.django_db
def test_rating_zero_immediate_retry(client):
    """Rule 1: rating=0 must return retry within 60s."""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()

    resp = make_review(client, user_id, card_id, 0, "idem-0")
    data = resp.json()

    assert resp.status_code == 201
    assert data["interval_seconds"] == 60
    assert data["rating_label"] == "分からない"
    logger.info("✓ Passed: rating=0 scheduled retry in 60s")


@pytest.mark.django_db
def test_first_intervals_labels(client):
    """Rule 2: First reviews produce expected intervals and labels."""
    user_id = uuid.uuid4()

    # rating=1
    card1 = uuid.uuid4()
    d1 = make_review(client, user_id, card1, 1, "idem-1").json()
    assert d1["interval_seconds"] == 86400
    assert d1["rating_label"] == "分かる"

    # rating=2
    card2 = uuid.uuid4()
    d2 = make_review(client, user_id, card2, 2, "idem-2").json()
    assert d2["interval_seconds"] == 345600
    assert d2["rating_label"] == "簡単"

    logger.info("✓ Passed: rating=1=1d(分かる), rating=2=4d(簡単)")


@pytest.mark.django_db
def test_monotonic_growth_multiple_steps(client):
    """Rule 3: intervals must not shrink, even across multiple reviews."""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()

    intervals = []
    for i, r in enumerate([1, 2, 1, 2]):  # alternate ratings
        resp = make_review(client, user_id, card_id, r, f"idem-grow-{i}")
        data = resp.json()
        intervals.append(data["interval_seconds"])

    assert all(intervals[i] <= intervals[i+1] for i in range(len(intervals)-1))
    logger.info("✓ Passed: intervals grew monotonically %s", intervals)


@pytest.mark.django_db
def test_idempotency_true_and_false(client):
    """Rule 4: first request creates, second with same key reuses."""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()

    # First request to creates schedule
    first = make_review(client, user_id, card_id, 2, "idem-same")
    d1 = first.json()
    assert first.status_code == 201
    assert d1["idempotent"] is False

    # Second identical request is reused, 200 OK, idempotent=True
    second = make_review(client, user_id, card_id, 2, "idem-same")
    d2 = second.json()
    assert second.status_code == 200
    assert d2["idempotent"] is True
    assert d1["next_review_utc"] == d2["next_review_utc"]

    logger.info("✓ Passed: idempotency handled correctly")


@pytest.mark.django_db
def test_due_cards_includes_and_excludes(client):
    """Due cards endpoint should include only those due by 'until'."""
    user_id, card_due, card_future = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    # rating=0 so due in 60s
    due_data = make_review(client, user_id, card_due, 0, "idem-due").json()

    # rating=2 so due much later
    make_review(client, user_id, card_future, 2, "idem-future")

    until_due = timezone.now() + timedelta(minutes=2)
    until_past = timezone.now() - timedelta(days=1)

    # Should include due card
    resp1 = get_due_cards(client, user_id, until_due)
    assert str(card_due) in resp1.json()["card_ids"]

    # Should exclude when until is too early
    resp2 = get_due_cards(client, user_id, until_past)
    assert resp2.json()["card_ids"] == []

    logger.info("✓ Passed: due-cards includes only due items")


@pytest.mark.django_db
def test_interval_cap(client):
    """Ensure max interval never exceeds 365 days."""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()
    last_interval = 0

    for i in range(12):
        resp = make_review(client, user_id, card_id, 2, f"idem-cap-{i}").json()
        last_interval = resp["interval_seconds"]

    assert last_interval <= 365 * 24 * 3600
    logger.info("✓ Passed: interval capped at 1 year")