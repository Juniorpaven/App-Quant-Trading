
import { useState, useRef } from 'react'
import axios from 'axios'
import html2canvas from 'html2canvas'; // Import html2canvas
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
import zoomPlugin from 'chartjs-plugin-zoom';
import CommandCenter from './components/CommandCenter';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  zoomPlugin
);

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const exportToImage = async (elementId, fileName) => {
    const element = document.getElementById(elementId);
    if (!element) return;
    try {
      const canvas = await html2canvas(element, {
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#2a2a2a' // Dark background matching card style
      });
      const image = canvas.toDataURL("image/jpeg", 1.0);
      const link = document.createElement('a');
      link.href = image;
      link.download = `${fileName}_${new Date().toISOString().slice(0, 10)}.jpg`;
      link.click();
    } catch (err) {
      console.error("Export failed:", err);
      alert("Lỗi xuất ảnh: " + err.message);
    }
  };

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
  const [manualWeights, setManualWeights] = useState({});
  const [useManual, setUseManual] = useState(false);

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

  const handleWeightChange = (ticker, value) => {
    setManualWeights({
      ...manualWeights,
      [ticker]: parseFloat(value) / 100
    });
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
        period: "5y",
        custom_weights: useManual ? manualWeights : {}
      });
      setBacktestResult(res.data);
      if (res.data.final_weights) {
        setOpsResult(res.data.final_weights);
      }
    } catch (err) {
      console.error(err);
      const errorMsg = typeof err.response?.data?.detail === "object"
        ? JSON.stringify(err.response?.data?.detail)
        : (err.response?.data?.detail || "Lỗi Backtest!");
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
      title: { display: true, text: 'So sánh Hiệu suất Đầu tư (5 Năm qua)' },
      zoom: {
        pan: {
          enabled: true,
          mode: 'x', // Cho phép kéo qua lại theo trục X
        },
        zoom: {
          wheel: {
            enabled: true, // Cho phép lăn chuột để zoom
          },
          pinch: {
            enabled: true
          },
          mode: 'x', // Chỉ zoom theo trục X
        }
      }
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

  // Ref for chart
  const chartRef = useRef(null);

  const resetZoom = () => {
    if (chartRef.current) {
      chartRef.current.resetZoom();
    }
  };

  return (
    <div style={{ padding: "10px 20px", fontFamily: "Arial, sans-serif", maxWidth: "100%", margin: "0 auto", backgroundColor: "#1e1e1e", color: "#e0e0e0", minHeight: "100vh", boxSizing: "border-box" }}>
      <h1 style={{ color: "#646cff", textAlign: "center", marginBottom: "20px", fontSize: "1.5rem" }}>Quant Trading Dashboard 3.0 (Ultimate)</h1>

      {/* COMMAND CENTER DASHBOARD */}
      <CommandCenter />

      <div style={gridContainerStyle}>

        {/* COLUMN 1: MARKET SCAN (NTF) */}
        <div style={columnStyle}>
          <div id="ntf-section" style={{ ...cardStyle, height: "100%", position: 'relative' }}>
            <button onClick={() => exportToImage('ntf-section', 'NTF_Analysis')} style={{ position: 'absolute', top: '10px', right: '10px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '20px' }} title="Export Image">📸</button>
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
          <div id="ai-section" style={{ ...cardStyle, borderLeft: "4px solid #e91e63", position: 'relative' }}>
            <button onClick={() => exportToImage('ai-section', 'AI_Oracle')} style={{ position: 'absolute', top: '10px', right: '10px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '20px' }} title="Export Image">📸</button>
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
              <div style={{ marginTop: "20px", padding: "20px", backgroundColor: "#2d1b2e", borderRadius: "12px", border: "1px solid #ff0055" }}>

                {/* 1. PHẦN TÍN HIỆU (GIỮ NGUYÊN) */}
                <h2 style={{ textAlign: "center", color: aiResult.signal.includes("TĂNG") ? "#00e676" : "#ff1744", fontSize: "32px", margin: "0" }}>
                  {aiResult.signal}
                </h2>
                <p style={{ textAlign: "center", color: "#ddd", marginBottom: "20px" }}>
                  Độ tin cậy: <b>{aiResult.confidence}%</b>
                </p>

                {/* 2. LƯỚI CHỈ SỐ (CẬP NHẬT BANDWIDTH) */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", backgroundColor: "rgba(0,0,0,0.3)", padding: "15px", borderRadius: "8px", marginBottom: "20px" }}>
                  <div>RSI: <b style={{ color: "#ffd700" }}>{aiResult.details.RSI}</b></div>
                  <div>MACD: <b style={{ color: aiResult.details.MACD > 0 ? "#00e676" : "#ff1744" }}>{aiResult.details.MACD}</b></div>
                  <div>Vol Ratio: <b style={{ color: aiResult.details.Vol_Rat > 1 ? "#00e676" : "#aaa" }}>{aiResult.details.Vol_Rat}x</b></div>
                  <div>%B (Vị trí): <b>{aiResult.details.BB_Pct}</b></div>

                  {/* HIỂN THỊ BANDWIDTH MỚI */}
                  <div style={{ gridColumn: "1 / span 2", borderTop: "1px solid #444", paddingTop: "10px", marginTop: "5px" }}>
                    BandWidth (Độ nén): <b style={{ color: "#00e5ff" }}>{aiResult.details.BandWidth}</b>
                    <br />
                    <span style={{ fontSize: "11px", color: "#aaa", fontStyle: "italic" }}>
                      {aiResult.details.BandWidth < 0.1 ? "⚠️ Đang nén chặt (Sắp nổ)" : "Bình thường"}
                    </span>
                  </div>
                </div>

                {/* 3. BIỂU ĐỒ NẾN MINI (MỚI) */}
                <div style={{ marginTop: "15px" }}>
                  <h4 style={{ margin: "0 0 10px 0", color: "#888" }}>Biểu đồ kỹ thuật:</h4>
                  {/* Dùng ảnh Chart tĩnh từ nguồn bên ngoài để nhẹ web */}
                  <img
                    src={`https://image.vietstock.vn/chart/TA/${aiResult.ticker.replace(".VN", "")}`}
                    alt="Chart"
                    style={{ width: "100%", borderRadius: "8px", border: "1px solid #444" }}
                    onError={(e) => { e.target.style.display = 'none' }} // Ẩn nếu lỗi ảnh
                  />
                  <div style={{ textAlign: "center", marginTop: "10px" }}>
                    <a
                      href={`https://fireant.vn/ma-chung-khoan/${aiResult.ticker.replace(".VN", "")}`}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "#00e5ff", textDecoration: "none", fontSize: "13px" }}
                    >
                      👉 Xem biểu đồ FireAnt chi tiết
                    </a>
                  </div>
                </div>

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

            {/* --- KHU VỰC NHẬP TỶ TRỌNG THỦ CÔNG --- */}
            <div style={{ marginTop: "15px", padding: "10px", border: "1px dashed #555" }}>
              <label style={{ color: "#00e5ff", cursor: "pointer", fontSize: "14px" }}>
                <input
                  type="checkbox"
                  checked={useManual}
                  onChange={(e) => setUseManual(e.target.checked)}
                  style={{ marginRight: "8px" }}
                />
                👉 <b>Kích hoạt Chế độ "Lái Tay" (Manual)</b>
              </label>

              {useManual && (
                <div style={{ marginTop: "10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  {opsTickers.split(',').map(t => t.trim()).filter(t => t).map(ticker => (
                    <div key={ticker} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "13px" }}>{ticker}</span>
                      <input
                        type="number"
                        placeholder="%"
                        style={{ width: "50px", background: "#333", color: "white", border: "1px solid #555", padding: "4px", textAlign: "right" }}
                        onChange={(e) => handleWeightChange(ticker, e.target.value)}
                      />
                    </div>
                  ))}
                  <div style={{ gridColumn: "1 / span 2", fontSize: "11px", color: "#aaa", fontStyle: "italic", marginTop: "5px" }}>
                    *Tổng tỷ trọng nên bằng 100%
                  </div>
                </div>
              )}
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
            <div id="allocation-target-section" style={{ ...cardStyle, marginBottom: "15px", position: 'relative' }}>
              <button onClick={() => exportToImage('allocation-target-section', 'Allocation_Target')} style={{ position: 'absolute', top: '10px', right: '10px', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '20px' }} title="Export Image">📸</button>
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

        </div>
      </div>

      {/* FULL WIDTH: BACKTEST CHART */}
      {
        backtestResult && (
          <div id="backtest-section" style={{ ...cardStyle, marginTop: "20px", width: "100%", boxSizing: "border-box" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
              <div>
                <h3 style={{ marginTop: 0, fontSize: "18px", marginBottom: "5px" }}>Backtest Performance (5 Years)</h3>
                <div style={{ fontSize: "12px", color: "#aaa" }}>
                  Date Range: {backtestResult.chart_data.dates[0]} — {backtestResult.chart_data.dates[backtestResult.chart_data.dates.length - 1]}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={() => exportToImage('backtest-section', 'Backtest_Performance')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '20px' }} title="Export Image">📸</button>
                <button
                  onClick={resetZoom}
                  style={{ ...btnStyle, width: "auto", padding: "5px 15px", fontSize: "12px", backgroundColor: "#555" }}
                >
                  🔄 Reset Zoom
                </button>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" }}>
              <div style={{ padding: "15px", background: "rgba(0, 230, 118, 0.1)", borderRadius: "8px", border: "1px solid #00e676" }}>
                <div style={{ color: "#00e676", fontSize: "14px", fontWeight: "bold" }}>OPS Strategy</div>
                <div style={{ fontSize: "24px", fontWeight: "bold" }}>{backtestResult.metrics.strategy.total_return}%</div>
                <div style={{ fontSize: "13px", color: "#ddd" }}>Sharpe: {backtestResult.metrics.strategy.sharpe_ratio}</div>
                <div style={{ fontSize: "13px", color: "#ddd" }}>Max DD: <span style={{ color: "#ff5252" }}>{backtestResult.metrics.strategy.max_drawdown}%</span></div>
              </div>
              <div style={{ padding: "15px", background: "rgba(255, 23, 68, 0.1)", borderRadius: "8px", border: "1px solid #ff1744" }}>
                <div style={{ color: "#ff1744", fontSize: "14px", fontWeight: "bold" }}>Benchmark</div>
                <div style={{ fontSize: "24px", fontWeight: "bold" }}>{backtestResult.metrics.benchmark.total_return}%</div>
                <div style={{ fontSize: "13px", color: "#ddd" }}>Sharpe: {backtestResult.metrics.benchmark.sharpe_ratio}</div>
                <div style={{ fontSize: "13px", color: "#ddd" }}>Max DD: <span style={{ color: "#ff5252" }}>{backtestResult.metrics.benchmark.max_drawdown}%</span></div>
              </div>
            </div>

            <div style={{ height: "400px", width: "100%" }}>
              <Line
                ref={chartRef}
                options={{
                  ...chartOptions,
                  maintainAspectRatio: false,
                  plugins: {
                    ...chartOptions.plugins,
                    legend: { display: false }
                  }
                }}
                data={chartData}
              />
            </div>
          </div>
        )
      }
    </div >
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

const getRsiColor = (rsi) => {
  if (rsi > 70) return "#ff1744"; // Đỏ (Nóng)
  if (rsi < 30) return "#00e676"; // Xanh (Đáy)
  return "#ffd700"; // Vàng
};

export default App
