import pytest
import requests
import uuid
import logging
from datetime import datetime, timedelta, timezone

BASE_URL = "http://127.0.0.1:8000"
logger = logging.getLogger(__name__)

def post_review(user_id, card_id, rating, idem):
    """Helper for POST /reviews"""
    payload = {
        "user_id": str(user_id),
        "card_id": str(card_id),
        "rating": rating,
        "idempotency_key": idem,
    }
    r = requests.post(f"{BASE_URL}/reviews", json=payload)
    data = r.json()
    logger.info(
        "POST /reviews rating=%s (%s) → status=%s interval=%s idempotent=%s",
        rating,
        {0: "分からない", 1: "分かる", 2: "簡単"}[rating],
        r.status_code,
        data.get("interval_seconds"),
        data.get("idempotent"),
    )
    return r


def get_due(user_id, until):
    """Helper for GET /users/{id}/due-cards"""
    r = requests.get(f"{BASE_URL}/users/{user_id}/due-cards", params={"until": until.isoformat()})
    data = r.json()
    logger.info(
        "GET /due-cards until=%s → status=%s card_count=%s",
        until.isoformat(),
        r.status_code,
        len(data["card_ids"]),
    )
    return r


@pytest.mark.integration
def test_rating_zero_immediate_retry_live():
    """rating=0 → retry within 60s"""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()
    r = post_review(user_id, card_id, 0, "idem-live-0")
    d = r.json()
    assert r.status_code == 201
    assert d["interval_seconds"] == 60
    assert d["rating_label"] == "分からない"
    logger.info("✓ Passed: rating=0 scheduled retry in 60s")


@pytest.mark.integration
def test_first_intervals_labels_live():
    """First reviews produce expected intervals and labels"""
    user_id = uuid.uuid4()

    r1 = post_review(user_id, uuid.uuid4(), 1, "idem-live-1")
    d1 = r1.json()
    assert d1["interval_seconds"] == 86400
    assert d1["rating_label"] == "分かる"

    r2 = post_review(user_id, uuid.uuid4(), 2, "idem-live-2")
    d2 = r2.json()
    assert d2["interval_seconds"] == 345600
    assert d2["rating_label"] == "簡単"

    logger.info("✓ Passed: rating=1=1d(分かる), rating=2=4d(簡単)")


@pytest.mark.integration
def test_monotonic_growth_live():
    """Intervals should not shrink across multiple reviews"""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()
    intervals = []
    for i, r in enumerate([1, 2, 1, 2]):
        resp = post_review(user_id, card_id, r, f"idem-live-grow-{i}")
        intervals.append(resp.json()["interval_seconds"])

    assert all(intervals[i] <= intervals[i+1] for i in range(len(intervals)-1))
    logger.info("✓ Passed: monotonic growth across ratings %s", intervals)


@pytest.mark.integration
def test_idempotency_live():
    """Identical requests should reuse result with 200 + idempotent=True"""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()

    first = post_review(user_id, card_id, 2, "idem-live-same")
    d1 = first.json()
    assert first.status_code == 201
    assert d1["idempotent"] is False

    second = post_review(user_id, card_id, 2, "idem-live-same")
    d2 = second.json()
    assert second.status_code == 200
    assert d2["idempotent"] is True
    assert d1["next_review_utc"] == d2["next_review_utc"]

    logger.info("✓ Passed: idempotency verified (201 then 200)")


@pytest.mark.integration
def test_due_cards_includes_and_excludes_live():
    """Due-cards should include due items and exclude future ones"""
    user_id, card_due, card_future = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    # rating=0 → due soon
    post_review(user_id, card_due, 0, "idem-live-due")
    # rating=2 → far future
    post_review(user_id, card_future, 2, "idem-live-future")

    until_due = datetime.now(timezone.utc) + timedelta(minutes=2)
    until_past = datetime.now(timezone.utc) - timedelta(days=1)

    r1 = get_due(user_id, until_due)
    assert str(card_due) in r1.json()["card_ids"]

    r2 = get_due(user_id, until_past)
    assert r2.json()["card_ids"] == []

    logger.info("✓ Passed: due-cards includes/excludes correctly")


@pytest.mark.integration
def test_interval_cap_live():
    """Ensure intervals never exceed 365 days"""
    user_id, card_id = uuid.uuid4(), uuid.uuid4()
    last_interval = 0

    for i in range(12):
        resp = post_review(user_id, card_id, 2, f"idem-live-cap-{i}")
        last_interval = resp.json()["interval_seconds"]

    assert last_interval <= 365 * 24 * 3600
    logger.info("✓ Passed: interval capped at 1 year")