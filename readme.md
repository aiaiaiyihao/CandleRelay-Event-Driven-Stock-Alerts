# SignalForge

SignalForge is an event-driven stock alerting and strategy backtesting platform.
Users describe market conditions in natural language, review the compiled and
validated Rule DSL, and run the same rule against live Kafka events or historical
market bars.

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

## Example rule

Input:

```text
当 NVDA 跌破 SMA20，并且成交量超过过去 20 天平均值的两倍时提醒我。
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

This starts PostgreSQL, Redis, Kafka, the API, and the live rule worker. The API
container applies Alembic migrations before serving traffic.

For manual development without the API and worker containers:

```bash
alembic upgrade head
uvicorn app.main:app --reload
python -m app.kafka.SignalConsumer
```

Swagger is available at <http://localhost:8000/docs>.

Import the included demo bars when running the services manually:

```bash
python scripts/import_market_bars.py examples/nvda_daily.csv \
  --symbol NVDA --timeframe 1d --source demo
```

Configuration:

```text
DATABASE_URL=postgresql://admin:admin@localhost:5432/marketdb
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP=localhost:9092
KAFKA_SIGNAL_GROUP=signalforge-live-rules
```

## API overview

### Compile natural language

```http
POST /rules/compile
Content-Type: application/json

{
  "text": "当 NVDA 跌破 SMA20，并且成交量超过过去 20 天平均值的两倍时提醒我。",
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
pytest -q
```

The test suite includes an end-to-end resume demo that compiles the example
Chinese sentence, stores the rule, imports `examples/nvda_daily.csv`, runs a
range backtest, and verifies the expected high-volume SMA20 breakdown trigger.

Database changes must be introduced through a new Alembic revision. Application
startup deliberately does not call SQLAlchemy `drop_all()` or `create_all()`.
