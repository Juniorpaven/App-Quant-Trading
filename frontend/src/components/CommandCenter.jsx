
import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CommandCenter = () => {
    const [sentiment, setSentiment] = useState(null);
    const [rrgData, setRrgData] = useState([]);
    const [fundTicker, setFundTicker] = useState("HPG");
    const [fundData, setFundData] = useState(null);
    const [loadingFund, setLoadingFund] = useState(false);

    useEffect(() => {
        fetchSentiment();
        fetchRRG();
    }, []);

    const fetchSentiment = async () => {
        try {
            const res = await axios.get(`${API_URL}/api/dashboard/sentiment`);
            setSentiment(res.data);
        } catch (e) { console.error("Sentiment error", e); }
    };

    const fetchRRG = async () => {
        try {
            const res = await axios.post(`${API_URL}/api/dashboard/rrg`);
            setRrgData(res.data.data || []);
        } catch (e) { console.error("RRG error", e); }
    };

    const checkFundamentals = async () => {
        if (!fundTicker) return;
        setLoadingFund(true);
        try {
            const res = await axios.post(`${API_URL}/api/dashboard/fundamentals`, { ticker: fundTicker });
            setFundData(res.data.data);
        } catch (e) { alert("Fund Error: " + e.message); }
        setLoadingFund(false);
    };

    // --- STYLES ---
    const containerStyle = {
        padding: "20px",
        backgroundColor: "#1a1a1a",
        borderRadius: "15px",
        marginBottom: "30px",
        border: "1px solid #333",
        boxShadow: "0 10px 30px rgba(0,0,0,0.5)"
    };

    const headerStyle = {
        color: "#00e5ff",
        fontSize: "24px",
        marginBottom: "20px",
        textTransform: "uppercase",
        letterSpacing: "2px",
        borderBottom: "1px solid #444",
        paddingBottom: "10px"
    };

    const sectionTitle = {
        color: "#aaa",
        fontSize: "16px",
        marginBottom: "15px",
        textTransform: "uppercase"
    };

    const cardStyle = {
        background: "linear-gradient(135deg, #2a2a2a 0%, #1e1e1e 100%)",
        borderRadius: "12px",
        padding: "20px",
        textAlign: "center",
        border: "1px solid #444",
        flex: 1,
        minWidth: "200px"
    };

    return (
        <div style={containerStyle}>
            <h1 style={headerStyle}>🛡️ Quant Cockpit - Titan Mode</h1>

            {/* ROW 1: SENTIMENT & TOP MOVERS */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "20px", marginBottom: "30px" }}>

                {/* MARKET GAUGE */}
                <div style={{ ...cardStyle, flex: 1 }}>
                    <h3 style={sectionTitle}>Market Pulse (VN30)</h3>
                    {sentiment ? (
                        <div style={{ position: 'relative', height: "200px" }}>
                            <Plot
                                data={[{
                                    domain: { x: [0, 1], y: [0, 1] },
                                    value: sentiment.market_score + 0.5, // Offset simple
                                    title: { text: sentiment.market_status, font: { size: 16, color: sentiment.market_color } },
                                    type: "indicator",
                                    mode: "gauge+number",
                                    gauge: {
                                        axis: { range: [-1, 1] }, // NTF Score range approx -1 to 1
                                        bar: { color: sentiment.market_color },
                                        steps: [
                                            { range: [-1, -0.1], color: "rgba(255, 23, 68, 0.3)" },
                                            { range: [-0.1, 0.1], color: "rgba(255, 215, 0, 0.3)" },
                                            { range: [0.1, 1], color: "rgba(0, 230, 118, 0.3)" }
                                        ],
                                        threshold: {
                                            line: { color: "white", width: 4 },
                                            thickness: 0.75,
                                            value: sentiment.market_score
                                        }
                                    }
                                }]}
                                layout={{
                                    width: 300,
                                    height: 200,
                                    margin: { t: 0, b: 0, l: 30, r: 30 },
                                    paper_bgcolor: "rgba(0,0,0,0)",
                                    font: { color: "white" }
                                }}
                                config={{ displayModeBar: false }}
                            />
                            <div style={{ textAlign: 'center', marginTop: '-50px', fontSize: '2em', fontWeight: 'bold', color: sentiment.market_color }}>
                                {sentiment.market_score}
                            </div>
                        </div>
                    ) : <p>Loading Sentiment...</p>}
                </div>

                {/* TOP 3 CARDS */}
                <div style={{ flex: 2, display: "flex", gap: "10px", flexDirection: "column" }}>
                    <h3 style={sectionTitle}>🔥 Top Leaders (Sector Flow)</h3>
                    <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
                        {sentiment && sentiment.top_movers.map((item, idx) => (
                            <div key={idx} style={{
                                ...cardStyle,
                                borderLeft: `5px solid ${item.score > 0.3 ? '#00e676' : '#ffd700'}`,
                                display: "flex", flexDirection: "column", justifyContent: "center"
                            }}>
                                <div style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "5px" }}>{item.ticker}</div>
                                <div style={{ fontSize: "14px", color: "#aaa" }}>NTF Score</div>
                                <div style={{ fontSize: "28px", fontWeight: "bold", color: item.score > 0 ? "#00e676" : "#ff1744" }}>
                                    {item.score}
                                </div>
                                <div style={{ marginTop: "10px", padding: "5px 10px", borderRadius: "4px", backgroundColor: item.score > 0.3 ? "rgba(0,230,118,0.2)" : "rgba(255,215,0,0.2)", color: item.score > 0.3 ? "#00e676" : "#ffd700", fontWeight: "bold" }}>
                                    {item.action}
                                </div>
                            </div>
                        ))}
                        {!sentiment && <p>Scanning Market...</p>}
                    </div>
                </div>
            </div>

            {/* ROW 2: RRG & FUNDAMENTALS */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "20px" }}>

                {/* RRG CHART */}
                <div style={{ ...cardStyle, flex: 2, minHeight: "500px" }}>
                    <h3 style={{ ...sectionTitle, display: 'flex', justifyContent: 'space-between' }}>
                        <span>🔄 Relative Rotation Graph (RRG)</span>
                        <span style={{ fontSize: '12px', color: '#666' }}>*Benchmark: VN-Index</span>
                    </h3>

                    {rrgData.length > 0 ? (
                        <Plot
                            data={[
                                {
                                    x: rrgData.map(d => d.x),
                                    y: rrgData.map(d => d.y),
                                    text: rrgData.map(d => d.ticker + " (" + d.quadrant + ")"),
                                    mode: 'markers+text',
                                    textposition: 'top center',
                                    marker: {
                                        size: 12,
                                        color: rrgData.map(d => d.x > 100 && d.y > 100 ? '#00e676' : d.x < 100 && d.y < 100 ? '#ff1744' : '#ffd700'),
                                        opacity: 0.8
                                    },
                                    type: 'scatter'
                                }
                            ]}
                            layout={{
                                autosize: true,
                                height: 450,
                                margin: { l: 50, r: 50, b: 50, t: 20 },
                                paper_bgcolor: "rgba(0,0,0,0)",
                                plot_bgcolor: "rgba(255,255,255,0.05)",
                                font: { color: "#e0e0e0" },
                                xaxis: {
                                    title: "Relative Strength (RS-Ratio)",
                                    gridcolor: "#333",
                                    zerolinecolor: "#666",
                                    range: [80, 120] // Auto-range better usually but lets center 100
                                },
                                yaxis: {
                                    title: "Momentum (RS-Momentum)",
                                    gridcolor: "#333",
                                    zerolinecolor: "#666",
                                    range: [90, 110]
                                },
                                shapes: [
                                    // Quadrant Lines
                                    { type: 'line', x0: 100, x1: 100, y0: 0, y1: 200, line: { color: 'gray', dash: 'dot' } },
                                    { type: 'line', x0: 0, x1: 200, y0: 100, y1: 100, line: { color: 'gray', dash: 'dot' } }
                                ],
                                annotations: [
                                    { x: 110, y: 105, text: "LEADING (Dẫn dắt) 🟢", showarrow: false, font: { color: "#00e676", size: 14, weight: "bold" } },
                                    { x: 90, y: 105, text: "IMPROVING (Cải thiện) 🔵", showarrow: false, font: { color: "#2979ff" } },
                                    { x: 90, y: 95, text: "LAGGING (Tụt hậu) 🔴", showarrow: false, font: { color: "#ff1744" } },
                                    { x: 110, y: 95, text: "WEAKENING (Suy yếu) 🟡", showarrow: false, font: { color: "#ffea00" } }
                                ]
                            }}
                            config={{ responsive: true, displayModeBar: false }}
                            style={{ width: "100%", height: "100%" }}
                        />
                    ) : (
                        <div style={{ padding: "50px", color: "#666" }}>Loading RRG Data (Fetching 1 Year History)...</div>
                    )}
                </div>

                {/* FUNDAMENTALS CHECK */}
                <div style={{ ...cardStyle, flex: 1 }}>
                    <h3 style={sectionTitle}>📊 Fundamental Snapshot</h3>
                    <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
                        <input
                            value={fundTicker}
                            onChange={(e) => setFundTicker(e.target.value)}
                            placeholder="Ticker (e.g. HPG)"
                            style={{ flex: 1, padding: "10px", borderRadius: "4px", border: "1px solid #555", backgroundColor: "#333", color: "white" }}
                        />
                        <button
                            onClick={checkFundamentals}
                            style={{ padding: "10px 20px", backgroundColor: "#00e5ff", border: "none", borderRadius: "4px", color: "black", fontWeight: "bold", cursor: "pointer" }}
                            disabled={loadingFund}
                        >
                            {loadingFund ? "..." : "CHECK"}
                        </button>
                    </div>

                    {fundData && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "#333", borderRadius: "5px" }}>
                                <span>P/E</span>
                                <strong style={{ color: fundData.pe > 20 ? "#ff1744" : "#00e676" }}>{fundData.pe}x</strong>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "#333", borderRadius: "5px" }}>
                                <span>ROE</span>
                                <strong style={{ color: fundData.roe < 10 ? "#ff1744" : "#00e676" }}>{fundData.roe}%</strong>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "#333", borderRadius: "5px" }}>
                                <span>EPS</span>
                                <strong>{fundData.eps} VND</strong>
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", padding: "10px", backgroundColor: "#333", borderRadius: "5px" }}>
                                <span>P/B</span>
                                <strong>{fundData.pb}x</strong>
                            </div>

                            {/* WARNING BOX */}
                            {(fundData.pe > 20 || fundData.roe < 10) && (
                                <div style={{ marginTop: "10px", padding: "10px", backgroundColor: "rgba(255, 23, 68, 0.1)", border: "1px solid #ff1744", color: "#ff1744", fontSize: "13px" }}>
                                    ⚠️ Warning:
                                    {fundData.pe > 20 && " High Valuation (P/E > 20)."}
                                    {fundData.roe < 10 && " Low Efficiency (ROE < 10%)."}
                                </div>
                            )}
                            {fundData.pe <= 20 && fundData.roe >= 10 && (
                                <div style={{ marginTop: "10px", padding: "10px", backgroundColor: "rgba(0, 230, 118, 0.1)", border: "1px solid #00e676", color: "#00e676", fontSize: "13px", fontWeight: "bold" }}>
                                    ✅ Fundamentals Good
                                </div>
                            )}
                            <div style={{ fontSize: '10px', color: '#666', marginTop: '5px' }}>Source: {fundData.source}</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CommandCenter;
