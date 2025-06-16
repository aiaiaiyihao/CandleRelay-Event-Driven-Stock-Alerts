# Market‑Data‑Service

A production‑ready micro‑service that pulls real‑time stock prices from **yfinance**, streams raw ticks through **Kafka**, calculates 5‑point moving averages, and serves everything via a **FastAPI** REST API.

---

## Features

| Layer      | Tech                               | Purpose                                                                  |
| ---------- | ---------------------------------- | ------------------------------------------------------------------------ |
| Data Fetch | `yfinance`                         | Pull latest price quotes                                                 |
| Storage    | **PostgreSQL**                     | Persist raw ticks & computed MAs                                         |
| Cache      | **Redis**                          | 100‑second hot‑cache for `/prices/latest`                                |
| Stream     | **Kafka + confluent‑kafka‑python** | Publish raw updates (`price‑events`)                                     |
| Consumer   | Async worker                       | Compute 5‑MA → `symbol_averages`                                         |
| API        | **FastAPI**                        | `GET /prices/latest`, `POST /prices/poll`, `POST /prices/poll/stop/{id}` |
| DevOps     | Docker Compose + GitHub Actions    | CI lint/tests, container build                                           |

---

## Repo Layout

```
market-data-service/
├── app/
│   ├── api/          # FastAPI routers
│   ├── core/         # settings, DB, Redis, Kafka cfg
│   ├── models/       # SQLAlchemy ORM models
│   ├── services/     # polling, provider, consumer logic
│   └── schemas/      # Pydantic request/response models
├── tests/            # pytest suite (unit + integration)
├── docker/           # Dockerfile & compose overrides
├── docs/             # Architecture diagrams
└── .github/workflows/ci.yml
```

---

## Quick‑start (local)

```bash
# 1. clone private repo
$ git clone git@github.com:aiaiaiyihao/market-data-service.git
$ cd market-data-service

# 2. spin up infra (Postgres, Redis, Kafka, FastAPI)
$ docker-compose up --build

# 3. hit swagger
open http://localhost:8000/docs
```

<details>
<summary>Ports</summary>

| Service             | Port |
| ------------------- | ---- |
| FastAPI             | 8000 |
| PostgreSQL          | 5432 |
| Redis               | 6379 |
| Kafka Broker        | 9092 |
| Kafka UI (optional) | 8081 |

</details>

---

## Manual dev venv

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements/dev.txt
uvicorn app.main:app --reload
```

Environment vars (see `.env.example`):

```
DATABASE_URL=postgresql://admin:admin@localhost:5432/marketdb
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP=localhost:9092
```

---

## 📑 API Reference

### `GET /prices/latest`

| Query      | Type | Required | Default    |
| ---------- | ---- | -------- | ---------- |
| `symbol`   | str  | ✅        | –          |
| `provider` | str  | ❌        | `yfinance` |

**200**

```json
{
  "symbol": "AAPL",
  "price": 189.31,
  "timestamp": "2025-06-15T18:22:01Z",
  "provider": "yfinance"
}
```

### `POST /prices/poll`

```json
{
  "symbols": ["AAPL", "MSFT"],
  "interval": 60,
  "provider": "yfinance"
}
```

**202 Accepted**

```json
{
  "job_id": "poll_abc123",
  "status": "accepted",
  "config": {
    "symbols": ["AAPL", "MSFT"],
    "interval": 60,
    "provider": "yfinance"
  }
}
```

### `POST /prices/poll/stop/{job_id}`

Stops a running poll.

---

### ❗ Error Codes

| Code | Reason                               |
| ---- | ------------------------------------ |
| 400  | invalid provider / duplicate symbols |
| 404  | symbol or job not found              |
| 429  | rate‑limit (future)                  |
| 500  | unexpected error                     |

---

## 🏗️ Architecture Decisions

* **Single‑table raw ticks** → simplifies Kafka producer and MA consumer.
* **JSON column for `symbols`** in `poll_jobs` → easy to extend to arbitrary symbol sets.
* **Composite indexes** on `(symbol, timestamp)` for fast look‑ups and MAs.
* **Idempotent Kafka producer** → safe retries.
* **Graceful shutdown** via FastAPI `lifespan` → flush Kafka, close Redis.

See full diagrams in [`docs/`](docs).

---

## Docker

```bash
# Build only API container
$ docker build -t market-api -f docker/Dockerfile .

# Full stack
$ docker-compose up -d --build
```

---

## Troubleshooting

| Symptom                                         | Fix                                                                   |
| ----------------------------------------------- | --------------------------------------------------------------------- |
| `Symbol already polling`                        | Stop existing job: `POST /prices/poll/stop/{id}`                      |
| Kafka `Broker not available`                    | Ensure Kafka & ZooKeeper containers healthy; restart `docker-compose` |
| `psycopg2.errors.DuplicateTable` on dev restart | Delete old index or remove `Base.metadata.drop_all()` in `main.py`    |
| Infinite retries in CI                          | Update `.github/workflows/ci.yml` Postgres health‑check timeout       |

