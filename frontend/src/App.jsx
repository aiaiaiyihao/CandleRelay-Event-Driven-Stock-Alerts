import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
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
  const [tracked, setTracked] = useState([])
  const [search, setSearch] = useState('NVDA')
  const [quote, setQuote] = useState(null)
  const [searchMessage, setSearchMessage] = useState('Enter an exact ticker symbol')
  const [selectedSymbol, setSelectedSymbol] = useState('NVDA')
  const [chartRange, setChartRange] = useState('3mo')
  const [chartData, setChartData] = useState([])
  const [chartMessage, setChartMessage] = useState('Loading market history…')
  const [visibleAverages, setVisibleAverages] = useState({ sma_20: true, sma_50: true, sma_200: false })
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('Ready to compile')

  useEffect(() => {
    api.alerts().then(setAlerts).catch(() => {})
    api.watchlist().then(setTracked).catch(() => {})
  }, [])

  useEffect(() => {
    let active = true
    setChartMessage(`Loading ${selectedSymbol} history…`)
    api.chart(selectedSymbol, chartRange)
      .then((result) => {
        if (!active) return
        setChartData(result.points.map((point) => ({
          ...point,
          date: new Date(point.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        })))
        setChartMessage(`${result.points.length} daily bars`)
      })
      .catch((error) => {
        if (!active) return
        setChartData([])
        setChartMessage(error.message)
      })
    return () => { active = false }
  }, [selectedSymbol, chartRange])

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

  async function searchStock(event) {
    event.preventDefault()
    const symbol = search.trim().toUpperCase()
    if (!symbol) return
    setBusy('search')
    setQuote(null)
    setSearchMessage(`Looking up ${symbol}…`)
    try {
      const result = await api.quote(symbol)
      setQuote(result)
      setSearch(result.symbol)
      setSearchMessage('Latest quote from yfinance')
    } catch (error) {
      setSearchMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  async function trackSymbol(symbol) {
    setBusy(`track-${symbol}`)
    try {
      const item = await api.track(symbol)
      setTracked((items) => items.some((entry) => entry.symbol === item.symbol) ? items : [...items, item])
      setSelectedSymbol(item.symbol)
      setSearchMessage(`${item.symbol} added to tracked symbols`)
    } catch (error) {
      setSearchMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  function selectTrackedSymbol(symbol) {
    setSelectedSymbol(symbol)
    setSearch(symbol)
    document.getElementById('stock-chart')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function untrackSymbol(symbol) {
    setBusy(`track-${symbol}`)
    try {
      await api.untrack(symbol)
      setTracked((items) => items.filter((item) => item.symbol !== symbol))
      setSearchMessage(`${symbol} removed from tracked symbols`)
    } catch (error) {
      setSearchMessage(error.message)
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

      <section className="market-explorer panel">
        <div className="panel-heading">
          <div><span className="step">00</span><h2>Market explorer</h2></div>
          <span className="tag">SEARCH / TRACK / MONITOR</span>
        </div>
        <div className="market-grid">
          <div className="stock-search">
            <p className="section-label">FIND A STOCK</p>
            <form onSubmit={searchStock}>
              <span className="search-icon">⌕</span>
              <input value={search} onChange={(event) => setSearch(event.target.value.toUpperCase())} placeholder="AAPL, NVDA, MSFT…" aria-label="Search stock ticker" />
              <button disabled={busy === 'search'}>{busy === 'search' ? 'Searching…' : 'Search quote'}</button>
            </form>
            <p className="search-message">{searchMessage}</p>
            <div className="quick-symbols">
              <span>QUICK SEARCH</span>
              {['NVDA', 'AAPL', 'MSFT', 'TSLA'].map((symbol) => <button key={symbol} onClick={() => setSearch(symbol)}>{symbol}</button>)}
            </div>
            {quote && (
              <div className="quote-result">
                <div><span>{quote.provider}</span><strong>{quote.symbol}</strong></div>
                <strong>${Number(quote.price).toFixed(2)}</strong>
                <time>{new Date(quote.timestamp).toLocaleString()}</time>
                {tracked.some((item) => item.symbol === quote.symbol)
                  ? <button className="tracked-button" onClick={() => untrackSymbol(quote.symbol)}>✓ Tracked</button>
                  : <button className="track-button" onClick={() => trackSymbol(quote.symbol)}>+ Track stock</button>}
              </div>
            )}
          </div>
          <div className="watchlist">
            <div className="watchlist-title">
              <div><p className="section-label">TRACKED SYMBOLS</p><h3>Your market watchlist</h3></div>
              <span>{tracked.length}</span>
            </div>
            {tracked.length === 0 ? (
              <div className="watchlist-empty"><b>NO SYMBOLS TRACKED</b><p>Search for a ticker and add it to your watchlist.</p></div>
            ) : (
              <div className="tracked-list">
                {tracked.map((item) => (
                  <div className={`tracked-row ${selectedSymbol === item.symbol ? 'selected' : ''}`} key={item.symbol} onClick={() => selectTrackedSymbol(item.symbol)} role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && selectTrackedSymbol(item.symbol)}>
                    <span className="tracking-dot" />
                    <strong>{item.symbol}</strong>
                    <span>Rules ready</span>
                    <time>{new Date(item.created_at).toLocaleDateString()}</time>
                    <button aria-label={`Remove ${item.symbol}`} onClick={() => untrackSymbol(item.symbol)} disabled={busy === `track-${item.symbol}`}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="stock-chart-panel panel" id="stock-chart">
        <div className="chart-header">
          <div className="chart-symbol">
            <span>SELECTED MARKET</span>
            <h2>{selectedSymbol}</h2>
            <p>{chartMessage}</p>
          </div>
          <div className="chart-controls">
            <div className="range-switcher" aria-label="Chart range">
              {[['1mo', '1M'], ['3mo', '3M'], ['6mo', '6M'], ['1y', '1Y']].map(([value, label]) => (
                <button className={chartRange === value ? 'active' : ''} key={value} onClick={() => setChartRange(value)}>{label}</button>
              ))}
            </div>
            <div className="average-switcher" aria-label="Moving averages">
              {[['sma_20', 'SMA 20'], ['sma_50', 'SMA 50'], ['sma_200', 'SMA 200']].map(([key, label]) => (
                <button className={visibleAverages[key] ? `active ${key}` : ''} key={key} onClick={() => setVisibleAverages((values) => ({ ...values, [key]: !values[key] }))}><i />{label}</button>
              ))}
            </div>
          </div>
        </div>
        <div className="interactive-chart">
          {chartData.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 16, right: 14, bottom: 4, left: 0 }}>
                <defs>
                  <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#e76d2d" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#e76d2d" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#252728" vertical={false} />
                <XAxis dataKey="date" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} minTickGap={34} />
                <YAxis domain={['auto', 'auto']} orientation="right" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} width={52} tickFormatter={(value) => `$${Number(value).toFixed(0)}`} />
                <Tooltip content={({ active, payload, label }) => active && payload?.length ? <div className="chart-tooltip"><span>{label}</span>{payload.map((item) => <div key={item.dataKey}><i style={{ background: item.color }} />{item.name}<strong>${Number(item.value).toFixed(2)}</strong></div>)}</div> : null} />
                <Area type="monotone" dataKey="close" name="Price" stroke="#e9e7e1" strokeWidth={2} fill="url(#priceFill)" dot={false} activeDot={{ r: 4, fill: '#e76d2d', stroke: '#0d0f10', strokeWidth: 2 }} />
                {visibleAverages.sma_20 && <Line type="monotone" dataKey="sma_20" name="SMA 20" stroke="#e76d2d" strokeWidth={1.5} dot={false} connectNulls={false} />}
                {visibleAverages.sma_50 && <Line type="monotone" dataKey="sma_50" name="SMA 50" stroke="#5fd398" strokeWidth={1.4} dot={false} connectNulls={false} />}
                {visibleAverages.sma_200 && <Line type="monotone" dataKey="sma_200" name="SMA 200" stroke="#8887d8" strokeWidth={1.4} dot={false} connectNulls={false} />}
              </ComposedChart>
            </ResponsiveContainer>
          ) : <div className="chart-empty">{chartMessage}</div>}
        </div>
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
