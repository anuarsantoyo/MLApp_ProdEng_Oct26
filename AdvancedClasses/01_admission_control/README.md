# Class 1 — Admission control

API keys (auth + authz), a time-based rate limit, and token quotas with
prepaid credits — all backed by SQLite.

## Files

| file | what it does |
|---|---|
| `create_db.py` | builds and seeds `class1.db` (drops + recreates) |
| `app.py` | the FastAPI service with every gate |
| (notebook) | the class walkthrough — built later, drives `app.py` over HTTP |

## Run

```bash
python create_db.py           # once: build + seed the database
uvicorn app:app --reload      # start the server in a terminal
```

Open http://127.0.0.1:8000/docs to poke the endpoints.

## Seeded callers (send as the `x-api-key` header)

| name | key | plan | monthly tokens | credits |
|---|---|---|---|---|
| Alice | `alice-123` | pro | 5000 | 1000 |
| Bob | `bob-456` | free | 2000 | 600 |

Rate limit: `REQUESTS_PER_MINUTE = 5` (set in `app.py`).

## The gates, in order

```
401 authentication   no / unknown key
403 authorization    only your own /v1/usage/{user_id}
429 rate limit       requests per minute, sliding window  (counted BEFORE validation)
422 validation       missing/bad body
402 quota / credits  monthly token allowance, then prepaid balance
handler              the (simulated) expensive work
```

## Endpoints

| method | path | shows |
|---|---|---|
| GET | `/health` | public, 200 |
| POST | `/v1/analyze` | the full gate stack (auth, rate, validation, quota, credits) |
| GET | `/v1/usage/{user_id}` | authorization (403 if you ask for someone else) |
| POST | `/v1/credits/topup` | add prepaid tokens |
| POST | `/_reset` | teaching helper: wipe logs/usage, restore seed balances |

## Why the 422 still costs a rate-limit slot

The rate limiter is a FastAPI dependency, so it runs **before** the body is
validated. A malformed request (422) is counted at the door and burns one of the
caller's requests — "admission before validation."
