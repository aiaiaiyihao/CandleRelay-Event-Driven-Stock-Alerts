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
  marketQuotes: (symbols) => request(`/market/quotes?symbols=${encodeURIComponent(symbols.join(','))}`),
  favorites: () => request('/favorites'),
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
  runBacktest: (ruleId, start, end) => request('/backtests/range', {
    method: 'POST',
    body: JSON.stringify({ rule_id: ruleId, start, end }),
  }),
  alerts: () => request('/alerts?acknowledged=false'),
  acknowledge: (id) => request(`/alerts/${id}/acknowledge`, { method: 'POST' }),
  quote: (symbol) => request(`/prices/latest?symbol=${encodeURIComponent(symbol)}`),
  searchStocks: (query) => request(`/stocks/search?q=${encodeURIComponent(query)}`),
  chart: (symbol, period) => request(`/stocks/${encodeURIComponent(symbol)}/chart?period=${encodeURIComponent(period)}`),
}
