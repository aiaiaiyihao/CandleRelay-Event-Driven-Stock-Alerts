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

const CHART_PERIODS = [['30m', '30 MIN'], ['60m', '60 MIN'], ['1d', '1D'], ['1wk', '1W'], ['1mo', '1M'], ['3mo', '3M'], ['1y', '1Y'], ['5y', '5Y'], ['max', 'MAX']]
const CHART_PERIOD_INFO = {
  '30m': '30 minutes · 1-minute points',
  '60m': '60 minutes · 1-minute points',
  '1d': '1 trading day · 1-minute points',
  '1wk': '5 trading days · 10-minute points',
  '1mo': 'about 22 trading days · 4-hour points',
  '3mo': 'about 63 trading days · daily points',
  '1y': 'about 252 trading days · 2-day points',
  '5y': 'about 1,260 trading days · weekly points',
  max: 'full available history · monthly points',
}

const INTRADAY_INTERVALS = new Set(['1m', '5m', '10m', '30m', '60m', '4h'])

function formatChartTimestamp(timestamp, interval, full = false) {
  const value = new Date(timestamp)
  if (INTRADAY_INTERVALS.has(interval)) {
    return value.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: full ? 'numeric' : undefined,
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: full ? 'short' : undefined,
    })
  }
  if (interval === '1mo') {
    return value.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  }
  return value.toLocaleDateString('en-US', {
    month: full ? 'long' : 'short',
    day: 'numeric',
    year: full ? 'numeric' : undefined,
  })
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><span>{payload[0].payload.tooltipDate || label}</span>{payload.map((item) => <div key={item.dataKey}><i style={{ background: item.color }} />{item.name}<strong>${Number(item.value).toFixed(2)}</strong></div>)}</div>
}

function MarketChart({ symbol, displayName, period, setPeriod, data, message, averages, setAverages, compact = false }) {
  return (
    <section className={`stock-chart-panel panel ${compact ? 'compact-chart' : ''}`} id={compact ? 'dashboard-chart' : 'stock-chart'}>
      <div className="chart-header">
        <div className="chart-symbol"><span>SELECTED MARKET</span><h2>{displayName || symbol}</h2>{displayName && displayName !== symbol && <p>{symbol}</p>}</div>
        <div className="chart-controls">
          <div className="interval-switcher" aria-label="Chart period">
            {CHART_PERIODS.map(([value, label]) => <button className={period === value ? 'active' : ''} key={value} onClick={() => setPeriod(value)}>{label}</button>)}
          </div>
          <div className="average-switcher" aria-label="Moving averages">
            {[['sma_20', 'SMA 20'], ['sma_50', 'SMA 50'], ['sma_200', 'SMA 200']].map(([key, label]) => <button className={averages[key] ? `active ${key}` : ''} key={key} onClick={() => setAverages((values) => ({ ...values, [key]: !values[key] }))}><i />{label}</button>)}
          </div>
          <span className="period-info">{CHART_PERIOD_INFO[period]}</span>
        </div>
      </div>
      <div className="interactive-chart">
        {data.length ? <ResponsiveContainer width="100%" height="100%"><ComposedChart data={data} margin={{ top: 16, right: 14, bottom: 4, left: 0 }}>
          <defs><linearGradient id={compact ? 'dashboardPriceFill' : 'favoritePriceFill'} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e76d2d" stopOpacity={0.28} /><stop offset="100%" stopColor="#e76d2d" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid stroke="#252728" vertical={false} />
          <XAxis dataKey="date" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} minTickGap={34} />
          <YAxis domain={['auto', 'auto']} orientation="right" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} width={52} tickFormatter={(value) => `$${Number(value).toFixed(0)}`} />
          <Tooltip content={<ChartTooltip />} />
          <Area type="monotone" dataKey="close" name="Price" stroke="#e9e7e1" strokeWidth={2} fill={`url(#${compact ? 'dashboardPriceFill' : 'favoritePriceFill'})`} dot={false} />
          {averages.sma_20 && <Line type="monotone" dataKey="sma_20" name="SMA 20" stroke="#e76d2d" strokeWidth={1.5} dot={false} />}
          {averages.sma_50 && <Line type="monotone" dataKey="sma_50" name="SMA 50" stroke="#5fd398" strokeWidth={1.4} dot={false} />}
          {averages.sma_200 && <Line type="monotone" dataKey="sma_200" name="SMA 200" stroke="#8887d8" strokeWidth={1.4} dot={false} />}
        </ComposedChart></ResponsiveContainer> : <div className="chart-empty">{message}</div>}
      </div>
    </section>
  )
}

