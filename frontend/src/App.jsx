
import { useState } from 'react'
import './App.css'

function App() {
  const [momentumData, setMomentumData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleTestBackend = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/`);
      const data = await response.json();
      alert(`Backend Status: ${data.status}`);
    } catch (err) {
      setError("Failed to connect to backend: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  const handleCalculateNTF = async () => {
    setLoading(true);
    setError(null);
    try {
      // Dummy data matching the pydantic model example
      const payload = {
        "prices": {
          "BTC": [100, 101, 102, 101, 103, 105, 104, 106, 108, 107],
          "ETH": [200, 202, 201, 203, 205, 204, 206, 208, 209, 210],
          "LTC": [50, 51, 52, 51, 51, 52, 53, 52, 54, 55]
        },
        "lookback_window": 5
      };

      const response = await fetch(`${API_URL}/api/ntf/momentum`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const result = await response.json();
      setMomentumData(result.momentum);
    } catch (err) {
      setError("Failed to calculate momentum: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>Quant Trading Dashboard</h1>
      <div className="card">
        <h2>System Status</h2>
        <button onClick={handleTestBackend} disabled={loading}>
          {loading ? 'Checking...' : 'Check Backend Connectivity'}
        </button>
      </div>

      <div className="card">
        <h2>Network Trend Following (NTF)</h2>
        <p>Calculate Momentum Spillover for BTC, ETH, LTC (Demo Data)</p>
        <button onClick={handleCalculateNTF} disabled={loading}>
          {loading ? 'Calculating...' : 'Run NTF Engine'}
        </button>

        {error && <p className="error">{error}</p>}

        {momentumData && (
          <div className="results">
            <h3>Momentum Results:</h3>
            <ul>
              {Object.entries(momentumData).map(([asset, score]) => (
                <li key={asset}>
                  <strong>{asset}</strong>: {score.toFixed(4)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="card">
        <h2>Online Portfolio Selection (OPS)</h2>
        <p><em>Check the User Manual to implement this form.</em></p>
      </div>
    </div>
  )
}

export default App
