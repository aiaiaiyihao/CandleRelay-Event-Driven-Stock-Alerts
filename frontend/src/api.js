const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
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
  watchlist: () => request('/watchlist'),
  track: (symbol) => request('/watchlist', {
    method: 'POST',
    body: JSON.stringify({ symbol }),
  }),
  untrack: (symbol) => request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
}
