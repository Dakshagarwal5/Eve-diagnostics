# EVE Healthcare — Diagnostic Test Bookings API

A small backend service for booking diagnostic tests and simulating payments,
built with **FastAPI**, **SQLAlchemy**, and **JWT auth**.

## Tech stack

- FastAPI (Python) — simple, fast, auto-generates OpenAPI/Swagger docs
- SQLAlchemy ORM
- **SQLite by default** (zero setup — good for reviewing/running quickly),
  **PostgreSQL supported** via `DATABASE_URL` and via `docker-compose`
- JWT auth (`python-jose`) + bcrypt password hashing (`passlib`)
- Pytest for tests

## How to run locally

### Option A — plain Python (SQLite, fastest way to try it)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`, interactive Swagger docs at
`http://localhost:8000/docs`.

### Option B — Docker Compose (Postgres)

```bash
docker-compose up --build
```

This starts the API on `http://localhost:8000` backed by a Postgres container.

### Running tests

```bash
pytest -v
```

## Environment variables

| Variable       | Default                  | Notes                                   |
|----------------|---------------------------|------------------------------------------|
| `DATABASE_URL` | `sqlite:///./eve.db`      | Set to a Postgres URL to use Postgres    |
| `JWT_SECRET`   | `dev-secret-change-me`    | Change in production                     |

## API Endpoints

### Auth
| Method | Endpoint         | Auth | Description                     |
|--------|------------------|------|----------------------------------|
| POST   | `/auth/signup`   | No   | Create a user, returns JWT       |
| POST   | `/auth/login`    | No   | Login, returns JWT               |

```bash
curl -X POST localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "a@b.com", "password": "password123"}'
```

### Centres & Tests
| Method | Endpoint                        | Auth | Description                  |
|--------|----------------------------------|------|-------------------------------|
| POST   | `/centres/`                      | Yes  | Create a diagnostic centre    |
| GET    | `/centres/`                      | No   | List centres (with tests)     |
| GET    | `/centres/{id}`                  | No   | Get one centre                |
| POST   | `/centres/{id}/tests`            | Yes  | Add a test to a centre        |
| GET    | `/centres/{id}/tests`            | No   | List a centre's tests         |

```bash
curl -X POST localhost:8000/centres/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name": "City Diagnostics", "location": "Delhi"}'

curl -X POST localhost:8000/centres/<centre_id>/tests \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"name": "Blood Test", "price": 500}'
```

### Bookings
| Method | Endpoint                    | Auth | Description                        |
|--------|-------------------------------|------|-------------------------------------|
| POST   | `/bookings/`                  | Yes  | Book a test (status → `PENDING`)    |
| GET    | `/bookings/`                  | Yes  | List my bookings                    |
| GET    | `/bookings/{id}`               | Yes  | Get my booking (owner only)         |
| POST   | `/bookings/{id}/cancel`        | Yes  | Cancel a `PENDING` booking          |

```bash
curl -X POST localhost:8000/bookings/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"test_id": "<test_id>", "centre_id": "<centre_id>", "appointment_time": "2026-10-01T10:00:00"}'
```

### Payments
| Method | Endpoint             | Auth | Description                                        |
|--------|-----------------------|------|-----------------------------------------------------|
| POST   | `/payments/`           | Yes  | Simulate paying for a booking (~80% success rate)   |
| POST   | `/payments/webhook/`   | No   | Simulated payment-provider webhook (**idempotent**) |

```bash
curl -X POST localhost:8000/payments/ \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"booking_id": "<booking_id>"}'

curl -X POST localhost:8000/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"event_id": "evt-123", "booking_id": "<booking_id>", "status": "SUCCESS"}'
```

## Database / schema design

- **User** — `id, email, hashed_password`
- **DiagnosticCentre** — `id, name, location`
- **DiagnosticTest** — `id, name, price, centre_id` (belongs to a centre)
- **Booking** — `id, user_id, test_id, centre_id, appointment_time, amount, status, created_at`
  - `status` is one of `PENDING / CONFIRMED / FAILED / CANCELLED`
  - `amount` is copied from the test's price at booking time (so later price
    changes don't retroactively change what a user was charged)
- **Payment** — `id, booking_id, event_id (unique), status, created_at`
  - One row per **processed payment event**. `event_id` has a **unique
    constraint** — this is what makes both `/payments/` and
    `/payments/webhook/` idempotent: if an event with the same `event_id`
    was already processed, the existing row is returned and the booking is
    never touched twice. A duplicate/retried webhook call can't create a
    second payment or flip a `CONFIRMED` booking back and forth.

## Key assumptions

- No admin role: any authenticated user can create centres/tests, to keep
  scope small. In a real system this would be a separate `is_admin` flag or
  role-based check.
- A booking can only be paid for while it is `PENDING`; once `CONFIRMED` or
  `FAILED`, further payment/webhook events for that booking are ignored aside
  from being idempotently recorded.
- `/payments/` (the "pay now" endpoint) simulates the payment provider
  directly and applies the result immediately, with an ~80% success rate.
  `/payments/webhook/` simulates the *provider calling us back* — separate
  endpoint, same idempotency mechanism (`event_id`), no auth (providers can't
  send a user's JWT), since it represents an external system.
- SQLite is the default DB for zero-setup local running; Postgres is fully
  supported by just changing `DATABASE_URL` (docker-compose.yml wires this
  up automatically).

## What I'd improve with more time

- Admin/role-based authorization instead of "any logged-in user can manage centres"
- Pagination on list endpoints (`/centres/`, `/bookings/`)
- Rate limiting on `/auth/login` and `/payments/webhook/`
- Retry/backoff handling and a dead-letter queue for webhook processing
  (e.g. via Celery + Redis) instead of synchronous handling
- Structured (JSON) logging and request tracing
- More granular test coverage (e.g. price=0 edge cases, expired JWTs, clock
  skew on `appointment_time`)
- Swagger is already free via FastAPI (`/docs`), but I'd add richer
  descriptions/examples per endpoint