function App() {
  const [page, setPage] = useState(() => {
    const route = window.location.pathname.replace(/^\//, '')
    return ['dashboard', 'favorites', 'rule-studio'].includes(route) ? route : 'dashboard'
  })
  const [user, setUser] = useState(null)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [authIdentifier, setAuthIdentifier] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authMessage, setAuthMessage] = useState('')
  const [text, setText] = useState(SAMPLE_TEXT)
  const [definition, setDefinition] = useState(SAMPLE_DEFINITION)
  const [warning, setWarning] = useState('No timeframe specified - defaulted to daily bars')
  const [ruleId, setRuleId] = useState('')
  const [backtest, setBacktest] = useState(SAMPLE_BACKTEST)
  const [alerts, setAlerts] = useState([])
  const [tracked, setTracked] = useState([])
  const [market, setMarket] = useState({ indexes: [], gainers: [], losers: [], scope: 'US large-cap stocks', market_state: 'CLOSED', updated_at: null })
  const [favoriteQuotes, setFavoriteQuotes] = useState([])
  const [favoriteSort, setFavoriteSort] = useState('change_desc')
  const [search, setSearch] = useState('NVDA')
  const [quote, setQuote] = useState(null)
  const [searchMessage, setSearchMessage] = useState('Enter an exact ticker symbol')
  const [suggestions, setSuggestions] = useState([])
  const [selectedSymbol, setSelectedSymbol] = useState('NVDA')
  const [chartPeriod, setChartPeriod] = useState('3mo')
  const [chartData, setChartData] = useState([])
  const [chartMessage, setChartMessage] = useState('Loading market history…')
  const [visibleAverages, setVisibleAverages] = useState({ sma_20: true, sma_50: true, sma_200: false })
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('Ready to compile')

  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/dashboard')
      setPage('dashboard')
    }
    api.me().then(setUser).catch(() => {})
    api.marketOverview().then(setMarket).catch(() => {})
    api.alerts().then(setAlerts).catch(() => {})
  }, [])

  useEffect(() => {
    const handleNavigation = () => {
      const route = window.location.pathname.replace(/^\//, '')
      setPage(['dashboard', 'favorites', 'rule-studio'].includes(route) ? route : 'dashboard')
    }
    window.addEventListener('popstate', handleNavigation)
    return () => window.removeEventListener('popstate', handleNavigation)
  }, [])

  useEffect(() => {
    if (user) api.favorites().then(setTracked).catch(() => setTracked([]))
    else setTracked([])
  }, [user])

  useEffect(() => {
    if (tracked.length) api.marketQuotes(tracked.map((item) => item.symbol)).then(setFavoriteQuotes).catch(() => setFavoriteQuotes([]))
    else setFavoriteQuotes([])
  }, [tracked])

  useEffect(() => {
    let active = true
    setChartMessage(`Loading ${selectedSymbol} history…`)
    api.chart(selectedSymbol, chartPeriod)
      .then((result) => {
        if (!active) return
        setChartData(result.points.map((point) => ({
          ...point,
          date: formatChartTimestamp(point.timestamp, result.interval),
          tooltipDate: formatChartTimestamp(point.timestamp, result.interval, true),
        })))
        setChartMessage('')
      })
      .catch((error) => {
        if (!active) return
        setChartData([])
        setChartMessage(error.message)
      })
    return () => { active = false }
  }, [selectedSymbol, chartPeriod])

  useEffect(() => {
    const query = search.trim()
    if (!query) {
      setSuggestions([])
      return undefined
    }
    let active = true
    const timer = window.setTimeout(() => {
      api.searchStocks(query)
        .then((results) => active && setSuggestions(results))
        .catch(() => active && setSuggestions([]))
    }, 250)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [search])

  const returns = useMemo(() => backtest?.result_summary?.average_forward_returns || {}, [backtest])
  const marketBySymbol = useMemo(() => Object.fromEntries(
    [...market.indexes, ...market.gainers, ...market.losers, ...favoriteQuotes].map((item) => [item.symbol, item]),
  ), [market, favoriteQuotes])
  const sortedFavorites = useMemo(() => [...tracked].sort((left, right) => {
    const leftMarket = marketBySymbol[left.symbol]
    const rightMarket = marketBySymbol[right.symbol]
    if (favoriteSort === 'symbol') return left.symbol.localeCompare(right.symbol)
    if (favoriteSort === 'price_desc') return (rightMarket?.price || 0) - (leftMarket?.price || 0)
    return (rightMarket?.change_percent ?? -Infinity) - (leftMarket?.change_percent ?? -Infinity)
  }), [tracked, marketBySymbol, favoriteSort])

  function navigate(nextPage) {
    window.history.pushState({}, '', `/${nextPage}`)
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function submitAuth(event) {
    event.preventDefault()
    setBusy('auth')
    setAuthMessage(authMode === 'login' ? 'Signing in…' : 'Creating account…')
    try {
      const result = authMode === 'login'
        ? await api.login(authIdentifier, authPassword)
        : await api.register(authIdentifier, authPassword)
      setUser(result)
      setAuthOpen(false)
      setAuthPassword('')
      setAuthMessage('')
    } catch (error) {
      setAuthMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  async function logout() {
    await api.logout().catch(() => {})
    setUser(null)
  }

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

  async function lookupStock(symbol) {
    if (!symbol) return
    setSuggestions([])
    setBusy('search')
    setQuote(null)
    setSearchMessage(`Looking up ${symbol}…`)
    try {
      const result = await api.quote(symbol)
      setQuote(result)
      setSearch(result.symbol)
      setSelectedSymbol(result.symbol)
      setSearchMessage('Latest quote from yfinance')
    } catch (error) {
      setSearchMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  async function searchStock(event) {
    event.preventDefault()
    await lookupStock(search.trim().toUpperCase())
  }

  function chooseSuggestion(item) {
    setSearch(item.symbol)
    lookupStock(item.symbol)
  }

  async function trackSymbol(symbol) {
    if (!user) {
      setAuthMode('login')
      setAuthOpen(true)
      return
    }
    setBusy(`track-${symbol}`)
    try {
      const item = await api.addFavorite(symbol)
      setTracked((items) => items.some((entry) => entry.symbol === item.symbol) ? items : [...items, item])
      setSelectedSymbol(item.symbol)
      setSearchMessage(`${item.symbol} added to My Favorites`)
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

  function selectMarketSymbol(symbol) {
    setSelectedSymbol(symbol)
    setSearch(symbol)
  }

  async function untrackSymbol(symbol) {
    setBusy(`track-${symbol}`)
    try {
      await api.removeFavorite(symbol)
      setTracked((items) => items.filter((item) => item.symbol !== symbol))
      setSearchMessage(`${symbol} removed from My Favorites`)
    } catch (error) {
      setSearchMessage(error.message)
    } finally {
      setBusy('')
    }
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="https://github.com/aiaiaiyihao/CandleRelay-Event-Driven-Stock-Alerts" target="_blank" rel="noreferrer" aria-label="CandleRelay on GitHub">
          <span className="brand-mark">CR</span>
          <span>CandleRelay</span>
        </a>
        <nav className="product-nav" aria-label="Product navigation">
          {[['dashboard', 'Dashboard'], ['favorites', 'My Favorites'], ['rule-studio', 'Rule Studio']].map(([route, label]) => <a className={page === route ? 'active' : ''} href={`/${route}`} key={route} onClick={(event) => { event.preventDefault(); navigate(route) }}>{label}</a>)}
        </nav>
        <div className="account-actions">
          {user ? (
            <><span>{user.identifier}</span><button onClick={logout}>Sign out</button></>
          ) : (
            <button className="sign-in-button" onClick={() => setAuthOpen(true)}>Sign in / Register</button>
          )}
        </div>
      </header>

      {authOpen && (
        <div className="auth-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setAuthOpen(false)}>
          <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
            <button className="auth-close" onClick={() => setAuthOpen(false)} aria-label="Close account dialog">×</button>
            <p className="eyebrow">PERSONAL CANDLERELAY ACCOUNT</p>
            <h2 id="auth-title">{authMode === 'login' ? 'Welcome back.' : 'Create your account.'}</h2>
            <p className="auth-copy">Use an email address or phone number to keep your market workspace personal.</p>
            <div className="auth-tabs">
              <button className={authMode === 'login' ? 'active' : ''} onClick={() => { setAuthMode('login'); setAuthMessage('') }}>Sign in</button>
              <button className={authMode === 'register' ? 'active' : ''} onClick={() => { setAuthMode('register'); setAuthMessage('') }}>Register</button>
            </div>
            <form onSubmit={submitAuth}>
              <label>Email or phone number<input autoFocus value={authIdentifier} onChange={(event) => setAuthIdentifier(event.target.value)} placeholder="trader@example.com or +14155550100" autoComplete="username" /></label>
              <label>Password<input type="password" minLength="8" value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} placeholder="At least 8 characters" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} /></label>
              {authMessage && <p className="auth-message">{authMessage}</p>}
              <button className="auth-submit" disabled={busy === 'auth'}>{authMode === 'login' ? 'Sign in' : 'Create account'} <span>→</span></button>
            </form>
            {authMode === 'register' && <small>No verification message is sent in this portfolio demo.</small>}
          </section>
        </div>
      )}

      {page === 'rule-studio' && <section className="hero" id="top">
        <div>
          <p className="eyebrow">NATURAL LANGUAGE → EXECUTABLE MARKET LOGIC</p>
          <h1>Forge market noise<br />into <span>precise signals.</span></h1>
        </div>
        <p className="hero-copy">One validated rule engine for historical replay and live Kafka events. Explainable by design, deterministic in production.</p>
      </section>}

      {page === 'dashboard' && <section className="dashboard-section page-surface" id="dashboard">
        <div className="section-intro"><div><p className="eyebrow">US MARKET COMMAND CENTER</p><h2>Market dashboard</h2></div><div className="market-status"><p>Major indexes and today's leading large-cap movers. Select any market to inspect its trend.</p><span className={market.market_state === 'OPEN' ? 'open' : ''}>{market.market_state === 'OPEN' ? 'MARKET OPEN' : 'MARKET CLOSED'}{market.updated_at ? ` · UPDATED ${new Date(market.updated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}` : ''}</span></div></div>
        <div className="index-strip">
          {market.indexes.map((item) => <button key={item.symbol} className={selectedSymbol === item.symbol ? 'selected' : ''} onClick={() => selectMarketSymbol(item.symbol)}><span>{item.name}</span><strong>{item.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong><em className={item.change_percent >= 0 ? 'up' : 'down'}>{item.change_percent >= 0 ? '+' : ''}{item.change_percent.toFixed(2)}%</em></button>)}
        </div>
        <div className="dashboard-grid">
          <div className="mover-panel panel">
            <div className="mover-columns">
              {[['TOP GAINERS', market.gainers, 'up'], ['TOP LOSERS', market.losers, 'down']].map(([title, items, tone]) => <div className="mover-list" key={title}><h3>{title}<span>US LARGE-CAP · TOP 10</span></h3>{items.map((item, index) => <div className={`mover-row ${selectedSymbol === item.symbol ? 'selected' : ''}`} key={item.symbol} onClick={() => selectMarketSymbol(item.symbol)} role="button" tabIndex={0}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item.symbol}</strong><em>${item.price.toFixed(2)}</em><b className={tone}>{item.change_percent >= 0 ? '+' : ''}{item.change_percent.toFixed(2)}%</b><button className={tracked.some((favorite) => favorite.symbol === item.symbol) ? 'star active' : 'star'} onClick={(event) => { event.stopPropagation(); tracked.some((favorite) => favorite.symbol === item.symbol) ? untrackSymbol(item.symbol) : trackSymbol(item.symbol) }} aria-label={`Toggle ${item.symbol} favorite`}>★</button></div>)}</div>)}
            </div>
          </div>
          <MarketChart symbol={selectedSymbol} displayName={marketBySymbol[selectedSymbol]?.name} period={chartPeriod} setPeriod={setChartPeriod} data={chartData} message={chartMessage} averages={visibleAverages} setAverages={setVisibleAverages} compact />
        </div>
      </section>}

      {page === 'favorites' && <>
      <section className="favorites-heading page-surface"><p className="eyebrow">PERSONAL MARKET WORKSPACE</p><h1>My Favorites</h1><p>Search, save, sort, and inspect the stocks that matter to you.</p></section>
      <section className="market-explorer panel" id="favorites">
        <div className="panel-heading">
          <div><span className="step">00</span><h2>Market explorer</h2></div>
          <span className="tag">PRIVATE / SORTABLE / PERSISTENT</span>
        </div>
        <div className="market-grid">
          <div className="stock-search">
            <p className="section-label">FIND A STOCK</p>
            <form onSubmit={searchStock}>
              <span className="search-icon">⌕</span>
              <input value={search} onChange={(event) => setSearch(event.target.value.toUpperCase())} placeholder="AAPL, NVDA, MSFT…" aria-label="Search stock ticker" />
              <button disabled={busy === 'search'}>{busy === 'search' ? 'Searching…' : 'Search quote'}</button>
            </form>
            {suggestions.length > 0 && (
              <div className="stock-suggestions" role="listbox" aria-label="Stock suggestions">
                {suggestions.map((item) => (
                  <button type="button" key={`${item.symbol}-${item.exchange}`} onClick={() => chooseSuggestion(item)} role="option">
                    <strong>{item.symbol}</strong>
                    <span>{item.name}</span>
                    <em>{item.exchange}</em>
                  </button>
                ))}
              </div>
            )}
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
                  ? <button className="tracked-button" onClick={() => untrackSymbol(quote.symbol)}>★ Favorite</button>
                  : <button className="track-button" onClick={() => trackSymbol(quote.symbol)}>☆ Add favorite</button>}
              </div>
            )}
          </div>
          <div className="watchlist">
            <div className="watchlist-title">
              <div><p className="section-label">MY FAVORITES</p><h3>{user ? 'Your private watchlist' : 'Sign in to save stocks'}</h3></div>
              <span>{tracked.length}</span>
            </div>
            <div className="favorite-sort"><span>SORT BY</span><select value={favoriteSort} onChange={(event) => setFavoriteSort(event.target.value)}><option value="change_desc">Daily change</option><option value="price_desc">Price</option><option value="symbol">Symbol</option></select></div>
            {tracked.length === 0 ? (
              <div className="watchlist-empty"><b>NO FAVORITES YET</b><p>{user ? 'Search for a ticker or use a star on the dashboard.' : 'Sign in to create your personal favorites list.'}</p></div>
            ) : (
              <div className="tracked-list">
                {sortedFavorites.map((item) => (
                  <div className={`tracked-row ${selectedSymbol === item.symbol ? 'selected' : ''}`} key={item.symbol} onClick={() => selectTrackedSymbol(item.symbol)} role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && selectTrackedSymbol(item.symbol)}>
                    <span className="favorite-star">★</span>
                    <strong>{item.symbol}</strong>
                    <span>{marketBySymbol[item.symbol] ? `$${marketBySymbol[item.symbol].price.toFixed(2)}` : 'Quote on select'}</span>
                    <time className={(marketBySymbol[item.symbol]?.change_percent || 0) >= 0 ? 'up' : 'down'}>{marketBySymbol[item.symbol] ? `${marketBySymbol[item.symbol].change_percent >= 0 ? '+' : ''}${marketBySymbol[item.symbol].change_percent.toFixed(2)}%` : '—'}</time>
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
          </div>
          <div className="chart-controls">
            <div className="interval-switcher" aria-label="Chart period">
              {CHART_PERIODS.map(([value, label]) => (
                <button className={chartPeriod === value ? 'active' : ''} key={value} onClick={() => setChartPeriod(value)}>{label}</button>
              ))}
            </div>
            <div className="average-switcher" aria-label="Moving averages">
              {[['sma_20', 'SMA 20'], ['sma_50', 'SMA 50'], ['sma_200', 'SMA 200']].map(([key, label]) => (
                <button className={visibleAverages[key] ? `active ${key}` : ''} key={key} onClick={() => setVisibleAverages((values) => ({ ...values, [key]: !values[key] }))}><i />{label}</button>
              ))}
            </div>
            <span className="period-info">{CHART_PERIOD_INFO[chartPeriod]}</span>
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
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="close" name="Price" stroke="#e9e7e1" strokeWidth={2} fill="url(#priceFill)" dot={false} activeDot={{ r: 4, fill: '#e76d2d', stroke: '#0d0f10', strokeWidth: 2 }} />
                {visibleAverages.sma_20 && <Line type="monotone" dataKey="sma_20" name="SMA 20" stroke="#e76d2d" strokeWidth={1.5} dot={false} connectNulls={false} />}
                {visibleAverages.sma_50 && <Line type="monotone" dataKey="sma_50" name="SMA 50" stroke="#5fd398" strokeWidth={1.4} dot={false} connectNulls={false} />}
                {visibleAverages.sma_200 && <Line type="monotone" dataKey="sma_200" name="SMA 200" stroke="#8887d8" strokeWidth={1.4} dot={false} connectNulls={false} />}
              </ComposedChart>
            </ResponsiveContainer>
          ) : <div className="chart-empty">{chartMessage}</div>}
        </div>
      </section>
      </>}

      {page === 'rule-studio' && <>
      <section className="workspace" id="rule-studio">
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
      </>}

      <footer><span>CandleRelay / Engine v1.0</span><span>Same rule. Live and replay.</span><span>FastAPI / Kafka / PostgreSQL</span></footer>
    </main>
  )
}

export default App
