# Flashcard Scheduler

A Django + DRF project implementing a **spaced repetition scheduling algorithm** with PostgreSQL persistence.
The system determines when flashcards should next be reviewed, based on user feedback, while enforcing **deterministic growth, idempotency, and data durability**.

---

## Algorithm Description

The scheduler is inspired by spaced repetition research but simplified for clarity and predictability.
It assigns the next review interval (`interval_seconds`) based on the user’s rating of the card:

- **0 = 分からない (Don’t know):** retry immediately (60 seconds)
- **1 = 分かる (Know):** schedule in ~1 day (86,400 seconds)
- **2 = 簡単 (Easy):** schedule in ~4 days (345,600 seconds)

For subsequent reviews, intervals grow monotonically using multiplicative factors while being capped at **365 days**.

### Formula (Simplified)

_Interval settings are editable in `/scheduler/config.py`_

```python
# scheduler/config.py

def schedule_next(rating, last_interval):
    if rating == 0:
        return 60  # always retry in 60s
    elif rating == 1:
        next_interval = max(86400, last_interval * 1.5)  # at least 1 day
    elif rating == 2:
        next_interval = max(345600, last_interval * 2.5)  # at least 4 days
    return min(next_interval, 365 * 24 * 3600)  # cap at 1 year
```

### Key Properties

- **Deterministic:** Same inputs always yield the same interval.
- **Monotonic:** Intervals never shrink.
- **Bounded:** Maximum interval is capped at 1 year.
- **Simple & Transparent:** All values are easy to inspect in logs and database.

### Why the Algorithm Satisfies the Rules

1. **Immediate retry for rating=0:**
   - Always returns 60s, ensuring failed cards reappear quickly.
2. **Expected first intervals:**
   - First review with rating=1 → 1 day
   - First review with rating=2 → 4 days
3. **Monotonic growth:**
   - Intervals are calculated as a function of the previous interval × growth factor, guaranteeing non-decreasing intervals across review cycles.
4. **Cap Rule — Maximum interval ≤ 1 year:**
   - Growth stops at 31,536,000 seconds, preventing runaway intervals.

---

## Testing Strategy

The repository includes a comprehensive test suite:

- **Unit Tests (Django test client):**
  - Verify immediate retry for rating=0
  - Verify first intervals and labels
  - Verify monotonic growth across multiple reviews
  - Verify idempotency (same request key returns same schedule)
  - Verify due-cards endpoint includes/excludes correctly
  - Verify intervals are capped at 1 year
- **Integration Tests (live server with requests):**
  - Send real API calls against a running server
  - Validate responses and ensure logs match expectations
- **Persistence Test (PostgreSQL):**
  - Insert reviews
  - Query database directly to confirm rows exist with correct fields

_All tests produce structured logs so each step is transparent._

---

## Setup Instructions

1. **Clone and install dependencies**

```sh
   git clone <https://github.com/vlk-louis/Flashcard-Scheduler.git>
   cd Flashcard-Scheduler
   uv sync --all-groups
```

2. **Setup PostgreSQL (15+)**

```sh
   brew install postgresql@15
   brew services start postgresql@15
   createdb flashcards
```

3. **Environment Configuration**

   By default:
   - Local development: connects to flashcards DB using your OS user (no password).
   - Production: use environment variables (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`).

   Example `.env` (not committed to git):

```env
   POSTGRES_DB=flashcards
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=supersecret
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
```

4. **Navigate to project folder**
```sh
cd general-assignment-template
```

5. **Run migrations**

```sh
uv run manage.py migrate
```

6. **Start server**

```sh
uv run python manage.py runserver
```

7. **Run tests**

```sh
uv run poe test
```

_Tests cover:_
- Unit rules validation
- Integration against live server
- Persistence into Postgres

---

## ⚡ Performance Notes

- **Complexity:** O(1) per review; no global state required.
- **Database load:** Only inserts and lookups keyed by user_id and card_id.
- **Idempotency:** Ensures duplicate requests do not create duplicates in DB.
- **Scalability:**
  - Can be sharded by user ID for horizontal scaling.
  - All computations can run in memory without external dependencies.
- **Logging:**
  - Local dev: human-readable colored logs
  - Production: JSON logs for structured ingestion

---

## One-liner Quickstart

```sh
brew services start postgresql@15 \
  && createdb flashcards \
  && cd general-assignment-template \
  && uv sync --all-groups \
  && uv run python manage.py migrate \
  && uv run python manage.py runserver \
  && uv run poe test
```