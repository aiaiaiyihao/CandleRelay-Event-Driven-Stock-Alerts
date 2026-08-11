# SignalForge

SignalForge is an event-driven stock alerting and strategy backtesting platform.
Users describe market conditions in natural language, review the compiled and
validated Rule DSL, and run the same rule against live Kafka events or historical
market bars. A React dashboard turns this workflow into a focused, interactive
demo suitable for portfolio and interview presentations.

## Core invariant

Live evaluation and historical replay share the same components:

```text
Natural language -> validated Rule DSL
                              |
Live Kafka MarketEvent -------+--> IndicatorEngine --> RuleEvaluator --> Alert
Historical MarketEvent replay +--> IndicatorEngine --> RuleEvaluator --> Backtest
```

Given the same ordered events and rule version, live and replay evaluation must
produce identical results. This behavior is covered by automated tests.

## Implemented capabilities

- Versioned, strictly validated Rule DSL
- AND condition groups and comparison/cross operators
- Normalized, timezone-aware OHLCV `MarketEvent`
- Incremental SMA and volume-ratio indicators
- Explainable condition results with actual left and right values
- Trigger transition and cooldown behavior
- Versioned rule persistence and history
- Historical event replay and persisted backtest summaries
- Kafka market-event codec and manual-offset consumer
- Database-backed alert deduplication and cooldown
- Alert listing, filtering, and acknowledgement
- Deterministic Chinese and English natural-language compiler
- Alembic-managed database schema
- Responsive React rule, backtest, and alert dashboard
- Persistent tracked-symbol watchlist with live ticker lookup
- Interactive 1M/3M/6M/1Y price charts with SMA20, SMA50, and SMA200 overlays

## Example rule

Input:

```text
Alert me when NVDA crosses below SMA20 and volume is more than 2 times the
average of the past 20 trading days.
```

Compiled DSL:

```json
{
  "dsl_version": "1.0",
  "symbol": "NVDA",
  "timeframe": "1d",
  "conditions": {
    "all": [
      {
        "left": {"type": "metric", "metric": "price"},
        "operator": "crosses_below",
        "right": {"type": "indicator", "indicator": "sma", "period": 20}
      },
      {
        "left": {"type": "indicator", "indicator": "volume_ratio", "period": 20},
        "operator": ">",
        "right": {"type": "value", "value": 2}
      }
    ]
  },
  "trigger": "on_false_to_true",
  "cooldown_seconds": 3600
}
```

## Local setup

```bash
python -m venv marketDataServer
source marketDataServer/bin/activate
pip install -r requirements/dev.txt
docker compose -f docker/docker-compose.yml up -d
```

This starts PostgreSQL, Redis, Kafka, the API, the live rule worker, and the
React frontend. The API container applies Alembic migrations before serving
traffic. SignalForge uses its own `signalforge_pgdata` volume so older local
PostgreSQL projects do not interfere with the demo credentials.

Open:

| Surface | URL |
| --- | --- |
| SignalForge dashboard | <http://localhost:3000> |
| FastAPI Swagger | <http://localhost:8000/docs> |
| API health check | <http://localhost:8000/health> |

For manual development without the API and worker containers:

```bash
alembic upgrade head
uvicorn app.main:app --reload
python -m app.kafka.SignalConsumer
```

Import the included demo bars when running the services manually:

```bash
python -m scripts.import_market_bars examples/nvda_daily.csv \
  --symbol NVDA --timeframe 1d --source demo
```

Configuration:

```text
DATABASE_URL=postgresql://admin:admin@localhost:5432/marketdb
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP=localhost:9092
KAFKA_SIGNAL_GROUP=signalforge-live-rules
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## React dashboard

The dashboard is intentionally centered on the project's differentiating flow:

1. Write a market rule in natural language.
2. Search an exact ticker and add it to the persistent watchlist.
3. Select a tracked symbol and inspect its chart across multiple time ranges.
4. Toggle common moving averages to compare trend structure.
5. Compile the text into a validated and explainable Rule DSL.
6. Review and activate the versioned rule.
7. Replay stored market bars and inspect forward returns.
8. View and acknowledge alerts produced by the live Kafka worker.

The UI uses realistic sample content on first render so the project remains
presentable before the local services are started. Actions use the real FastAPI
endpoints whenever the backend is available.

Run the frontend separately during development:

```bash
cd frontend
npm install
npm run dev
```

Set a different API origin in `frontend/.env` when needed:

```text
VITE_API_URL=http://localhost:8000
```

## API overview

### Compile natural language

```http
POST /rules/compile
Content-Type: application/json

{
  "text": "Alert me when NVDA crosses below SMA20 and volume is more than 2 times the average of the past 20 trading days.",
  "cooldown_seconds": 3600
}
```

Compilation returns a candidate DSL, an explanation, and ambiguity warnings. It
does not enable the rule automatically. Submit the reviewed definition to
`POST /rules`.

### Rules

```text
POST  /rules
GET   /rules
GET   /rules/{rule_id}
PUT   /rules/{rule_id}
GET   /rules/{rule_id}/versions
PATCH /rules/{rule_id}/status
```

### Stock lookup and watchlist

```text
GET    /prices/latest?symbol=NVDA
GET    /stocks/NVDA/chart?range=3mo
GET    /watchlist
POST   /watchlist
DELETE /watchlist/{symbol}
```

The dashboard uses exact ticker lookup for the latest yfinance quote. Tracked
symbols are stored in PostgreSQL and remain available after a page refresh.
Selecting a tracked symbol loads daily OHLCV history for `1mo`, `3mo`, `6mo`,
or `1y`, including server-calculated SMA20, SMA50, and SMA200 series.

### Backtests

```text
POST /backtests
POST /backtests/range
GET  /backtests/{run_id}
```

`POST /backtests` accepts normalized events inline. `POST /backtests/range`
loads previously imported bars using a rule ID and timezone-aware start/end
timestamps.

### Alerts

```text
GET  /alerts
GET  /alerts?rule_id={rule_id}&acknowledged=false
POST /alerts/{alert_id}/acknowledge
```

### Legacy price endpoints

```text
GET  /prices/latest
POST /prices/poll
```

These endpoints remain available during the migration from the original market
data service. New real-time integrations should publish validated OHLCV events to
the Kafka `market-events` topic.

## Development

```bash
# Backend tests
pytest -q

# Frontend production build
npm --prefix frontend run build

# Validate the complete container stack
docker compose -f docker/docker-compose.yml config
```

The test suite includes an end-to-end resume demo that compiles the example
English sentence, stores the rule, imports `examples/nvda_daily.csv`, runs a
range backtest, and verifies the expected high-volume SMA20 breakdown trigger.

Database changes must be introduced through a new Alembic revision. Application
startup deliberately does not call SQLAlchemy `drop_all()` or `create_all()`.

## Project structure

```text
app/
├── api/             FastAPI rule, backtest, alert, and price routes
├── backtesting/     Historical event replay and forward-return metrics
├── compilers/       Natural-language compiler boundary and local compiler
├── domain/          Rule DSL and normalized MarketEvent
├── indicators/      Incremental SMA, EMA, RSI, and volume ratio
├── kafka/           Market-event codec, producer, and live worker
├── models/          SQLAlchemy persistence models
└── services/        Rule, alert, market data, and backtest workflows

frontend/            React + Vite dashboard
migrations/          Alembic schema history
examples/            Importable NVDA demonstration data
docker/              API image and complete Compose stack
tests/               Unit, API, replay-parity, and end-to-end demo tests
```
