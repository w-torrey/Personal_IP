const BASE = '/api'

export async function getAlerts() {
    const res = await fetch(`${BASE}/alerts`)
    if (!res.ok) throw new Error("Failed to fetch alerts.")
        return res.json()
}

export async function createWatchlist(x, y) { 
    const res = await fetch(`${BASE}/watchlist`, {
        method: 'POST',
        headers: { 'Content Type': 'application/json'},
        body: JSON.stringify({x, y}),
})
    if (!res.ok) throw new Error("Failed to create watchlist.")
    return res.json()
}

export async function runNow() {
    const res = await fetch(`${BASE}/run-now`, {method: POST})
    if (!res.ok) throw new Error("Failed to run.")
        return res.json()
}