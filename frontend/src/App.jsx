import { useEffect, useMemo, useState } from 'react'
import { api } from './api'

const SAMPLE_TEXT = 'Alert me when NVDA crosses below SMA20 and volume is more than 2 times the average of the past 20 trading days.'

const SAMPLE_DEFINITION = {
  dsl_version: '1.0',
  symbol: 'NVDA',
  timeframe: '1d',
  conditions: {
    all: [
      {
        left: { type: 'metric', metric: 'price' },
        operator: 'crosses_below',
        right: { type: 'indicator', indicator: 'sma', period: 20 },
      },
      {
        left: { type: 'indicator', indicator: 'volume_ratio', period: 20 },
        operator: '>',
        right: { type: 'value', value: 2 },
      },
    ],
  },
  trigger: 'on_false_to_true',
  cooldown_seconds: 3600,
}

const SAMPLE_BACKTEST = {
  bars_processed: 22,
  trigger_count: 1,
  result_summary: {
    triggers: [{ evaluated_at: '2026-07-22T20:00:00+00:00', entry_price: '120.00000000' }],
    average_forward_returns: { 1: '0.047', 5: '0.118', 20: '0.214' },
  },
}

function Metric({ label, value, tone }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong className={tone || ''}>{value}</strong>
    </div>
  )
}

function Condition({ item, index }) {
  const operand = (side) => {
    if (side.type === 'metric') return side.metric
    if (side.type === 'value') return side.value
    return `${side.indicator}_${side.period}`
  }
  return (
    <div className="condition-row">
      <span className="condition-index">0{index + 1}</span>
      <code>{operand(item.left)}</code>
      <span className="operator">{item.operator.replaceAll('_', ' ')}</span>
      <code>{operand(item.right)}</code>
    </div>
  )
}

