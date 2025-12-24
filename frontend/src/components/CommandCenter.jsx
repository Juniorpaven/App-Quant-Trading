
import React, { useState, useEffect, Suspense } from 'react';
import axios from 'axios';

// Lazy load Plotly to prevent bundle crash if it fails
const Plot = React.lazy(() => import('react-plotly.js'));

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CommandCenter = () => {
    const [sentiment, setSentiment] = useState(null);
    const [rrgData, setRrgData] = useState([]);
    const [fundTicker, setFundTicker] = useState("HPG");
    const [fundData, setFundData] = useState(null);
    const [loadingFund, setLoadingFund] = useState(false);
    const [isRrgLoading, setIsRrgLoading] = useState(true);
    const [marketError, setMarketError] = useState(false);
    const [leaders, setLeaders] = useState([]);

    const isManualMode = React.useRef(false); // Flag to prevent API overwrites

    useEffect(() => {
        fetchSentiment();
        fetchRRG();
    }, []);

    const fetchSentiment = async () => {
        try {
            const res = await axios.get(`${API_URL}/api/dashboard/sentiment`);

            // If user has already uploaded manual data, DO NOT overwrite with API
            if (isManualMode.current) return;

            setSentiment(res.data);

            // Sync API top movers to leaders state
            if (res.data && res.data.top_movers) {
                setLeaders(res.data.top_movers.map(m => m.ticker));
            }
        } catch (e) { console.error("Sentiment error", e); }
    };

    const fetchRRG = async () => {
        try {
            setIsRrgLoading(true);
            const res = await axios.post(`${API_URL}/api/dashboard/rrg`);

            // If user has already uploaded manual data, DO NOT overwrite with API
            if (isManualMode.current) {
                setIsRrgLoading(false);
                return;
            }

            const data = res.data.data || [];
            setRrgData(data);

            // If we have RRG data but no leaders yet (and no sentiment top movers), 
            // we could calculate leaders here too, but sentiment usually handles it.

            setIsRrgLoading(false);
            setMarketError(false);

            // Populate groups from API data
            const groups = new Set(data.map(d => d.group || "Unclassified"));
            setGroups(['ALL', ...Array.from(groups).sort()]);

        } catch (e) {
            console.error("RRG error", e);
            if (!isManualMode.current) {
                setIsRrgLoading(false);
                setMarketError(true);
            }
        }
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


    const [groups, setGroups] = useState([]);
    const [selectedGroup, setSelectedGroup] = useState('ALL');

    // --- RRG SNAPSHOT UPLOAD MODE ---
    const handleFileUpload = (event) => {
        isManualMode.current = true; // LOCK STATE: Prevent background API from overwriting
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target.result;
            const lines = text.split('\n').filter(l => l.trim());
            const data = [];
            const foundGroups = new Set();

            // PARSE CSV based on user's exact format:
            // Ticker,Group,RS_Ratio,RS_Momentum
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                const parts = line.split(',');

                if (parts.length >= 4) {
                    // Mapping based on provided sample:
                    // 0: Ticker
                    // 1: Group
                    // 2: RS_Ratio
                    // 3: RS_Momentum

                    const ticker = parts[0].replace(/["']/g, "").trim();
                    const group = parts[1].replace(/["']/g, "").trim();
                    const ratio = parseFloat(parts[2]);
                    const mom = parseFloat(parts[3]);

                    if (isNaN(ratio) || isNaN(mom)) continue; // Skip bad rows

                    foundGroups.add(group);

                    // RE-CALCULATE QUADRANT
                    let resultQuad = "Unknown";
                    if (ratio > 100 && mom > 100) resultQuad = "Leading (Dẫn dắt) 🟢";
                    else if (ratio > 100 && mom < 100) resultQuad = "Weakening (Suy yếu) 🟡";
                    else if (ratio < 100 && mom < 100) resultQuad = "Lagging (Tụt hậu) 🔴";
                    else resultQuad = "Improving (Cải thiện) 🔵";

                    data.push({
                        ticker: ticker,
                        x: ratio,
                        y: mom,
                        group: group,
                        quadrant: resultQuad
                    });
                }
            }

            // UPDATE STATE
            setRrgData(data);
            setGroups(['ALL', ...Array.from(foundGroups).sort()]);
            setIsRrgLoading(false);
            setMarketError(false);

            // --- AUTO CALCULATE TOP LEADERS ---
            // Find stocks in Leading quadrant (x>100, y>100), sort by distance from center (strength)
            const leaders = data
                .filter(d => d.x > 100 && d.y > 100)
                .sort((a, b) => (b.x + b.y) - (a.x + a.y)) // Simple sort by sum of scores
                .slice(0, 5) // Top 5
                .map(d => d.ticker);

            setLeaders(leaders);

            // --- AUTO RESTORE MARKET PULSE ---
            // Calculate a synthetic market score based on % of stocks above 100 RS-Ratio
            const bullishCount = data.filter(d => d.x > 100).length;
            const score = (bullishCount / data.length) * 2 - 1; // Map 0..1 to -1..1

            let status = "SIDEWAYS";
            let color = "white";
            if (score > 0.2) { status = "BULLISH"; color = "#00e676"; }
            else if (score < -0.2) { status = "BEARISH"; color = "#ff1744"; }

            setSentiment({
                market_status: status,
                market_score: parseFloat(score.toFixed(2)),
                market_color: color
            });

            console.log("RRG Snapshot Loaded:", data.length, "items. IndexCol:", hasIndexCol);
        };
        reader.readAsText(file);
    };

    // Filter RRG Data based on selection
    const filteredRrgData = selectedGroup === 'ALL'
        ? rrgData
        : rrgData.filter(d => d.group === selectedGroup);

    return (
        <div style={{ padding: '20px', backgroundColor: '#121212', minHeight: '100vh', color: 'white', fontFamily: 'Inter, sans-serif' }}>
            {/* ... Header ... */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#00e676', marginRight: '10px', boxShadow: '0 0 10px #00e676' }}></div>
                <h2 style={{ margin: 0, fontSize: '1.2em', letterSpacing: '2px', textTransform: 'uppercase', color: '#00e676' }}>🛡️ QUANT COCKPIT - TITAN MODE</h2>
            </div>

            {/* ERROR / FALLBACK UI - ALWAYS SHOW IF NO DATA */}
            {(marketError || isRrgLoading || rrgData.length === 0) && (
                <div style={{ marginBottom: '20px', padding: '10px', border: '1px dashed #333', borderRadius: '8px', textAlign: 'center' }}>
                    <p style={{ color: '#888', fontSize: '0.9em' }}>
                        {isRrgLoading && !marketError && rrgData.length === 0 ? "⏳ Đang kết nối Server..." : "⚠️ Chưa có dữ liệu RRG."}
                    </p>

                    {/* FILE UPLOAD BUTTON */}
                    <label style={{
                        display: 'inline-block',
                        marginTop: '10px',
                        padding: '8px 16px',
                        backgroundColor: '#212121',
                        border: '1px solid #444',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9em',
                        color: '#00e676'
                    }}>
                        📂 Nạp File Snapshot (RRG)
                        <input type="file" accept=".csv" onChange={handleFileUpload} style={{ display: 'none' }} />
                    </label>
                    <div style={{ fontSize: '10px', color: '#666', marginTop: '5px' }}>Dùng file CSV từ Colab để xem ngay nếu Server chậm.</div>
                </div>
            )}

            {/* DEBUG VIEW (COLLAPSIBLE) */}
            <details style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#333', borderRadius: '8px', cursor: 'pointer' }}>
                <summary style={{ color: '#ccc', fontSize: '0.9em' }}>🕵️ Kỹ thuật viên: Soi dữ liệu gốc (Debug)</summary>
                <div style={{ marginTop: '10px', overflowX: 'auto', backgroundColor: '#222', padding: '10px', borderRadius: '4px' }}>
                    {rrgData.length > 0 ? (
                        <table style={{ width: '100%', fontSize: '0.8em', color: '#aaa', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid #444' }}>
                                    <th style={{ textAlign: 'left', padding: '5px' }}>Ticker</th>
                                    <th style={{ textAlign: 'left', padding: '5px' }}>RS-Ratio</th>
                                    <th style={{ textAlign: 'left', padding: '5px' }}>RS-Momentum</th>
                                    <th style={{ textAlign: 'left', padding: '5px' }}>Group</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rrgData.slice(0, 5).map((d, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid #333' }}>
                                        <td style={{ padding: '5px' }}>{d.ticker}</td>
                                        <td style={{ padding: '5px', color: d.x > 100 ? '#00e676' : '#ff1744' }}>{d.x.toFixed(2)}</td>
                                        <td style={{ padding: '5px', color: d.y > 100 ? '#00e676' : '#ff1744' }}>{d.y.toFixed(2)}</td>
                                        <td style={{ padding: '5px' }}>{d.group}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : <p style={{ color: '#666', fontSize: '0.8em' }}>Chưa có dữ liệu. Hãy nạp file CSV.</p>}
                </div>
            </details>

            {/* Main Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', minHeight: '85vh', alignContent: 'start' }}>

                {/* 1. CHART AREA (RRG) - SPANS 2 COLUMNS */}
                <div style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '20px' }}>

                    {/* MARKET PULSE HEADER (REIMAGINED) */}
                    {sentiment && (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '20px',
                            padding: '15px',
                            backgroundColor: '#1e1e1e',
                            borderRadius: '12px',
                            border: '1px solid #333',
                            boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
                        }}>
                            {/* LEFT: SENTIMENT */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '10px', color: '#888', textTransform: 'uppercase', letterSpacing: '1px' }}>MARKET PULSE (VN30)</div>
                                    <h3 style={{ margin: '5px 0', fontSize: '1.8em', color: sentiment.market_color }}>{sentiment.market_status}</h3>
                                    <div style={{ fontSize: '2em', fontWeight: 'bold', color: sentiment.market_color }}>{sentiment.market_score}</div>
                                </div>

                                {/* Mini Gauge Chart */}
                                <div style={{ width: '120px', height: '60px' }}>
                                    <Suspense fallback={<div>...</div>}>
                                        <Plot
                                            data={[{
                                                type: "indicator",
                                                mode: "gauge",
                                                value: sentiment.market_score + 1, // Shift range -1..1 to 0..2 for gauge
                                                gauge: {
                                                    axis: { range: [0, 2], visible: false },
                                                    bar: { color: sentiment.market_color },
                                                    bgcolor: "#333",
                                                    borderwidth: 0,
                                                    steps: [
                                                        { range: [0, 0.9], color: "#444" }, // Red zone equivalent
                                                        { range: [0.9, 1.1], color: "#555" },
                                                        { range: [1.1, 2], color: "#666" }
                                                    ]
                                                }
                                            }]}
                                            layout={{ width: 120, height: 60, margin: { t: 0, b: 0, l: 0, r: 0 }, paper_bgcolor: "rgba(0,0,0,0)" }}
                                            config={{ displayModeBar: false }}
                                        />
                                    </Suspense>
                                </div>
                            </div>

                            {/* RIGHT: TOP LEADERS */}
                            <div style={{ borderLeft: '1px solid #444', paddingLeft: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                <div style={{ fontSize: '10px', color: '#ff9800', marginBottom: '10px' }}>🔥 TOP LEADERS (SECTOR FLOW)</div>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    {leaders.length > 0 ? leaders.map((l, i) => (
                                        <span key={i} style={{
                                            padding: '5px 10px',
                                            backgroundColor: '#2c2c2c',
                                            border: `1px solid ${i === 0 ? '#ff9800' : '#444'}`,
                                            borderRadius: '4px',
                                            fontSize: '0.9em',
                                            fontWeight: 'bold',
                                            color: i === 0 ? '#ff9800' : '#ccc'
                                        }}>
                                            {l.replace(".VN", "")}
                                        </span>
                                    )) : <span style={{ color: '#666' }}>Scanning Market...</span>}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* RRG CHART MAIN */}
                    <div style={{
                        flex: 1,
                        backgroundColor: '#1e1e1e',
                        borderRadius: '12px',
                        border: '1px solid #333',
                        padding: '10px',
                        position: 'relative',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
                        minHeight: '400px'
                    }}>
                        <div style={{ position: 'absolute', top: '15px', left: '15px', display: 'flex', gap: '10px', zIndex: 10, alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', color: '#00e5ff', display: 'flex', alignItems: 'center' }}>🟦 RELATIVE ROTATION GRAPH (RRG)</span>

                            {/* SECTOR SELECTOR */}
                            {groups.length > 0 && (
                                <select
                                    value={selectedGroup}
                                    onChange={(e) => setSelectedGroup(e.target.value)}
                                    style={{
                                        backgroundColor: '#333',
                                        color: 'white',
                                        border: '1px solid #555',
                                        padding: '2px 5px',
                                        borderRadius: '4px',
                                        fontSize: '11px',
                                        marginLeft: '10px'
                                    }}
                                >
                                    {groups.map(g => <option key={g} value={g}>{g}</option>)}
                                </select>
                            )}

                            {/* PERMANENT UPLOAD TRIGGER */}
                            <label style={{ cursor: 'pointer', fontSize: '10px', color: '#666', textDecoration: 'underline', marginLeft: '10px' }}>
                                (📂 Nạp CSV)
                                <input type="file" accept=".csv" onChange={handleFileUpload} style={{ display: 'none' }} />
                            </label>
                        </div>

                        {isRrgLoading && rrgData.length === 0 ? ( // Only show loading if no data and still loading
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666', flexDirection: 'column' }}>
                                <div style={{ marginBottom: '10px' }}>Loading RRG Data (Fetching 1 Year History)...</div>
                                <div style={{ fontSize: '0.8em', color: '#444' }}>If this takes too long, please use the Upload button above.</div>
                            </div>
                        ) : (
                            <Suspense fallback={<div>Loading RRG...</div>}>
                                <Plot
                                    data={[
                                        {
                                            x: filteredRrgData.map(d => d.x),
                                            y: filteredRrgData.map(d => d.y),
                                            text: filteredRrgData.map(d => d.ticker),
                                            mode: 'text+markers',
                                            textposition: 'top center',
                                            marker: {
                                                size: 12,
                                                color: filteredRrgData.map(d => {
                                                    if (d.x > 100 && d.y > 100) return '#00e676'; // Leading Green
                                                    if (d.x < 100 && d.y > 100) return '#2979ff'; // Improving Blue
                                                    if (d.x < 100 && d.y < 100) return '#ff1744'; // Lagging Red
                                                    return '#ffea00'; // Weakening Yellow
                                                }),
                                                line: { width: 1, color: 'white' }
                                            },
                                            type: 'scatter',
                                            hoverinfo: 'text+x+y+cluster' // cluster added for group info if formatted
                                        }
                                    ]}
                                    layout={{
                                        autosize: true,
                                        margin: { t: 50, r: 20, l: 40, b: 40 },
                                        xaxis: { title: 'RS-Ratio (Trend)', zeroline: false, gridcolor: '#333', range: [90, 110] }, // Fixed range or auto
                                        yaxis: { title: 'RS-Momentum (Speed)', zeroline: false, gridcolor: '#333', range: [90, 110] },
                                        paper_bgcolor: "rgba(0,0,0,0)",
                                        plot_bgcolor: "rgba(0,0,0,0)",
                                        font: { color: "#ddd" },
                                        shapes: [
                                            { type: 'line', x0: 100, x1: 100, y0: 0, y1: 200, line: { color: 'white', width: 1, dash: 'dot' } },
                                            { type: 'line', x0: 0, x1: 200, y0: 100, y1: 100, line: { color: 'white', width: 1, dash: 'dot' } }
                                        ],
                                        annotations: [
                                            { x: 105, y: 105, text: "LEADING (Dẫn dắt) 🟢", showarrow: false, font: { color: "#00e676", size: 14 }, opacity: 0.5 },
                                            { x: 95, y: 105, text: "IMPROVING (Cải thiện) 🔵", showarrow: false, font: { color: "#2979ff", size: 14 }, opacity: 0.5 },
                                            { x: 95, y: 95, text: "LAGGING (Tụt hậu) 🔴", showarrow: false, font: { color: "#ff1744", size: 14 }, opacity: 0.5 },
                                            { x: 105, y: 95, text: "WEAKENING (Suy yếu) 🟡", showarrow: false, font: { color: "#ffea00", size: 14 }, opacity: 0.5 }
                                        ]
                                    }}
                                    useResizeHandler={true}
                                    style={{ width: '100%', height: '100%' }}
                                    config={{ displayModeBar: false }}
                                />
                            </Suspense>
                        )}

                        <div style={{ position: 'absolute', bottom: '10px', right: '10px', fontSize: '10px', color: '#666' }}>
                            {marketError ? "Source: Manual Upload" : "Source: VCI/VNStock Engine v2"}
                        </div>
                    </div>
                </div>

                {/* 2. SIDEBAR PANELS */}
                <div style={{ ...cardStyle, flex: 1, textAlign: 'left', padding: '15px', background: '#1e1e1e', border: '1px solid #333', boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }}>
                    <h3 style={{ ...sectionTitle, marginBottom: '10px', color: '#00e5ff' }}>📊 Fundamental Snapshot</h3>
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

                            {/* COPY PROMPT BUTTON */}
                            <button
                                onClick={() => {
                                    if (!fundData) return;
                                    const tickerSimple = fundTicker.replace(".VN", "").toUpperCase();
                                    const rrgItem = rrgData.find(item => item.ticker === tickerSimple);
                                    // Extract simple status e.g. "LEADING" from "Leading (Dẫn dắt) 🟢"
                                    const rrgStatus = rrgItem ? rrgItem.quadrant.split('(')[0].trim().toUpperCase() : "N/A";
                                    const marketStatus = sentiment ? sentiment.market_status : "N/A";

                                    const prompt = `Phân tích Quant mã ${tickerSimple}: RRG ${rrgStatus}, P/E ${fundData.pe}, ROE ${fundData.roe}%, Market Pulse ${marketStatus}.`;

                                    navigator.clipboard.writeText(prompt);
                                    alert("📋 Đã copy Prompt cho AI:\n" + prompt);
                                }}
                                style={{
                                    marginTop: "15px",
                                    padding: "8px",
                                    width: "100%",
                                    backgroundColor: "#e91e63",
                                    color: "white",
                                    border: "none",
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    fontWeight: "bold",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: "5px"
                                }}
                            >
                                🤖 Copy Prompt to AI
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CommandCenter;
