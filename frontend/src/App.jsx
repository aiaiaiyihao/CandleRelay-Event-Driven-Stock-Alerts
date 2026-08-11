import { useEffect, useMemo, useRef, useState } from 'react'
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

function MoverList({ title, items, tone, page, setPage, selectedSymbol, selectSymbol, previewSymbol, cancelPreview, tracked, trackSymbol, untrackSymbol }) {
  const pageSize = 10
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize))
  const safePage = Math.min(page, pageCount - 1)
  const visibleItems = items.slice(safePage * pageSize, (safePage + 1) * pageSize)
  return (
    <div className="mover-list">
      <h3>{title}<span>TOP 50 · 10 / PAGE</span></h3>
      {visibleItems.map((item, index) => <div className={`mover-row ${selectedSymbol === item.symbol ? 'selected' : ''}`} key={item.symbol} onMouseEnter={() => previewSymbol(item.symbol)} onMouseLeave={cancelPreview} onClick={() => { cancelPreview(); selectSymbol(item.symbol) }} role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && selectSymbol(item.symbol)}><span>{String((safePage * pageSize) + index + 1).padStart(2, '0')}</span><strong>{item.symbol}</strong><em>${item.price.toFixed(2)}</em><b className={tone}>{item.change_percent >= 0 ? '+' : ''}{item.change_percent.toFixed(2)}%</b><button className={tracked.some((favorite) => favorite.symbol === item.symbol) ? 'star active' : 'star'} onClick={(event) => { event.stopPropagation(); cancelPreview(); tracked.some((favorite) => favorite.symbol === item.symbol) ? untrackSymbol(item.symbol) : trackSymbol(item.symbol) }} aria-label={`Toggle ${item.symbol} favorite`}>★</button></div>)}
      <div className="mover-pagination"><button disabled={safePage === 0} onClick={() => setPage(safePage - 1)} aria-label={`Previous ${title.toLowerCase()} page`}>←</button><span>{safePage + 1} / {pageCount}</span><button disabled={safePage >= pageCount - 1} onClick={() => setPage(safePage + 1)} aria-label={`Next ${title.toLowerCase()} page`}>→</button></div>
    </div>
  )
}

