# Architecture & Components

This project uses a modular and testable architecture designed for clarity, maintainability, and correctness. All core logic is organized under the `scheduler/` Django app, with isolated layers for API, data, services, and configuration.

---

## Folder Structure

```
scheduler/
├── api/
│   ├── views.py         # Handles HTTP requests and orchestrates logic
│   ├── urls.py          # Defines /reviews and /due-cards routes
│   └── serializers.py   # Validates input and formats output
│
├── data/
│   ├── models.py        # Django models (PostgreSQL-backed)
│   └── repos.py         # DB access layer: fetch/create review records
│
├── services/
│   └── reviews.py       # Review processing: scheduling, idempotency
│
├── tests/
│   ├── test_scheduler.py           # Unit tests (pure logic)
│   └── test_integration_server.py  # Integration tests (live API + DB)
│
└── config.py            # Interval strategy: tunable multipliers, caps
```

---

## `assignment/settings.py` Modifications

- **Added app to `INSTALLED_APPS`:**

```python
INSTALLED_APPS = [
    ...
    "scheduler",
]
```

- **Configured PostgreSQL as the database backend:**

**Local Development**
- Connects to the flashcards DB using your OS user.
- No password or env needed if running locally.

**Production (via .env):**

```env
POSTGRES_DB=flashcards
POSTGRES_USER=postgres
POSTGRES_PASSWORD=supersecret
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

---

## Component Breakdown

### api/ | Request/Response Layer

- **views.py:**
  - Implements two endpoints:
    - `POST /reviews`: Submit a flashcard review with rating and idempotency key.
    - `GET /users/<uuid>/due-cards?until=...`: Fetch card IDs due before a given UTC datetime.
- **urls.py:**
  - Maps endpoint paths to views.
- **serializers.py:**
  - Validates incoming request payloads.
  - Transforms Review model into structured JSON responses.

---

### data/ | Persistence Layer

- **models.py:**
  - Defines the Review model:
    - `user_id`, `card_id`, `rating`, `interval_seconds`
    - `next_review_utc`, `created_at`, `idempotency_key`
- **repos.py:**
  - Abstracts DB access:
    - `get_or_create_review()`
    - `fetch_due_cards()`
    - `check_idempotent_request()`

---

### services/ | Core Logic Layer

- **reviews.py:**
  - Orchestrates the entire review processing logic:
    - Validates idempotency
    - Schedules the next review time
    - Saves or reuses DB rows
    - Uses logic from `config.py` to calculate intervals.

---

### config.py | Interval Strategy

Contains the main logic for scheduling review intervals. You can adjust the spacing algorithm easily from here:

```python
RATING_0_INTERVAL = 60              # 1 min
RATING_1_MIN_INTERVAL = 86400       # 1 day
RATING_2_MIN_INTERVAL = 345600      # 4 days

GROWTH_1 = 1.5                      # multiplier for rating=1
GROWTH_2 = 2.5                      # multiplier for rating=2
MAX_INTERVAL = 365 * 24 * 3600      # cap: 1 year in seconds
```

This logic ensures:
- Monotonic growth
- Deterministic results
- Bounded intervals

---

### tests/ | Validation Layer

- **test_scheduler.py:**
  - Unit tests for:
    - Interval generation
    - Rating logic
    - Growth and cap rules
- **test_integration_server.py:**
  - Live API tests using requests:
    - Tests full flow (POST + GET)
    - Validates idempotency
    - Ensures PostgreSQL records are correct

---

##  System Flow (High Level)

```
  A[Client Request] -->|POST /reviews| B[api.views]
  B --> C[api.serializers]
  C --> D[services.reviews.process_review()]
  D --> E[data.repos] --> F[data.models.Review]
  F -->|Persist| G[PostgreSQL]

  A2[Client Request] -->|GET /due-cards| B2[api.views]
  B2 --> C2[api.serializers]
  C2 --> E2[data.repos.fetch_due_cards()]
  E2 --> G
