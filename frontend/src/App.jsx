
import { useState, useEffect } from 'react'
import axios from 'axios'
// --- IMPORT MỚI CHO BIỂU ĐỒ ---
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

// Đăng ký các thành phần biểu đồ
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

// Lấy URL từ biến môi trường (cấu hình Vercel) hoặc mặc định localhost
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [status, setStatus] = useState("");

  // State cho NTF
  const [ntfTickers, setNtfTickers] = useState("BTC-USD, ETH-USD, LTC-USD");
  const [ntfLookback, setNtfLookback] = useState(20);
  const [ntfResult, setNtfResult] = useState(null);
  const [ntfMissing, setNtfMissing] = useState([]);
  const [loadingNTF, setLoadingNTF] = useState(false);

  // State cho OPS
  const [opsTickers, setOpsTickers] = useState("AAPL, MSFT, GOOGL, AMZN");
  const [opsEta, setOpsEta] = useState(0.05);
  // Thêm state mới OPS Max Weight
  const [opsMaxWeight, setOpsMaxWeight] = useState(1.0);
  const [opsResult, setOpsResult] = useState(null);
  const [loadingOPS, setLoadingOPS] = useState(false);

  // --- STATE MỚI CHO BACKTEST ---
  const [backtestResult, setBacktestResult] = useState(null);
  const [loadingBacktest, setLoadingBacktest] = useState(false);

  // 1. Check Backend
  const checkBackend = async () => {
    try {
      const res = await axios.get(`${API_URL}/`);
      setStatus(res.data.status);
    } catch (err) {
      setStatus("Error connecting to backend");
      console.error(err);
    }
  };

  // 2. Run NTF
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
      const errorMsg = err.response?.data?.detail || "Lỗi kết nối Backend/Vercel (Kiểm tra Log)";
      alert(`NTF Error: ${errorMsg}`);
    }
    setLoadingNTF(false);
  };

  // 3. Run OPS
  const runOPS = async () => {
    setLoadingOPS(true);
    setOpsResult(null);
    try {
      const res = await axios.post(`${API_URL}/api/run-ops`, {
        tickers: opsTickers,
        eta: Number(opsEta)
      });
      setOpsResult(res.data.weights);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Lỗi kết nối Backend/Vercel (Kiểm tra Log)";
      alert(`OPS Error: ${errorMsg}`);
    }
    setLoadingOPS(false);
  };

  // 4. Run Backtest
  const runBacktest = async () => {
    setLoadingBacktest(true);
    setBacktestResult(null);
    try {
      // Dùng chung input của phần OPS để Backtest
      const res = await axios.post(`${API_URL}/api/backtest`, {
        tickers: opsTickers,
        eta: Number(opsEta),
        max_weight: Number(opsMaxWeight),
        period: "1y" // Mặc định 1 năm
      });
      setBacktestResult(res.data);
    } catch (err) {
      console.error(err);
      const errorMsg = err.response?.data?.detail || "Lỗi Backtest! Đảm bảo Backend đã cập nhật.";
      alert(`Backtest Error: ${errorMsg}`);
    }
    setLoadingBacktest(false);
  };

  // --- CẤU HÌNH BIỂU ĐỒ ---
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: 'So sánh Hiệu suất Đầu tư (1 Năm qua)' },
    },
    scales: {
      x: { ticks: { maxTicksLimit: 10 } } // Giới hạn số nhãn ngày cho đỡ rối
    }
  };

  const chartData = backtestResult ? {
    labels: backtestResult.chart_data.dates,
    datasets: [
      {
        label: 'Thuật toán OPS (AI)',
        data: backtestResult.chart_data.strategy,
        borderColor: '#00e676', // Màu xanh lá
        backgroundColor: 'rgba(0, 230, 118, 0.5)',
        borderWidth: 2,
        pointRadius: 0, // Ẩn điểm tròn cho mượt
      },
      {
        label: 'Mua & Giữ (Benchmark)',
        data: backtestResult.chart_data.benchmark,
        borderColor: '#ff1744', // Màu đỏ
        backgroundColor: 'rgba(255, 23, 68, 0.5)',
        borderWidth: 2,
        pointRadius: 0,
        borderDash: [5, 5], // Nét đứt
      },
    ],
  } : null;

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif", maxWidth: "900px", margin: "0 auto", backgroundColor: "#1e1e1e", color: "#e0e0e0", minHeight: "100vh" }}>
      <h1 style={{ color: "#646cff", textAlign: "center" }}>Quant Trading Dashboard 3.0 (Ultimate)</h1>

      {/* SECTION: SYSTEM STATUS */}
      <div style={cardStyle}>
        <h2>📡 System Status</h2>
        <button onClick={checkBackend} style={btnStyle}>Check Connectivity</button>
        {status && <p style={{ marginTop: "10px", color: "#4caf50" }}>Status: {status}</p>}
      </div>

      {/* SECTION: NTF ENGINE */}
      <div style={cardStyle}>
        <h2>🌐 Network Trend Following (NTF)</h2>
        <p style={{ fontSize: "0.9em", color: "#aaa" }}>Nhập mã tài sản để đo Momentum (VD: VCB.VN, HPG.VN hoặc BTC-USD)</p>

        <div style={inputGroup}>
          <label>Tickers (comma separated):</label>
          <textarea
            value={ntfTickers}
            onChange={(e) => setNtfTickers(e.target.value)}
            style={{ ...inputStyle, resize: "vertical", minHeight: "60px" }}
            rows={3}
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
          {loadingNTF ? "Calculating..." : "Run NTF Analysis"}
        </button>

        {ntfResult && (
          <div style={resultBox}>
            {/* Warning for missing tickers */}
            {ntfMissing && ntfMissing.length > 0 && (
              <div style={{ marginBottom: "15px", padding: "10px", backgroundColor: "#3a2a2a", borderLeft: "4px solid #f44336", color: "#ff8a80" }}>
                ⚠️ <strong>Missing Data:</strong> {ntfMissing.join(", ")} (Possibly delisted or invalid)
              </div>
            )}

            <h3>Momentum Scores:</h3>
            <ul>
              {Object.entries(ntfResult)
                .sort(([, a], [, b]) => b - a) // Sắp xếp từ cao xuống thấp
                .map(([key, val]) => (
                  <li key={key} style={{ marginBottom: "5px" }}>
                    <strong>{key}:</strong> <span style={{ color: val > 0 ? "#4caf50" : "#f44336" }}>{val}</span>
                  </li>
                ))}
            </ul>
          </div>
        )}
      </div>

      {/* SECTION: OPS ENGINE & BACKTEST */}
      <div style={cardStyle}>
        <h2>⚖️ Portfolio Optimization & Backtest</h2>
        <p style={{ fontSize: "0.9em", color: "#aaa" }}>Phân bổ tỷ trọng tối ưu & Kiểm thử quá khứ.</p>

        <div style={inputGroup}>
          <label>Portfolio Assets:</label>
          <textarea
            value={opsTickers}
            onChange={(e) => setOpsTickers(e.target.value)}
            style={{ ...inputStyle, resize: "vertical", minHeight: "60px" }}
            rows={3}
          />
        </div>
        <div style={inputGroup}>
          <label>Learning Rate (Eta):</label>
          <input
            type="number"
            step="0.01"
            value={opsEta}
            onChange={(e) => setOpsEta(e.target.value)}
            style={inputStyle}
          />
          <small style={{ display: "block", marginTop: "5px", color: "#888" }}>Eta cao = Thích ứng nhanh (Aggressive). Eta thấp = Ổn định (Conservative).</small>
        </div>

        <div style={inputGroup}>
          <label>Max Weight (0.0 - 1.0):</label>
          <input
            type="number"
            step="0.1"
            max="1.0"
            min="0.1"
            value={opsMaxWeight}
            onChange={(e) => setOpsMaxWeight(e.target.value)}
            style={inputStyle}
          />
          <small style={{ display: "block", marginTop: "5px", color: "#888" }}>Tỷ trọng tối đa cho một mã (VD: 0.5 = Max 50%).</small>
        </div>

        <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
          <button onClick={runOPS} style={{ ...btnStyle, flex: 1 }} disabled={loadingOPS}>
            {loadingOPS ? "Optimizing..." : "TÍNH TỶ TRỌNG NGAY ⚖️"}
          </button>
          <button onClick={runBacktest} style={{ ...btnStyle, backgroundColor: "#0091ea", flex: 1 }} disabled={loadingBacktest}>
            {loadingBacktest ? "Đang giả lập..." : "KIỂM THỬ QUÁ KHỨ 📈"}
          </button>
        </div>

        {opsResult && (
          <div style={resultBox}>
            <h3>Recommended Allocation:</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #555" }}>
                  <th style={{ textAlign: "left", padding: "5px" }}>Asset</th>
                  <th style={{ textAlign: "right", padding: "5px" }}>Weight</th>
                  <th style={{ textAlign: "right", padding: "5px" }}>Percent</th>
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

        {/* KẾT QUẢ BACKTEST */}
        {backtestResult && (
          <div style={{ marginTop: "20px", padding: "15px", backgroundColor: "#1a1a1a", borderRadius: "8px", border: "1px solid #333" }}>

            {/* 1. Bảng chỉ số */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" }}>
              <div style={{ padding: "10px", background: "rgba(0, 230, 118, 0.1)", borderRadius: "5px", border: "1px solid #00e676" }}>
                <h4 style={{ margin: "0 0 10px 0", color: "#00e676" }}>🤖 Thuật toán OPS</h4>
                <div>Lợi nhuận: <b>{backtestResult.metrics.strategy.total_return}%</b></div>
                <div>Sharpe Ratio: <b>{backtestResult.metrics.strategy.sharpe_ratio}</b></div>
                <div>Sụt giảm (Drawdown): <b style={{ color: "#ff1744" }}>{backtestResult.metrics.strategy.max_drawdown}%</b></div>
              </div>
              <div style={{ padding: "10px", background: "rgba(255, 255, 255, 0.05)", borderRadius: "5px", border: "1px solid #555" }}>
                <h4 style={{ margin: "0 0 10px 0", color: "#aaa" }}>🐢 Mua & Giữ (Benchmark)</h4>
                <div>Lợi nhuận: <b>{backtestResult.metrics.benchmark.total_return}%</b></div>
                <div>Sharpe Ratio: <b>{backtestResult.metrics.benchmark.sharpe_ratio}</b></div>
                <div>Sụt giảm (Drawdown): <b style={{ color: "#ff1744" }}>{backtestResult.metrics.benchmark.max_drawdown}%</b></div>
              </div>
            </div>

            {/* 2. Biểu đồ */}
            <div style={{ height: "300px" }}>
              <Line options={chartOptions} data={chartData} />
            </div>

            <p style={{ fontSize: "12px", color: "#666", textAlign: "center", marginTop: "10px" }}>
              *Dữ liệu giả lập 1 năm gần nhất. Quá khứ không đảm bảo tương lai.
            </p>
          </div>
        )}

      </div>

    </div>
  )
}

// --- CSS STYLES (Inline for simplicity) ---
const cardStyle = {
  backgroundColor: "#2a2a2a",
  padding: "20px",
  borderRadius: "10px",
  marginBottom: "20px",
  boxShadow: "0 4px 6px rgba(0,0,0,0.3)"
};

const inputGroup = {
  marginBottom: "15px",
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start"
};

const inputStyle = {
  width: "100%",
  padding: "10px",
  marginTop: "5px",
  borderRadius: "5px",
  border: "1px solid #444",
  backgroundColor: "#333",
  color: "#fff",
  fontSize: "16px"
};

const btnStyle = {
  padding: "10px 20px",
  backgroundColor: "#646cff",
  color: "white",
  border: "none",
  borderRadius: "5px",
  cursor: "pointer",
  fontSize: "16px",
  fontWeight: "bold",
  transition: "background 0.3s"
};

const resultBox = {
  marginTop: "20px",
  padding: "15px",
  backgroundColor: "#1a1a1a",
  borderRadius: "5px",
  borderLeft: "4px solid #646cff"
};

export default App
