const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `Request failed (${response.status})`)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  me: () => request('/auth/me'),
  register: (identifier, password) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  }),
  login: (identifier, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  marketOverview: (refresh = false) => request(`/market/overview${refresh ? '?refresh=true' : ''}`),
  marketChat: (question, contextSymbol = null) => request('/market/chat', {
    method: 'POST',
    body: JSON.stringify({ question, context_symbol: contextSymbol || undefined }),
  }),
  sectorStocks: (sector, page = 1, sortOrder = 'desc') => request(`/market/sectors/${encodeURIComponent(sector)}/stocks?page=${page}&page_size=10&sort_order=${sortOrder}`),
  marketQuotes: (symbols) => request(`/market/quotes?symbols=${encodeURIComponent(symbols.join(','))}`),
  favorites: () => request('/favorites'),
  favoriteNews: (refresh = false) => request(`/favorites/news${refresh ? '?refresh=true' : ''}`),
  addFavorite: (symbol) => request('/favorites', {
    method: 'POST',
    body: JSON.stringify({ symbol }),
  }),
  removeFavorite: (symbol) => request(`/favorites/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  compile: (text) => request('/rules/compile', {
    method: 'POST',
    body: JSON.stringify({ text, cooldown_seconds: 3600 }),
  }),
  createRule: (name, definition) => request('/rules', {
    method: 'POST',
    body: JSON.stringify({ name, definition }),
  }),
  rules: () => request('/rules'),
  setRuleEnabled: (id, enabled) => request(`/rules/${encodeURIComponent(id)}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  }),
  deleteRule: (id) => request(`/rules/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  runBacktest: (ruleId, start, end) => request('/backtests/range', {
    method: 'POST',
    body: JSON.stringify({ rule_id: ruleId, start, end }),
  }),
  alerts: () => request('/alerts?acknowledged=false'),
  allAlerts: () => request('/alerts'),
  acknowledge: (id) => request(`/alerts/${id}/acknowledge`, { method: 'POST' }),
  quote: (symbol) => request(`/prices/latest?symbol=${encodeURIComponent(symbol)}`),
  searchStocks: (query) => request(`/stocks/search?q=${encodeURIComponent(query)}`),
  stockDetail: (symbol) => request(`/stocks/${encodeURIComponent(symbol)}/detail`),
  stockNews: (symbol, refresh = false) => request(`/stocks/${encodeURIComponent(symbol)}/news${refresh ? '?refresh=true' : ''}`),
  chart: (symbol, period) => request(`/stocks/${encodeURIComponent(symbol)}/chart?period=${encodeURIComponent(period)}`),
}