```

---

## Idempotency Logic

- Review submissions use `idempotency_key`.
- If a review already exists with that key, the system returns the same result with:

```json
{
  "idempotent": true
}
```

- Ensures safe retries in client applications.

---

## Design Principles

- **Modular:** Each component handles one clear concern.
- **Scalable:** Stateless logic, horizontal DB-friendly.
- **Idempotent:** Prevents double writes and race conditions.
- **Transparent:** Easy to log, debug, and test.
- **Extensible:** You can plug in more ratings or advanced logic via `config.py`.

# API Usage Examples

This backend exposes two main endpoints:

```
| Method | Path                                     | Purpose                              |
|--------|------------------------------------------|--------------------------------------|
| POST   | `/reviews`                               | Submit a review & get next due date |
| GET    | `/users/{user_id}/due-cards?until=...`   | List card IDs due before `until`    |
```
---

## ▶POST `/reviews`

Submit a flashcard review with:
```
- `user_id` (UUID)
- `card_id` (UUID)
- `rating` (`0 = 分からない`, `1 = 分かる`, `2 = 簡単`)
- `idempotency_key`: a unique string per request to prevent duplicates.
```

### Example `curl`
```bash
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-1234",
    "card_id": "card-5678",
    "rating": 2,
    "idempotency_key": "review-abc"
  }'
  ```

### Sample response:
```json
{
  "interval_seconds": 345600,
  "next_review_utc": "2025-10-06T12:00:00Z",
  "rating_label": "簡単",
  "idempotent": false
}
```

### If the same request is sent again with the same idempotency_key, the response will be:
```json
{
  "interval_seconds": 345600,
  "next_review_utc": "2025-10-06T12:00:00Z",
  "rating_label": "簡単",
  "idempotent": true
}
```

```bash
GET /users/{user_id}/due-cards?until=...
```

Returns a list of card IDs whose next_review_utc is less than or equal to the provided until datetime.

### Example curl
```bash
curl "http://localhost:8000/users/user-1234/due-cards?until=2025-10-06T00:00:00Z"
```

### Sample Response
```json
{
  "card_ids": ["card-5678", "card-9012"]
}
```

### If no cards are due yet:
```json
{
  "card_ids": []
}
```

### All queries are performed automatically in the test cases

```bash
uv run poe test
Poe => pytest
============================================ test session starts =============================================
platform darwin -- Python 3.12.9, pytest-8.4.1, pluggy-1.6.0
django: version: 5.2.4, settings: assignment.settings (from env)
rootdir: /Users/lb/Development/Flashcard-Scheduler/general-assignment-template
configfile: pytest.ini
testpaths: scheduler/tests
plugins: django-4.11.1
collected 12 items                                                                                           

scheduler/tests/test_scheduler.py::test_rating_zero_immediate_retry 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=0 (分からない) → status=201 interval=60 idempotent=False
08:37:49 [INFO] ✓ Passed: rating=0 scheduled retry in 60s
PASSED                                                                                                 [  8%]
scheduler/tests/test_scheduler.py::test_first_intervals_labels 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=86400 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] ✓ Passed: rating=1=1d(分かる), rating=2=4d(簡単)
PASSED                                                                                                 [ 16%]
scheduler/tests/test_scheduler.py::test_monotonic_growth_multiple_steps 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=86400 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=216000 idempotent=False
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=864000 idempotent=False
08:37:49 [INFO] ✓ Passed: intervals grew monotonically [86400, 216000, 345600, 864000]
PASSED                                                                                                 [ 25%]
scheduler/tests/test_scheduler.py::test_idempotency_true_and_false 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=200 interval=345600 idempotent=True
08:37:49 [INFO] ✓ Passed: idempotency handled correctly
PASSED                                                                                                 [ 33%]
scheduler/tests/test_scheduler.py::test_due_cards_includes_and_excludes 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=0 (分からない) → status=201 interval=60 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] GET /due-cards until=2025-10-02T08:39:49.666315+00:00 → status=200 card_count=1
08:37:49 [INFO] GET /due-cards until=2025-10-01T08:37:49.666318+00:00 → status=200 card_count=0
08:37:49 [INFO] ✓ Passed: due-cards includes only due items
PASSED                                                                                                 [ 41%]
scheduler/tests/test_scheduler.py::test_interval_cap 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=864000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=2160000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=5400000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=13500000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] ✓ Passed: interval capped at 1 year
PASSED                                                                                                 [ 50%]
scheduler/tests/test_integration_server.py::test_rating_zero_immediate_retry_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=0 (分からない) → status=201 interval=60 idempotent=False
08:37:49 [INFO] ✓ Passed: rating=0 scheduled retry in 60s
PASSED                                                                                                 [ 58%]
scheduler/tests/test_integration_server.py::test_first_intervals_labels_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=86400 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] ✓ Passed: rating=1=1d(分かる), rating=2=4d(簡単)
PASSED                                                                                                 [ 66%]
scheduler/tests/test_integration_server.py::test_monotonic_growth_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=86400 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=216000 idempotent=False
08:37:49 [INFO] POST /reviews rating=1 (分かる) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=864000 idempotent=False
08:37:49 [INFO] ✓ Passed: monotonic growth across ratings [86400, 216000, 345600, 864000]
PASSED                                                                                                 [ 75%]
scheduler/tests/test_integration_server.py::test_idempotency_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=200 interval=345600 idempotent=True
08:37:49 [INFO] ✓ Passed: idempotency verified (201 then 200)
PASSED                                                                                                 [ 83%]
scheduler/tests/test_integration_server.py::test_due_cards_includes_and_excludes_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=0 (分からない) → status=201 interval=60 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] GET /due-cards until=2025-10-02T08:39:49.836082+00:00 → status=200 card_count=1
08:37:49 [INFO] GET /due-cards until=2025-10-01T08:37:49.836085+00:00 → status=200 card_count=0
08:37:49 [INFO] ✓ Passed: due-cards includes/excludes correctly
PASSED                                                                                                 [ 91%]
scheduler/tests/test_integration_server.py::test_interval_cap_live 
----------------------------------------------- live log call ------------------------------------------------
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=345600 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=864000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=2160000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=5400000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=13500000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] POST /reviews rating=2 (簡単) → status=201 interval=31536000 idempotent=False
08:37:49 [INFO] ✓ Passed: interval capped at 1 year
PASSED                                                                                                 [100%]

============================================= 12 passed in 0.67s =============================================
```