function App() {
  const [text, setText] = useState(SAMPLE_TEXT)
  const [definition, setDefinition] = useState(SAMPLE_DEFINITION)
  const [warning, setWarning] = useState('No timeframe specified - defaulted to daily bars')
  const [ruleId, setRuleId] = useState('')
  const [backtest, setBacktest] = useState(SAMPLE_BACKTEST)
  const [alerts, setAlerts] = useState([])
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('Ready to compile')

  useEffect(() => {
    api.alerts().then(setAlerts).catch(() => {})
  }, [])

  const returns = useMemo(() => backtest?.result_summary?.average_forward_returns || {}, [backtest])

  async function compileRule() {
    setBusy('compile')
    setMessage('Compiling and validating DSL…')
    try {
      const result = await api.compile(text)
      setDefinition(result.definition)
      setWarning(result.warnings?.[0] || '')
      setMessage('Rule validated - review before activation')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  async function activateRule() {
    setBusy('activate')
    try {
      const rule = await api.createRule(`${definition.symbol} signal`, definition)
      setRuleId(rule.id)
      setMessage(`Rule v${rule.version} activated`)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  async function runBacktest() {
    if (!ruleId) {
      setMessage('Activate the rule before running a stored-data backtest')
      return
    }
    setBusy('backtest')
    try {
      const result = await api.runBacktest(ruleId, '2026-07-01T00:00:00Z', '2026-07-23T00:00:00Z')
      setBacktest(result)
      setMessage(`Backtest completed - ${result.trigger_count} signal found`)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="SignalForge home">
          <span className="brand-mark">SF</span>
          <span>SignalForge</span>
        </a>
        <div className="system-state"><i /> EVENT STREAM ACTIVE</div>
        <div className="header-meta"><span>NVDA</span><strong>$120.00</strong><em>−14.29%</em></div>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">NATURAL LANGUAGE → EXECUTABLE MARKET LOGIC</p>
          <h1>Forge market noise<br />into <span>precise signals.</span></h1>
        </div>
        <p className="hero-copy">One validated rule engine for historical replay and live Kafka events. Explainable by design, deterministic in production.</p>
      </section>

      <section className="workspace">
        <article className="panel composer">
          <div className="panel-heading">
            <div><span className="step">01</span><h2>Describe your signal</h2></div>
            <span className="tag">NATURAL LANGUAGE</span>
          </div>
          <textarea value={text} onChange={(event) => setText(event.target.value)} aria-label="Natural language trading rule" />
          <div className="composer-footer">
            <span className="status-copy"><i /> {message}</span>
            <button className="primary" onClick={compileRule} disabled={Boolean(busy)}>
              {busy === 'compile' ? 'Forging…' : 'Forge rule'} <span>→</span>
            </button>
          </div>
        </article>

        <article className="panel logic">
          <div className="panel-heading">
            <div><span className="step">02</span><h2>Validated logic</h2></div>
            <span className="valid">✓ DSL v{definition.dsl_version}</span>
          </div>
          <div className="logic-meta">
            <Metric label="SYMBOL" value={definition.symbol} />
            <Metric label="TIMEFRAME" value={definition.timeframe} />
            <Metric label="TRIGGER" value="FALSE → TRUE" />
          </div>
          <div className="condition-list">
            {definition.conditions.all.map((item, index) => <Condition key={index} item={item} index={index} />)}
          </div>
          {warning && <p className="warning">△ {warning}</p>}
          <div className="logic-actions">
            <button className="ghost" onClick={() => navigator.clipboard?.writeText(JSON.stringify(definition, null, 2))}>Copy JSON</button>
            <button className="activate" onClick={activateRule} disabled={Boolean(busy)}>{busy === 'activate' ? 'Activating…' : 'Activate rule'}</button>
          </div>
        </article>
      </section>

      <section className="results">
        <article className="panel backtest-card">
          <div className="panel-heading">
            <div><span className="step">03</span><h2>Historical replay</h2></div>
            <button className="run" onClick={runBacktest} disabled={Boolean(busy)}>{busy === 'backtest' ? 'Running…' : 'Run backtest ↗'}</button>
          </div>
          <div className="metrics-row">
            <Metric label="BARS PROCESSED" value={backtest.bars_processed} />
            <Metric label="SIGNALS FOUND" value={backtest.trigger_count} tone="orange" />
            <Metric label="20-BAR RETURN" value={returns['20'] ? `+${(Number(returns['20']) * 100).toFixed(1)}%` : '—'} tone="green" />
          </div>
          <div className="chart" aria-label="Sample NVDA price chart">
            <div className="grid-line one" /><div className="grid-line two" /><div className="grid-line three" />
            <svg viewBox="0 0 800 180" preserveAspectRatio="none" role="img" aria-label="Price line dropping through moving average">
              <polyline className="sma-line" points="0,126 80,120 160,112 240,104 320,96 400,88 480,80 560,72 640,66 720,61 800,56" />
              <polyline className="price-line" points="0,142 80,126 160,132 240,104 320,112 400,79 480,91 560,53 640,65 700,42 750,48 800,146" />
              <circle cx="800" cy="146" r="7" />
            </svg>
            <span className="signal-label">SIGNAL - JUL 22</span>
          </div>
        </article>

        <aside className="panel alert-card">
          <div className="panel-heading"><div><span className="step">04</span><h2>Live alerts</h2></div><span className="count">{alerts.length || 1}</span></div>
          {(alerts.length ? alerts : [{ id: 'demo', symbol: 'NVDA', market_timestamp: '2026-07-22T20:00:00Z', rule_version: 1 }]).map((alert) => (
            <div className="alert" key={alert.id}>
              <div className="alert-top"><span className="pulse" /><strong>{alert.symbol}</strong><time>{new Date(alert.market_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div>
              <h3>High-volume breakdown</h3>
              <p>Price crossed below SMA20 while volume exceeded the 20-day average by 2×.</p>
              <div><span>RULE v{alert.rule_version}</span>{alert.id !== 'demo' && <button onClick={() => api.acknowledge(alert.id).then(() => setAlerts((items) => items.filter((item) => item.id !== alert.id)))}>Acknowledge</button>}</div>
            </div>
          ))}
          <div className="event-route"><span>KAFKA</span><b>→</b><span>ENGINE</span><b>→</b><span>ALERT</span></div>
        </aside>
      </section>

      <footer><span>SignalForge / Engine v1.0</span><span>Same rule. Live and replay.</span><span>FastAPI / Kafka / PostgreSQL</span></footer>
    </main>
  )
}

export default App
