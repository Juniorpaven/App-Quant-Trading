
import { useState } from 'react'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [status, setStatus] = useState("");

  // State NTF
  const [ntfTickers, setNtfTickers] = useState("BTC-USD, ETH-USD, LTC-USD");
  const [ntfLookback, setNtfLookback] = useState(20);
  const [ntfResult, setNtfResult] = useState(null);
  const [ntfMissing, setNtfMissing] = useState([]);
  const [loadingNTF, setLoadingNTF] = useState(false);

  // State OPS
  const [opsTickers, setOpsTickers] = useState("AAPL, MSFT, GOOGL, AMZN");
  const [opsEta, setOpsEta] = useState(0.05);
  const [opsLookbacks, setOpsLookbacks] = useState("20, 60, 120");
  const [opsMaxWeight, setOpsMaxWeight] = useState(1.0);
  const [opsResult, setOpsResult] = useState(null);
  const [loadingOPS, setLoadingOPS] = useState(false);

  // State Backtest
  const [backtestResult, setBacktestResult] = useState(null);
  const [loadingBacktest, setLoadingBacktest] = useState(false);

  // State AI
  const [aiTicker, setAiTicker] = useState("HPG.VN");
  const [aiResult, setAiResult] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);

  // Handlers
  const checkBackend = async () => {
    try {
      const res = await axios.get(`${API_URL}/`);
      setStatus(res.data.status);
    } catch (err) {
      setStatus("Error connecting to backend");
      console.error(err);
    }
  };

  const runNTF = async () => {
    setLoadingNTF(true);
    setNtfResult(null);
    try {
      const res = await axios.post(`${API_URL}/api/run-ntf`, {
        tickers: ntfTickers,
        lookback: Number(ntfLookback)
      });
      setNtfResult(res.data.data);
      setNtfMissing(res.data.missing || []);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Lỗi kết nối Backend/Vercel";
      alert(`NTF Error: ${errorMsg}`);
    }
    setLoadingNTF(false);
  };

  const runOPS = async () => {
    setLoadingOPS(true);
    setOpsResult(null);
    try {
      const res = await axios.post(`${API_URL}/api/run-ops`, {
        tickers: opsTickers,
        eta: Number(opsEta),
        lookbacks: opsLookbacks
      });
      setOpsResult(res.data.weights);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Lỗi kết nối Backend/Vercel";
      alert(`OPS Error: ${errorMsg}`);
    }
    setLoadingOPS(false);
  };

  const runBacktest = async () => {
    setLoadingBacktest(true);
    setBacktestResult(null);
    try {
      const res = await axios.post(`${API_URL}/api/backtest`, {
        tickers: opsTickers,
        eta: Number(opsEta),
        max_weight: Number(opsMaxWeight),
        period: "1y"
      });
      setBacktestResult(res.data);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Lỗi Backtest!";
      alert(`Backtest Error: ${errorMsg}`);
    }
    setLoadingBacktest(false);
  };

  const askAI = async () => {
    setLoadingAI(true);
    setAiResult(null);
    try {
      const res = await axios.post(`${API_URL}/api/ask-ai`, { ticker: aiTicker });
      setAiResult(res.data);
    } catch (err) {
      alert("Lỗi AI: " + (err.response?.data?.detail || err.message));
    }
    setLoadingAI(false);
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: 'So sánh Hiệu suất Đầu tư (1 Năm qua)' },
    },
    scales: {
      x: { ticks: { maxTicksLimit: 10 } }
    }
  };

  const chartData = backtestResult ? {
    labels: backtestResult.chart_data.dates,
    datasets: [
      {
        label: 'Thuật toán OPS (AI)',
        data: backtestResult.chart_data.strategy,
        borderColor: '#00e676',
        backgroundColor: 'rgba(0, 230, 118, 0.5)',
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: 'Mua & Giữ (Benchmark)',
        data: backtestResult.chart_data.benchmark,
        borderColor: '#ff1744',
        backgroundColor: 'rgba(255, 23, 68, 0.5)',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [5, 5],
      },
    ],
  } : null;

  return (
    <div style={{ padding: "10px 20px", fontFamily: "Arial, sans-serif", maxWidth: "100%", margin: "0 auto", backgroundColor: "#1e1e1e", color: "#e0e0e0", minHeight: "100vh", boxSizing: "border-box" }}>
      <h1 style={{ color: "#646cff", textAlign: "center", marginBottom: "20px", fontSize: "1.5rem" }}>Quant Trading Dashboard 3.0 (Ultimate)</h1>

      <div style={gridContainerStyle}>

        {/* COLUMN 1: MARKET SCAN (NTF) */}
        <div style={columnStyle}>
          <div style={{ ...cardStyle, height: "100%" }}>
            <h2>🌐 Network Trend Following</h2>
            <p style={{ fontSize: "0.85em", color: "#aaa" }}>Market Momentum Scanner</p>

            <div style={inputGroup}>
              <label>Tickers:</label>
              <textarea
                value={ntfTickers}
                onChange={(e) => setNtfTickers(e.target.value)}
                style={{ ...inputStyle, resize: "vertical", minHeight: "80px", fontSize: "14px" }}
                rows={4}
              />
            </div>
            <div style={inputGroup}>
              <label>Lookback (days):</label>
              <input
                type="number"
                value={ntfLookback}
                onChange={(e) => setNtfLookback(e.target.value)}
                style={inputStyle}
              />
            </div>

            <button onClick={runNTF} style={btnStyle} disabled={loadingNTF}>
              {loadingNTF ? "Scanning..." : "Run NTF Analysis"}
            </button>

            {ntfResult && (
              <div style={resultBox}>
                {ntfMissing && ntfMissing.length > 0 && (
                  <div style={{ marginBottom: "10px", padding: "8px", backgroundColor: "#3a2a2a", borderLeft: "3px solid #f44336", color: "#ff8a80", fontSize: "13px" }}>
                    ⚠️ Missing: {ntfMissing.join(", ")}
                  </div>
                )}

                <h3 style={{ fontSize: "16px", marginTop: 0 }}>Momentum Scores:</h3>
                <ul style={{ paddingLeft: "20px", margin: "10px 0" }}>
                  {Object.entries(ntfResult)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, val]) => (
                      <li key={key} style={{ marginBottom: "3px", fontSize: "14px" }}>
                        <strong>{key}:</strong> <span style={{ color: val > 0 ? "#00e676" : "#ff1744" }}>{val}</span>
                      </li>
                    ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* COLUMN 2: STRATEGY CONFIG (AI + OPS INPUTS) */}
        <div style={columnStyle}>

          {/* AI ORACLE */}
          <div style={{ ...cardStyle, borderLeft: "4px solid #e91e63" }}>
            <h2>🤖 AI Oracle</h2>

            <div style={inputGroup}>
              <label>Ticker:</label>
              <input
                value={aiTicker}
                onChange={(e) => setAiTicker(e.target.value)}
                style={inputStyle}
                placeholder="VD: HPG.VN"
              />
            </div>
            <button onClick={askAI} style={{ ...btnStyle, backgroundColor: "#e91e63" }} disabled={loadingAI}>
              {loadingAI ? "Scanning..." : "ASK AI 🔮"}
            </button>

            {aiResult && (
              <div style={{ marginTop: "15px", padding: "15px", backgroundColor: "#2d1b2e", borderRadius: "8px", textAlign: "center" }}>
                <h3 style={{ margin: "0 0 10px 0", fontSize: "24px", color: aiResult.signal.includes("TĂNG") ? "#00e676" : "#ff1744" }}>
                  {aiResult.signal}
                </h3>
                <div style={{ marginBottom: "15px", color: "#ddd" }}>Độ tin cậy: <b>{aiResult.confidence}%</b></div>

                {/* LƯỚI CHỈ SỐ KỸ THUẬT */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "13px", textAlign: "left", backgroundColor: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                  <div>RSI (Sức mạnh): <b style={{ color: "#ffd700" }}>{aiResult.details.RSI}</b></div>
                  <div>MACD (Xu hướng): <b style={{ color: aiResult.details.MACD > 0 ? "#00e676" : "#ff1744" }}>{aiResult.details.MACD}</b></div>
                  <div>Bollinger (%B): <b>{aiResult.details.BB_Pct}</b></div>
                  <div>Vol Ratio (Tiền): <b style={{ color: aiResult.details.Vol_Rat > 1 ? "#00e676" : "#aaa" }}>{aiResult.details.Vol_Rat}x</b></div>
                </div>
                <p style={{ fontSize: "11px", color: "#666", marginTop: "5px", fontStyle: "italic" }}>
                  *MACD {'>'} 0: Tăng. %B {'>'} 1: Quá mua. Vol {'>'} 1: Tiền vào mạnh.
                </p>
              </div>
            )}
          </div>

          {/* OPS CONFIG */}
          <div style={cardStyle}>
            <h2>⚖️ Portfolio Config</h2>

            <div style={inputGroup}>
              <label>Assets:</label>
              <textarea
                value={opsTickers}
                onChange={(e) => setOpsTickers(e.target.value)}
                style={{ ...inputStyle, resize: "vertical", minHeight: "80px", fontSize: "14px" }}
                rows={4}
              />
            </div>

            <div style={inputGroup}>
              <label>Lookbacks:</label>
              <input type="text" value={opsLookbacks} onChange={(e) => setOpsLookbacks(e.target.value)} style={inputStyle} />
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <div style={{ ...inputGroup, flex: 1 }}>
                <label>Eta:</label>
                <input type="number" step="0.01" value={opsEta} onChange={(e) => setOpsEta(e.target.value)} style={inputStyle} />
              </div>
              <div style={{ ...inputGroup, flex: 1 }}>
                <label>Max W:</label>
                <input type="number" step="0.1" value={opsMaxWeight} onChange={(e) => setOpsMaxWeight(e.target.value)} style={inputStyle} />
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "15px" }}>
              <button onClick={runOPS} style={{ ...btnStyle, flex: 1 }} disabled={loadingOPS}>
                {loadingOPS ? "..." : "OPTIMIZE ⚖️"}
              </button>
              <button onClick={runBacktest} style={{ ...btnStyle, backgroundColor: "#0091ea", flex: 1 }} disabled={loadingBacktest}>
                {loadingBacktest ? "..." : "BACKTEST 📈"}
              </button>
            </div>
          </div>
        </div>

        {/* COLUMN 3: RESULTS (STATUS + TABLE + CHART) */}
        <div style={columnStyle}>

          {/* SYSTEM STATUS */}
          <div style={{ ...cardStyle, padding: "10px 15px", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
            <h2 style={{ margin: 0, fontSize: "16px" }}>📡 Status</h2>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {status ? <span style={{ color: "#4caf50", fontSize: "12px" }}>● Online</span> : <span style={{ color: "#555" }}>● Unknown</span>}
              <button onClick={checkBackend} style={{ ...btnStyle, padding: "5px 10px", fontSize: "12px" }}>Check</button>
            </div>
          </div>

          {/* OPS RESULTS TABLE */}
          {opsResult && (
            <div style={{ ...cardStyle, marginBottom: "15px" }}>
              <h3 style={{ marginTop: 0, fontSize: "16px" }}>Allocation Target</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #555", color: "#888" }}>
                    <th style={{ textAlign: "left", padding: "5px" }}>Asset</th>
                    <th style={{ textAlign: "right", padding: "5px" }}>Weight</th>
                    <th style={{ textAlign: "right", padding: "5px" }}>%</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(opsResult)
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, val]) => (
                      <tr key={key} style={{ borderBottom: "1px solid #333" }}>
                        <td style={{ padding: "5px" }}>{key}</td>
                        <td style={{ textAlign: "right", padding: "5px" }}>{val}</td>
                        <td style={{ textAlign: "right", padding: "5px", color: "#2196f3", fontWeight: "bold" }}>
                          {(val * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {/* BACKTEST CHART */}
          {backtestResult && (
            <div style={cardStyle}>
              <h3 style={{ marginTop: 0, fontSize: "16px" }}>Backtest Performance</h3>

              {/* Metrics Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "15px" }}>
                <div style={{ padding: "8px", background: "rgba(0, 230, 118, 0.1)", borderRadius: "5px", border: "1px solid #00e676" }}>
                  <div style={{ color: "#00e676", fontSize: "12px", fontWeight: "bold" }}>OPS Strategy</div>
                  <div style={{ fontSize: "16px", fontWeight: "bold" }}>{backtestResult.metrics.strategy.total_return}%</div>
                  <div style={{ fontSize: "11px", color: "#aaa" }}>Sharpe: {backtestResult.metrics.strategy.sharpe_ratio}</div>
                </div>
                <div style={{ padding: "8px", background: "rgba(255, 23, 68, 0.1)", borderRadius: "5px", border: "1px solid #ff1744" }}>
                  <div style={{ color: "#ff1744", fontSize: "12px", fontWeight: "bold" }}>Benchmark</div>
                  <div style={{ fontSize: "16px", fontWeight: "bold" }}>{backtestResult.metrics.benchmark.total_return}%</div>
                  <div style={{ fontSize: "11px", color: "#aaa" }}>Sharpe: {backtestResult.metrics.benchmark.sharpe_ratio}</div>
                </div>
              </div>

              <div style={{ height: "200px" }}>
                <Line options={{ ...chartOptions, plugins: { ...chartOptions.plugins, legend: { display: false } } }} data={chartData} />
              </div>
            </div>
          )}

          {!opsResult && !backtestResult && (
            <div style={{ ...cardStyle, textAlign: "center", color: "#555", padding: "40px" }}>
              <div style={{ fontSize: "40px", marginBottom: "10px" }}>📊</div>
              <div>Results will appear here</div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}

// --- CSS STYLES ---

const gridContainerStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: "20px",
  alignItems: "flex-start",
  justifyContent: "center",
  width: "100%"
};

const columnStyle = {
  flex: "1 1 320px",
  display: "flex",
  flexDirection: "column",
  gap: "20px",
  minWidth: "300px",
  maxWidth: "100%"
};

const cardStyle = {
  backgroundColor: "#2a2a2a",
  padding: "15px 20px",
  borderRadius: "8px",
  boxShadow: "0 4px 6px rgba(0,0,0,0.2)"
};

const inputGroup = {
  marginBottom: "12px",
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start"
};

const inputStyle = {
  width: "100%",
  padding: "8px 10px",
  marginTop: "4px",
  borderRadius: "4px",
  border: "1px solid #444",
  backgroundColor: "#333",
  color: "#fff",
  fontSize: "14px",
  boxSizing: "border-box"
};

const btnStyle = {
  padding: "10px",
  backgroundColor: "#646cff",
  color: "white",
  border: "none",
  borderRadius: "4px",
  cursor: "pointer",
  fontSize: "14px",
  fontWeight: "bold",
  transition: "opacity 0.2s",
  width: "100%"
};

const resultBox = {
  marginTop: "15px",
  padding: "10px",
  backgroundColor: "#1e1e1e",
  borderRadius: "4px",
  borderLeft: "3px solid #646cff"
};

export default App
