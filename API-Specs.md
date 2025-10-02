# 🧱 Architecture & Components

This project uses a modular and testable architecture designed for clarity, maintainability, and correctness. All core logic is organized under the `scheduler/` Django app, with isolated layers for API, data, services, and configuration.

---

## 📁 Folder Structure

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

## ⚙️ `assignment/settings.py` Modifications

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

## 🔍 Component Breakdown

### 🌐 api/ — Request/Response Layer

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

### 🧬 data/ — Persistence Layer

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

### ⚙️ services/ — Core Logic Layer

- **reviews.py:**
  - Orchestrates the entire review processing logic:
    - Validates idempotency
    - Schedules the next review time
    - Saves or reuses DB rows
    - Uses logic from `config.py` to calculate intervals.

---

### 📐 config.py — Interval Strategy

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

### 🧪 tests/ — Validation Layer

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

## 🔄 System Flow (High-Level)

```mermaid
flowchart TD
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

## 🔁 Idempotency Logic

- Review submissions use `idempotency_key`.
- If a review already exists with that key, the system returns the same result with:

```json
{
  "idempotent": true
}
```

- Ensures safe retries in client applications.

---

## ⚖️ Design Principles

- ✅ **Modular:** Each component handles one clear concern.
- ✅ **Scalable:** Stateless logic, horizontal DB-friendly.
- ✅ **Idempotent:** Prevents double writes and race conditions.
- ✅ **Transparent:** Easy to log, debug, and test.
- ✅ **Extensible:** You can plug in more ratings or advanced logic via `config.py`.