function MarketChart({ symbol, displayName, period, setPeriod, data, message, averages, setAverages, compact = false, emphasizeTicker = false }) {
  const [zoomLevel, setZoomLevel] = useState(0)
  const [yStretch, setYStretch] = useState(0)
  const [panOffset, setPanOffset] = useState(0)
  const [panning, setPanning] = useState(false)
  const panStart = useRef(null)
  const zoomRatios = [1, 0.75, 0.5, 0.25, 0.125]
  const yPaddingRatios = [0.3, 0.16, 0.07, 0.02]
  const visibleCount = Math.max(10, Math.ceil(data.length * zoomRatios[zoomLevel]))
  const maximumPan = Math.max(0, data.length - visibleCount)
  const visibleEnd = data.length - panOffset
  const visibleData = useMemo(() => data.slice(Math.max(0, visibleEnd - visibleCount), visibleEnd), [data, visibleCount, visibleEnd])
  const yDomain = useMemo(() => {
    const keys = ['close', ...Object.keys(averages).filter((key) => averages[key])]
    const values = visibleData.flatMap((point) => keys.map((key) => point[key]).filter((value) => Number.isFinite(value)))
    if (!values.length) return ['auto', 'auto']
    const minimum = Math.min(...values)
    const maximum = Math.max(...values)
    const range = Math.max(maximum - minimum, Math.abs(maximum) * 0.01, 1)
    const padding = range * yPaddingRatios[yStretch]
    return [minimum - padding, maximum + padding]
  }, [visibleData, averages, yStretch])

  useEffect(() => {
    setZoomLevel(0)
    setYStretch(0)
    setPanOffset(0)
  }, [symbol, period])

  useEffect(() => {
    setPanOffset((value) => Math.min(value, maximumPan))
  }, [maximumPan])

  function resetChartView() {
    setZoomLevel(0)
    setYStretch(0)
    setPanOffset(0)
  }

  function beginPan(event) {
    if (maximumPan === 0 || event.button !== 0) return
    panStart.current = { x: event.clientX, offset: panOffset, width: event.currentTarget.clientWidth }
    event.currentTarget.setPointerCapture(event.pointerId)
    setPanning(true)
  }

  function movePan(event) {
    if (!panStart.current) return
    const distance = event.clientX - panStart.current.x
    const points = Math.round((distance / panStart.current.width) * visibleCount)
    setPanOffset(Math.max(0, Math.min(maximumPan, panStart.current.offset + points)))
  }

  function endPan(event) {
    if (!panStart.current) return
    panStart.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    setPanning(false)
  }

  return (
    <section className={`stock-chart-panel panel ${compact ? 'compact-chart' : ''}`} id={compact ? 'dashboard-chart' : 'stock-chart'}>
      <div className="chart-header">
        <div className={`chart-symbol ${emphasizeTicker ? 'ticker-emphasis' : ''}`}><span>SELECTED MARKET</span><h2>{emphasizeTicker ? symbol : displayName || symbol}</h2>{displayName && displayName !== symbol && <p>{emphasizeTicker ? displayName : symbol}</p>}</div>
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
      <div className={`interactive-chart ${panning ? 'panning' : ''}`} onPointerDown={beginPan} onPointerMove={movePan} onPointerUp={endPan} onPointerCancel={endPan} onWheel={(event) => { if (!event.ctrlKey && !event.metaKey) return; event.preventDefault(); setZoomLevel((value) => Math.max(0, Math.min(zoomRatios.length - 1, value + (event.deltaY < 0 ? 1 : -1)))) }}>
        <div className="chart-view-controls" aria-label="Chart navigation controls" onPointerDown={(event) => event.stopPropagation()}>
          <span>X {Math.round(1 / zoomRatios[zoomLevel] * 10) / 10}×</span>
          <button disabled={zoomLevel === 0} onClick={() => setZoomLevel((value) => Math.max(0, value - 1))} aria-label="Zoom chart out">−</button>
          <button disabled={zoomLevel === zoomRatios.length - 1} onClick={() => setZoomLevel((value) => Math.min(zoomRatios.length - 1, value + 1))} aria-label="Zoom chart in">+</button>
          <button disabled={panOffset >= maximumPan} onClick={() => setPanOffset((value) => Math.min(maximumPan, value + Math.max(1, Math.round(visibleCount * 0.25))))} aria-label="Pan to older data">←</button>
          <button disabled={panOffset === 0} onClick={() => setPanOffset((value) => Math.max(0, value - Math.max(1, Math.round(visibleCount * 0.25))))} aria-label="Pan to newer data">→</button>
          <span>Y {yStretch + 1}×</span>
          <button disabled={yStretch === 0} onClick={() => setYStretch((value) => Math.max(0, value - 1))} aria-label="Compress price axis">−</button>
          <button disabled={yStretch === yPaddingRatios.length - 1} onClick={() => setYStretch((value) => Math.min(yPaddingRatios.length - 1, value + 1))} aria-label="Stretch price axis">+</button>
          <button className="chart-reset" onClick={resetChartView}>RESET</button>
        </div>
        {visibleData.length ? <ResponsiveContainer width="100%" height="100%"><ComposedChart data={visibleData} margin={{ top: 62, right: 14, bottom: 4, left: 0 }}>
          <defs><linearGradient id={compact ? 'dashboardPriceFill' : 'favoritePriceFill'} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e76d2d" stopOpacity={0.28} /><stop offset="100%" stopColor="#e76d2d" stopOpacity={0} /></linearGradient></defs>
          <CartesianGrid stroke="#252728" vertical={false} />
          <XAxis dataKey="date" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} minTickGap={34} />
          <YAxis domain={yDomain} allowDataOverflow={false} orientation="right" stroke="#5d605c" tick={{ fontSize: 9, fontFamily: 'DM Mono' }} tickLine={false} axisLine={false} width={52} tickFormatter={(value) => `$${Number(value).toFixed(0)}`} />
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
    if (route.startsWith('sectors/')) return 'sector'
    if (route.startsWith('stocks/')) return 'stock'
    return ['dashboard', 'favorites', 'rule-studio'].includes(route) ? route : 'dashboard'
  })
  const [sectorSlug, setSectorSlug] = useState(() => window.location.pathname.startsWith('/sectors/') ? window.location.pathname.split('/')[2] : '')
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
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [tracked, setTracked] = useState([])
  const [market, setMarket] = useState({ indexes: [], gainers: [], losers: [], sectors: [], scope: 'Active US-listed stocks', market_state: 'CLOSED', updated_at: null, data_source: 'yfinance', data_status: 'live' })
  const [moverPages, setMoverPages] = useState({ gainers: 0, losers: 0 })
  const [sectorStocks, setSectorStocks] = useState({ sector: '', page: 1, page_size: 10, total: 0, stocks: [], updated_at: null })
  const [sectorPage, setSectorPage] = useState(1)
  const [sectorSortOrder, setSectorSortOrder] = useState('desc')
  const [stockDetail, setStockDetail] = useState(null)
  const [favoriteQuotes, setFavoriteQuotes] = useState([])
  const [favoriteDetail, setFavoriteDetail] = useState(null)
  const [favoriteNews, setFavoriteNews] = useState([])
  const [favoriteNewsPage, setFavoriteNewsPage] = useState(0)
  const [favoriteSort, setFavoriteSort] = useState('change_desc')
  const [favoritePage, setFavoritePage] = useState(0)
  const [search, setSearch] = useState('')
  const [quote, setQuote] = useState(null)
  const [searchMessage, setSearchMessage] = useState('Enter an exact ticker symbol')
  const [suggestions, setSuggestions] = useState([])
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const [selectedSymbol, setSelectedSymbol] = useState(() => window.location.pathname.startsWith('/stocks/') ? window.location.pathname.split('/')[2].toUpperCase() : 'NVDA')
  const [chartPeriod, setChartPeriod] = useState('3mo')
  const [chartData, setChartData] = useState([])
  const [chartMessage, setChartMessage] = useState('Loading market history…')
  const [visibleAverages, setVisibleAverages] = useState({ sma_20: true, sma_50: true, sma_200: false })
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('Ready to compile')
  const previewTimer = useRef(null)
  const suggestionTimer = useRef(null)

  useEffect(() => {
    if (window.location.pathname === '/') {
      window.history.replaceState({}, '', '/dashboard')
      setPage('dashboard')
    }
    api.me().then(setUser).catch(() => {})
    api.marketOverview().then(setMarket).catch(() => {})
  }, [])

  useEffect(() => {
    if (!user) {
      setAlerts([])
      setNotificationsOpen(false)
      return undefined
    }
    let active = true
    const loadAlerts = () => api.alerts().then((items) => active && setAlerts(items)).catch(() => {})
    loadAlerts()
    const interval = window.setInterval(loadAlerts, 30_000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [user])

  useEffect(() => () => {
    window.clearTimeout(previewTimer.current)
    window.clearTimeout(suggestionTimer.current)
  }, [])

  useEffect(() => {
    const handleNavigation = () => {
      const route = window.location.pathname.replace(/^\//, '')
      if (route.startsWith('sectors/')) {
        setSectorSlug(route.split('/')[1])
        setPage('sector')
      } else if (route.startsWith('stocks/')) {
        setSelectedSymbol(route.split('/')[1].toUpperCase())
        setPage('stock')
      } else {
        setPage(['dashboard', 'favorites', 'rule-studio'].includes(route) ? route : 'dashboard')
      }
    }
    window.addEventListener('popstate', handleNavigation)
    return () => window.removeEventListener('popstate', handleNavigation)
  }, [])

  useEffect(() => {
    if (page !== 'sector' || !sectorSlug) return
    setBusy('sector')
    api.sectorStocks(sectorSlug, sectorPage, sectorSortOrder)
      .then(setSectorStocks)
      .catch(() => setSectorStocks({ sector: sectorSlug, page: sectorPage, page_size: 10, total: 0, stocks: [], updated_at: null }))
      .finally(() => setBusy(''))
  }, [page, sectorSlug, sectorPage, sectorSortOrder])

  useEffect(() => {
    if (page !== 'stock' || !selectedSymbol) return
    setBusy('stock-detail')
    setStockDetail(null)
    api.stockDetail(selectedSymbol)
      .then(setStockDetail)
      .catch(() => setStockDetail(null))
      .finally(() => setBusy(''))
  }, [page, selectedSymbol])

  useEffect(() => {
    if (user) api.favorites().then(setTracked).catch(() => setTracked([]))
    else setTracked([])
  }, [user])

  useEffect(() => {
    if (tracked.length) api.marketQuotes(tracked.map((item) => item.symbol)).then(setFavoriteQuotes).catch(() => setFavoriteQuotes([]))
    else setFavoriteQuotes([])
  }, [tracked])

  useEffect(() => {
    if (page !== 'favorites' || !selectedSymbol) return undefined
    let active = true
    setFavoriteDetail(null)
    api.stockDetail(selectedSymbol)
      .then((result) => active && setFavoriteDetail(result))
      .catch(() => active && setFavoriteDetail(null))
    return () => { active = false }
  }, [page, selectedSymbol])

  useEffect(() => {
    setFavoriteNewsPage(0)
    if (page === 'favorites' && user && tracked.length) api.favoriteNews().then(setFavoriteNews).catch(() => setFavoriteNews([]))
    else setFavoriteNews([])
  }, [page, user, tracked])

  useEffect(() => {
    if (page === 'favorites' && tracked.length && !tracked.some((item) => item.symbol === selectedSymbol)) {
      setSelectedSymbol(tracked[0].symbol)
      setChartPeriod('1d')
    }
  }, [page, tracked, selectedSymbol])

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
    if (!query || !suggestionsOpen) {
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
  }, [search, suggestionsOpen])

  const returns = useMemo(() => backtest?.result_summary?.average_forward_returns || {}, [backtest])
  const marketBySymbol = useMemo(() => (
    [...market.indexes, ...market.gainers, ...market.losers, ...favoriteQuotes].reduce((items, item) => {
      const previous = items[item.symbol]
      const resolvedName = item.name && item.name !== item.symbol ? item.name : previous?.name
      items[item.symbol] = { ...previous, ...item, name: resolvedName || item.symbol }
      return items
    }, {})
  ), [market, favoriteQuotes])
  const rankedSectors = useMemo(
    () => [...market.sectors].sort((left, right) => (right.change_percent ?? -Infinity) - (left.change_percent ?? -Infinity)),
    [market.sectors],
  )
  const sortedFavorites = useMemo(() => [...tracked].sort((left, right) => {
    const leftMarket = marketBySymbol[left.symbol]
    const rightMarket = marketBySymbol[right.symbol]
    if (favoriteSort === 'symbol') return left.symbol.localeCompare(right.symbol)
    if (favoriteSort === 'price_desc') return (rightMarket?.price || 0) - (leftMarket?.price || 0)
    return (rightMarket?.change_percent ?? -Infinity) - (leftMarket?.change_percent ?? -Infinity)
  }), [tracked, marketBySymbol, favoriteSort])
  const favoritePageCount = Math.max(1, Math.ceil(sortedFavorites.length / 10))
  const visibleFavorites = sortedFavorites.slice(favoritePage * 10, (favoritePage + 1) * 10)
  const sortedFavoriteNews = useMemo(
    () => [...favoriteNews].sort((left, right) => new Date(right.published_at || 0) - new Date(left.published_at || 0)),
    [favoriteNews],
  )
  const favoriteNewsPageCount = Math.max(1, Math.ceil(sortedFavoriteNews.length / 10))
  const visibleFavoriteNews = sortedFavoriteNews.slice(favoriteNewsPage * 10, (favoriteNewsPage + 1) * 10)

  useEffect(() => {
    setFavoritePage((current) => Math.min(current, favoritePageCount - 1))
  }, [favoritePageCount])

  useEffect(() => {
    setFavoriteNewsPage((current) => Math.min(current, favoriteNewsPageCount - 1))
  }, [favoriteNewsPageCount])

  async function refreshMarket() {
    setBusy('market-refresh')
    try {
      setMarket(await api.marketOverview(true))
      setMoverPages({ gainers: 0, losers: 0 })
    } finally {
      setBusy('')
    }
  }

  function navigate(nextPage) {
    window.history.pushState({}, '', `/${nextPage}`)
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function navigateSector(slug) {
    window.history.pushState({}, '', `/sectors/${slug}`)
    setSectorSlug(slug)
    setSectorPage(1)
    setPage('sector')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function navigateStock(symbol) {
    const normalized = symbol.toUpperCase()
    window.history.pushState({}, '', `/stocks/${normalized}`)
    setSelectedSymbol(normalized)
    setSearch(normalized)
    setPage('stock')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function previewSymbolLater(symbol) {
    window.clearTimeout(previewTimer.current)
    previewTimer.current = window.setTimeout(() => {
      setSelectedSymbol(symbol.toUpperCase())
    }, 400)
  }

  function cancelSymbolPreview() {
    window.clearTimeout(previewTimer.current)
  }

  function createAlertForStock(symbol) {
    setText(`Alert me when ${symbol} crosses below SMA20 and volume is more than 2 times the average of the past 20 trading days.`)
    navigate('rule-studio')
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
    if (!user) {
      setAuthMode('login')
      setAuthOpen(true)
      setMessage('Sign in before activating a personal alert')
      return
    }
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
    setSuggestionsOpen(false)
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
    setSuggestionsOpen(false)
    setSearch(item.symbol)
    lookupStock(item.symbol)
  }

  function updateStockSearch(value) {
    setSearch(value.toUpperCase())
    setSuggestionsOpen(Boolean(value.trim()))
    window.clearTimeout(suggestionTimer.current)
    suggestionTimer.current = window.setTimeout(() => {
      setSuggestionsOpen(false)
      setSuggestions([])
    }, 3000)
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
    cancelSymbolPreview()
    navigateStock(symbol)
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
            <><span>{user.identifier}</span><div className="notification-center"><button className="notification-trigger" onClick={() => setNotificationsOpen((value) => !value)} aria-label={`${alerts.length} unread alerts`} aria-expanded={notificationsOpen}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>{alerts.length > 0 && <b>{alerts.length > 99 ? '99+' : alerts.length}</b>}</button>{notificationsOpen && <div className="notification-panel"><div className="notification-heading"><strong>ALERTS</strong><span>{alerts.length} UNREAD</span></div><div className="notification-list">{alerts.length ? alerts.slice(0, 8).map((alert) => <article key={alert.id}><button onClick={() => { setSelectedSymbol(alert.symbol); navigate('rule-studio'); setNotificationsOpen(false) }}><strong>{alert.symbol}</strong><span>Rule v{alert.rule_version} triggered</span><time>{new Date(alert.market_timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</time></button><button className="notification-read" onClick={() => api.acknowledge(alert.id).then(() => setAlerts((items) => items.filter((item) => item.id !== alert.id)))} aria-label={`Mark ${alert.symbol} alert as read`}>×</button></article>) : <div className="notification-empty">NO NEW ALERTS</div>}</div></div>}</div><button onClick={logout}>Sign out</button></>
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
        <div className="section-intro"><div><p className="eyebrow">US MARKET COMMAND CENTER</p><h2>Market dashboard</h2></div><div className="market-status"><p>Major indexes and today's leading active US-listed stocks. Select any market to inspect its trend.</p><div><span className={market.market_state === 'OPEN' ? 'open' : ''}>{market.market_state === 'OPEN' ? 'MARKET OPEN' : 'MARKET CLOSED'}{market.updated_at ? ` · UPDATED ${new Date(market.updated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}` : ''}</span><span className={`market-source ${market.data_status}`}>{market.data_status === 'stale' ? 'REDIS CACHED DATA' : market.data_status === 'fallback' ? 'ALPHA VANTAGE · TOP 20' : 'YFINANCE'}</span><button onClick={refreshMarket} disabled={busy === 'market-refresh'}>{busy === 'market-refresh' ? 'REFRESHING…' : '↻ REFRESH'}</button></div></div></div>
        <div className="index-strip">
          {market.indexes.map((item) => <button key={item.symbol} className={selectedSymbol === item.symbol ? 'selected' : ''} onClick={() => selectMarketSymbol(item.symbol)}><span>{item.name}</span><strong>{item.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong><em className={item.change_percent >= 0 ? 'up' : 'down'}>{item.change_percent >= 0 ? '+' : ''}{item.change_percent.toFixed(2)}%</em></button>)}
        </div>
        <div className="dashboard-grid">
          <div className="mover-panel panel">
            <div className="mover-columns">
              <MoverList title="TOP GAINERS" items={market.gainers} tone="up" page={moverPages.gainers} setPage={(nextPage) => setMoverPages((pages) => ({ ...pages, gainers: nextPage }))} selectedSymbol={selectedSymbol} selectSymbol={navigateStock} previewSymbol={previewSymbolLater} cancelPreview={cancelSymbolPreview} tracked={tracked} trackSymbol={trackSymbol} untrackSymbol={untrackSymbol} />
              <MoverList title="TOP LOSERS" items={market.losers} tone="down" page={moverPages.losers} setPage={(nextPage) => setMoverPages((pages) => ({ ...pages, losers: nextPage }))} selectedSymbol={selectedSymbol} selectSymbol={navigateStock} previewSymbol={previewSymbolLater} cancelPreview={cancelSymbolPreview} tracked={tracked} trackSymbol={trackSymbol} untrackSymbol={untrackSymbol} />
            </div>
          </div>
          <MarketChart symbol={selectedSymbol} displayName={marketBySymbol[selectedSymbol]?.name} period={chartPeriod} setPeriod={setChartPeriod} data={chartData} message={chartMessage} averages={visibleAverages} setAverages={setVisibleAverages} compact />
        </div>
        <section className="sector-panel panel">
          <div className="sector-heading"><div><p className="eyebrow">SECTOR ETF PROXY</p><h3>Sector performance</h3></div><span>RANKED HIGH TO LOW · CLICK TO EXPLORE</span></div>
          <div className="sector-grid">{rankedSectors.map((sector, index) => <button key={sector.slug} onClick={() => navigateSector(sector.slug)}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{sector.name}</strong><small>{sector.symbol}</small></div><b className={sector.change_percent >= 0 ? 'up' : 'down'}>{sector.change_percent >= 0 ? '+' : ''}{sector.change_percent.toFixed(2)}%</b></button>)}</div>
        </section>
      </section>}

      {page === 'sector' && <section className="sector-page page-surface">
        <button className="back-link" onClick={() => navigate('dashboard')}>← BACK TO DASHBOARD</button>
        <div className="section-intro"><div><p className="eyebrow">SECTOR CONSTITUENTS</p><h2>{sectorStocks.sector || sectorSlug.replaceAll('-', ' ')}</h2></div><div className="market-status"><p>Active US-listed stocks in this sector, ranked by daily percentage change.</p>{sectorStocks.updated_at && <span>UPDATED {new Date(sectorStocks.updated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>}<div className="sector-sort"><span>SORT</span><button onClick={() => { setSectorSortOrder((order) => order === 'desc' ? 'asc' : 'desc'); setSectorPage(1) }}>{sectorSortOrder === 'desc' ? 'HIGH TO LOW ↓' : 'LOW TO HIGH ↑'}</button></div></div></div>
        <div className="sector-stock-table panel">
          <div className="sector-stock-head"><span>RANK</span><span>SYMBOL</span><span>COMPANY</span><span>PRICE</span><span>DAILY CHANGE</span></div>
          {busy === 'sector' ? <div className="sector-empty">LOADING SECTOR STOCKS…</div> : sectorStocks.stocks.map((stock, index) => <button key={stock.symbol} onClick={() => navigateStock(stock.symbol)}><span>{String(((sectorPage - 1) * 10) + index + 1).padStart(2, '0')}</span><strong>{stock.symbol}</strong><em>{stock.name}</em><span>${stock.price.toFixed(2)}</span><b className={stock.change_percent >= 0 ? 'up' : 'down'}>{stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%</b></button>)}
          {!sectorStocks.stocks.length && busy !== 'sector' && <div className="sector-empty">NO STOCKS AVAILABLE</div>}
          <div className="sector-pagination"><button disabled={sectorPage === 1 || busy === 'sector'} onClick={() => setSectorPage((value) => value - 1)}>← PREVIOUS</button><span>PAGE {sectorPage} / {Math.max(1, Math.ceil(sectorStocks.total / 10))} · {sectorStocks.total} STOCKS</span><button disabled={sectorPage >= Math.ceil(sectorStocks.total / 10) || busy === 'sector'} onClick={() => setSectorPage((value) => value + 1)}>NEXT →</button></div>
        </div>
      </section>}

      {page === 'stock' && <section className="stock-detail-page page-surface">
        <button className="back-link" onClick={() => window.history.length > 1 ? window.history.back() : navigate('dashboard')}>← BACK</button>
        {stockDetail ? <>
          <div className="stock-detail-grid">
          <section className="stock-summary panel">
            <div className="stock-identity"><div><p className="eyebrow">{stockDetail.exchange || 'US MARKET'} · {stockDetail.currency || 'USD'}</p><h1>{stockDetail.symbol}</h1><h2>{stockDetail.name}</h2><p>{[stockDetail.sector, stockDetail.industry].filter(Boolean).join(' · ')}</p></div><div className="stock-price"><strong>${stockDetail.price.toFixed(2)}</strong><span className={(stockDetail.change_percent || 0) >= 0 ? 'up' : 'down'}>{stockDetail.change_percent >= 0 ? '+' : ''}{stockDetail.change?.toFixed(2)} ({stockDetail.change_percent?.toFixed(2)}%)</span>{Math.abs(stockDetail.change_percent || 0) >= 50 && <em>EXTREME MOVE · VERIFY QUOTE</em>}<small>{stockDetail.market_state || 'MARKET DATA'}{stockDetail.updated_at ? ` · UPDATED ${new Date(stockDetail.updated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}` : ''}</small></div></div>
            <div className="stock-actions"><button className={tracked.some((item) => item.symbol === stockDetail.symbol) ? 'active' : ''} onClick={() => tracked.some((item) => item.symbol === stockDetail.symbol) ? untrackSymbol(stockDetail.symbol) : trackSymbol(stockDetail.symbol)}>{tracked.some((item) => item.symbol === stockDetail.symbol) ? '★ IN FAVORITES' : '☆ ADD TO FAVORITES'}</button><button className="primary" onClick={() => createAlertForStock(stockDetail.symbol)}>CREATE ALERT →</button></div>
            <div className="stock-stats">{[
              ['OPEN', stockDetail.open, 'price'], ['PREVIOUS CLOSE', stockDetail.previous_close, 'price'], ['DAY HIGH', stockDetail.day_high, 'price'], ['DAY LOW', stockDetail.day_low, 'price'], ['VOLUME', stockDetail.volume, 'number'], ['MARKET CAP', stockDetail.market_cap, 'compact'], ['52W HIGH', stockDetail.fifty_two_week_high, 'price'], ['52W LOW', stockDetail.fifty_two_week_low, 'price'],
            ].map(([label, value, format]) => <div key={label}><span>{label}</span><strong>{value == null ? '—' : format === 'price' ? `$${Number(value).toFixed(2)}` : format === 'compact' ? Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(value) : Number(value).toLocaleString()}</strong></div>)}</div>
          </section>
          <aside className="stock-news panel">
            <div className="stock-news-heading"><div><p className="eyebrow">LATEST COMPANY COVERAGE</p><h2>Major News</h2></div><span>UP TO 5</span></div>
            <div className="stock-news-list">
              {stockDetail.news?.length ? stockDetail.news.map((item) => <a key={`${item.url}-${item.title}`} href={item.url} target="_blank" rel="noreferrer"><strong>{item.title}</strong><span>{item.publisher}{item.published_at ? ` · ${new Date(item.published_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}` : ''}</span></a>) : <div className="stock-news-empty">NO RECENT NEWS AVAILABLE</div>}
            </div>
          </aside>
          </div>
          <MarketChart symbol={selectedSymbol} displayName={stockDetail.name} period={chartPeriod} setPeriod={setChartPeriod} data={chartData} message={chartMessage} averages={visibleAverages} setAverages={setVisibleAverages} />
        </> : <div className="stock-detail-loading panel">{busy === 'stock-detail' ? 'LOADING STOCK DETAILS…' : 'STOCK DETAILS UNAVAILABLE'}</div>}
      </section>}

      {page === 'favorites' && <>
      <section className="favorites-heading page-surface">
        <div><p className="eyebrow">PERSONAL MARKET WORKSPACE</p><h1>My Favorites</h1><p>Search, save, sort, and inspect the stocks that matter to you.</p></div>
        <div className="favorites-search stock-search">
          <p className="section-label">FIND A STOCK</p>
          <form onSubmit={searchStock}><span className="search-icon">⌕</span><input value={search} onChange={(event) => updateStockSearch(event.target.value)} placeholder="AAPL, NVDA, MSFT…" aria-label="Search stock ticker" /><button disabled={busy === 'search'}>{busy === 'search' ? 'Searching…' : 'Search'}</button></form>
          {suggestionsOpen && suggestions.length > 0 && <div className="stock-suggestions" role="listbox" aria-label="Stock suggestions" onMouseLeave={() => { setSuggestionsOpen(false); setSuggestions([]) }}>{suggestions.map((item) => <button type="button" key={`${item.symbol}-${item.exchange}`} onClick={() => chooseSuggestion(item)} role="option"><strong>{item.symbol}</strong><span>{item.name}</span><em>{item.exchange}</em></button>)}</div>}
          <div className="favorites-search-status"><span>{searchMessage}</span>{quote && (tracked.some((item) => item.symbol === quote.symbol) ? <button className="tracked-button" onClick={() => untrackSymbol(quote.symbol)}>★ FAVORITE</button> : <button className="track-button" onClick={() => trackSymbol(quote.symbol)}>☆ ADD FAVORITE</button>)}</div>
        </div>
      </section>
      <section className="favorites-workspace" id="favorites">
          <div className="watchlist panel">
            <div className="watchlist-title">
              <div><p className="section-label">MY FAVORITES</p><h3>{user ? 'Your private watchlist' : 'Sign in to save stocks'}</h3></div>
              <span>{tracked.length}</span>
            </div>
            <div className="favorite-sort"><span>SORT BY</span><select value={favoriteSort} onChange={(event) => { setFavoriteSort(event.target.value); setFavoritePage(0) }}><option value="change_desc">Daily change</option><option value="price_desc">Price</option><option value="symbol">Symbol</option></select></div>
            {tracked.length === 0 ? (
              <div className="watchlist-empty"><b>NO FAVORITES YET</b><p>{user ? 'Search for a ticker or use a star on the dashboard.' : 'Sign in to create your personal favorites list.'}</p></div>
            ) : (
              <><div className="tracked-list">
                {visibleFavorites.map((item) => (
                  <div className={`tracked-row ${selectedSymbol === item.symbol ? 'selected' : ''}`} key={item.symbol} onMouseEnter={() => previewSymbolLater(item.symbol)} onMouseLeave={cancelSymbolPreview} onClick={() => selectTrackedSymbol(item.symbol)} role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && selectTrackedSymbol(item.symbol)}>
                    <span className="favorite-star">★</span>
                    <strong>{item.symbol}</strong>
                    <span>{marketBySymbol[item.symbol] ? `$${marketBySymbol[item.symbol].price.toFixed(2)}` : 'Quote on select'}</span>
                    <time className={(marketBySymbol[item.symbol]?.change_percent || 0) >= 0 ? 'up' : 'down'}>{marketBySymbol[item.symbol] ? `${marketBySymbol[item.symbol].change_percent >= 0 ? '+' : ''}${marketBySymbol[item.symbol].change_percent.toFixed(2)}%` : '—'}</time>
                    <button aria-label={`Remove ${item.symbol}`} onClick={(event) => { event.stopPropagation(); cancelSymbolPreview(); untrackSymbol(item.symbol) }} disabled={busy === `track-${item.symbol}`}>×</button>
                  </div>
                ))}
              </div><div className="favorite-pagination"><button disabled={favoritePage === 0} onClick={() => setFavoritePage((value) => value - 1)}>←</button><span>{favoritePage + 1} / {favoritePageCount}</span><button disabled={favoritePage >= favoritePageCount - 1} onClick={() => setFavoritePage((value) => value + 1)}>→</button></div></>
            )}
          </div>
          <div className="favorite-chart-stack">
            <MarketChart symbol={selectedSymbol} displayName={favoriteDetail?.name || marketBySymbol[selectedSymbol]?.name} period={chartPeriod} setPeriod={setChartPeriod} data={chartData} message={chartMessage} averages={visibleAverages} setAverages={setVisibleAverages} compact emphasizeTicker />
            <div className="favorite-market-stats panel">{[
              ['OPEN', favoriteDetail?.open, 'price'], ['PREVIOUS CLOSE', favoriteDetail?.previous_close, 'price'], ['DAY HIGH', favoriteDetail?.day_high, 'price'], ['DAY LOW', favoriteDetail?.day_low, 'price'], ['VOLUME', favoriteDetail?.volume, 'number'], ['MARKET CAP', favoriteDetail?.market_cap, 'compact'], ['52W HIGH', favoriteDetail?.fifty_two_week_high, 'price'], ['52W LOW', favoriteDetail?.fifty_two_week_low, 'price'],
            ].map(([label, value, format]) => <div key={label}><span>{label}</span><strong>{value == null ? '—' : format === 'price' ? `$${Number(value).toFixed(2)}` : format === 'compact' ? Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(value) : Number(value).toLocaleString()}</strong></div>)}</div>
          </div>
      </section>
      <section className="favorite-news panel">
        <div className="favorite-news-heading"><div><p className="eyebrow">YOUR WATCHLIST · LATEST COVERAGE</p><h2>Favorites News</h2></div><span>{favoriteNews.length} STORIES</span></div>
        <div className="favorite-news-grid">
          {visibleFavoriteNews.length ? visibleFavoriteNews.map((item) => <a key={`${item.symbol}-${item.url}`} href={item.url} target="_blank" rel="noreferrer"><span>{item.symbol}</span><strong>{item.title}</strong><small>{item.publisher}{item.published_at ? ` · ${new Date(item.published_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}` : ''}</small></a>) : <div className="favorite-news-empty">{tracked.length ? 'NO RECENT NEWS AVAILABLE' : 'ADD FAVORITES TO BUILD YOUR NEWS FEED'}</div>}
        </div>
        {sortedFavoriteNews.length > 0 && <div className="favorite-news-pagination"><button disabled={favoriteNewsPage === 0} onClick={() => setFavoriteNewsPage((value) => value - 1)}>← PREVIOUS</button><span>PAGE {favoriteNewsPage + 1} / {favoriteNewsPageCount} · 10 PER PAGE</span><button disabled={favoriteNewsPage >= favoriteNewsPageCount - 1} onClick={() => setFavoriteNewsPage((value) => value + 1)}>NEXT →</button></div>}
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
