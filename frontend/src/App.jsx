import './App.css'
import {useState, useEffect} from 'react'
import {getAlerts} from './api'

function App() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState([])
  const [error, setError] = useState([])

  useEffect(() => {
    async function fetchAlerts() {
      setError(null)
      try {
        const data = await getAlerts()
        setAlerts(data)
      }
      catch(err) {
        setError(err.message)
      }
      finally {
        setLoading(false)
      }
    }
    fetchAlerts()
  }, [])

  const colunms = alerts.reduce((acc, alert) => {
    const key = '${alert.x} @ ${alert.y}'
    if (!acc[key]) acc[key] = []
    acc[key].push(alert)
    return acc
  }, [])
  return (
    <div className="app">
      <header className="header">
        <h1>IndexPulse</h1>
        </header>

        <main className="dashboard">
         {loading && <p className="status">Loading...</p>}
         {!loading && error && <p className="status">Error: {error}</p>}
         {!loading && !error && alerts.length === 0 && <p className="status">No alerts yet.</p>}


          {Object.entries(colunms).map(([label, items]) => (
            <div key={label} className="column">
              <h2 className="column-title">{label}</h2>
              {items.map(alert => (
                <div key={alert.id} className="alert-card">
                  <p className="alert-title">{alert.title}</p>                  
                  <p className="alert-snippet">{alert.snippet}</p>
                  <a href={alert.link} target="_blank" rel="noreferrer">View Source →</a>
                </div>
              ))}
            </div>
          ))}
        </main>
    </div>
  )
}

export default App
