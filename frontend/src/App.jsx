import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Mail, Search, CheckCircle, Send, Loader2,
    ArrowRight, Sparkles, Zap, Copy, RefreshCw, ChevronRight, BarChart, Upload, FileText, MapPin, Download
} from 'lucide-react';

const TEMPLATES = {
    "partnership": {
        name: "🤝 Partnership",
        subject: "Potential Synergy: [Your Company] + [Target Company]",
        message: "Hi [Name],\n\nI've been following [Target Company]'s work in [Industry] and I'm impressed by your recent [Achievement/Project].\n\nAt [Your Company], we assist companies like yours with [Value Proposition]. I believe there is a strong synergy between our offerings.\n\nAre you open to a brief 10-minute chat next week?\n\nBest,\n[Your Name]"
    },
    "sales": {
        name: "💼 Sales",
        subject: "Question regarding [Target Company] services",
        message: "Hello,\n\nI was browsing your website and had a specific question about your offerings. We are currently looking for a solution that handles [Problem].\n\nCould you point me to the right person to speak with?\n\nThanks,\n[Your Name]"
    },
    "investor": {
        name: "🚀 Investor",
        subject: "Investment Opportunity: Disrupting [Industry]",
        message: "Hi [Investor Name],\n\nI am the founder of [Your Company], and we are solving [Problem] for [Target Audience]. We have gained [Traction Metric] in the last [Timeframe].\n\nI'd love to share our deck with you if you are currently deploying capital in this space.\n\nBest,\n[Your Name]"
    },
    "custom": {
        name: "✨ Custom",
        subject: "",
        message: ""
    }
};

const STEPS = [
    { id: 'IDLE', label: 'Target', number: 1 },
    { id: 'SCRAPING', label: 'Extract', number: 2 },
    { id: 'REVIEW', label: 'Review', number: 3 },
    { id: 'COMPLETED', label: 'Done', number: 4 }
];

function App() {
    const [mode, setMode] = useState('single'); // 'single' | 'batch' | 'maps'
    const [formData, setFormData] = useState({ url: '', subject: '', message: '' });
    const [mapsData, setMapsData] = useState({ query: '', limit: 10 });
    const [file, setFile] = useState(null);
    const [templateKey, setTemplateKey] = useState('partnership');

    // Workflow State
    const [campaignId, setCampaignId] = useState(null);
    const [batchCampaigns, setBatchCampaigns] = useState([]); // [{id, url, status, count}]
    const [status, setStatus] = useState({});
    const [results, setResults] = useState(null);
    const [appState, setAppState] = useState('IDLE');

    // Maps State
    const [mapsTaskId, setMapsTaskId] = useState(null);
    const [mapsStatus, setMapsStatus] = useState(null); // Pending, Running, Completed, Failed
    const [mapsResults, setMapsResults] = useState([]);

    // Handle Template Selection
    useEffect(() => {
        if (templateKey !== 'custom' && TEMPLATES[templateKey]) {
            setFormData(prev => ({
                ...prev,
                subject: TEMPLATES[templateKey].subject,
                message: TEMPLATES[templateKey].message
            }));
        }
    }, [templateKey]);

    // Cleanup interval on unmount
    useEffect(() => {
        return () => setCampaignId(null);
    }, []);

    const handleScrape = async (e) => {
        e.preventDefault();

        if (mode === 'single') {
            if (!formData.url) return;
            setAppState('SCRAPING');
            try {
                const res = await axios.post('/api/campaign', { url: formData.url });
                if (res.data.id) {
                    setCampaignId(res.data.id);
                }
            } catch (err) {
                console.error(err);
                setAppState('IDLE');
                alert("Failed to start campaign. Ensure backend is running.");
            }
        } else if (mode === 'batch') {
            // Batch Mode
            if (!file) return;
            setAppState('BATCH_SCRAPING');
            const data = new FormData();
            data.append('file', file);

            try {
                const res = await axios.post('/api/upload-csv', data, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                if (res.data.campaigns) {
                    setBatchCampaigns(res.data.campaigns);
                }
            } catch (err) {
                console.error(err);
                setAppState('IDLE');
                alert("Failed to upload CSV.");
            }
        } else if (mode === 'maps') {
            // Maps Mode
            if (!mapsData.query) return;
            setAppState('MAPS_SCRAPING');
            setMapsStatus("Pending");
            try {
                const res = await axios.post('/api/maps/scrape', {
                    query: mapsData.query,
                    limit: parseInt(mapsData.limit)
                });
                if (res.data.task_id) {
                    setMapsTaskId(res.data.task_id);
                }
            } catch (err) {
                console.error(err);
                setAppState('IDLE');
                alert("Failed to start maps scraping.");
            }
        }
    };

    // Poll Status (Single + Batch + Maps)
    useEffect(() => {
        let interval;

        const isBatchRunning = batchCampaigns.length > 0 && batchCampaigns.some(c => {
            const s = status[c.id];
            // Keep polling if any campaign is undefined (initial) or processing
            return !s || (s !== 'Scraped' && s !== 'Failed' && s !== 'Completed');
        });

        const isMapsRunning = mapsTaskId && mapsStatus !== 'Completed' && mapsStatus !== 'Failed';

        const shouldPoll =
            (appState === 'SCRAPING' && campaignId) ||
            (appState === 'SENDING' && campaignId) ||
            (appState === 'BATCH_SCRAPING' && isBatchRunning) ||
            (appState === 'MAPS_SCRAPING' && isMapsRunning);

        if (shouldPoll) {
            interval = setInterval(async () => {
                try {
                    // Poll main status for single/batch
                    if (appState !== 'MAPS_SCRAPING') {
                        const res = await axios.get('/api/status');
                        const allStatus = res.data;
                        setStatus(allStatus);

                        // Single Mode Logic
                        if (mode === 'single' && campaignId) {
                            const myStatus = allStatus[campaignId];
                            if (myStatus === 'Scraped' && appState === 'SCRAPING') {
                                const resultRes = await axios.get(`/api/campaign/${campaignId}/results`);
                                setResults(resultRes.data);
                                setAppState('REVIEW');
                            }
                            if (myStatus === 'Completed' && appState === 'SENDING') {
                                setAppState('COMPLETED');
                            }
                        }
                    } else if (mode === 'maps' && mapsTaskId) {
                        // Maps polling
                        const res = await axios.get(`/api/maps/status/${mapsTaskId}`);
                        setMapsStatus(res.data.status);

                        if (res.data.status === 'Completed') {
                            const resultsRes = await axios.get(`/api/maps/results/${mapsTaskId}`);
                            if (resultsRes.data.results) {
                                setMapsResults(resultsRes.data.results);
                            }
                        }
                    }

                } catch (e) {
                    console.error(e);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [campaignId, appState, batchCampaigns, mode, status, mapsTaskId, mapsStatus]);

    const handleSend = async () => {
        if (!campaignId || !results) return;
        setAppState('SENDING');
        try {
            await axios.post('/api/send', {
                campaign_id: campaignId,
                subject: formData.subject,
                template: formData.message,
                emails: results.emails
            });
            setStatus(prev => ({ ...prev, [campaignId]: 'Sending' }));
            setAppState('COMPLETED');
        } catch (err) {
            console.error(err);
            alert("Failed to send emails");
            setAppState('REVIEW');
        }
    };

    const reset = () => {
        setAppState('IDLE');
        setResults(null);
        setCampaignId(null);
        setBatchCampaigns([]);
        setMapsTaskId(null);
        setMapsStatus(null);
        setMapsResults([]);
        setFormData({ url: '', subject: '', message: '' });
        setMapsData({ query: '', limit: 10 });
        setFile(null);
        setTemplateKey('partnership');
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
    };

    const downloadMapsCsv = () => {
        if (!mapsTaskId) return;
        window.open(`http://localhost:8000/api/maps/download/${mapsTaskId}`, '_blank');
    };

    // Helper to determine active step
    const getStepStatus = (stepId) => {
        const order = STEPS.findIndex(s => s.id === stepId);
        // Map BATCH_SCRAPING / MAPS_SCRAPING to 'SCRAPING' step visually
        let effectiveState = appState;
        if (appState === 'BATCH_SCRAPING') effectiveState = 'SCRAPING';
        if (appState === 'MAPS_SCRAPING') effectiveState = 'SCRAPING';

        const currentOrder = STEPS.findIndex(s => s.id === effectiveState);
        if (currentOrder > order) return 'completed';
        if (currentOrder === order) return 'active';
        return '';
    }

    return (
        <div className="container">
            <div className="blob blob-1"></div>
            <div className="blob blob-2"></div>

            <header className="fade-in">
                <div className="brand">
                    <Mail size={40} className="logo-icon" />
                    <h1>Email Automation</h1>
                </div>
                <p className="subtitle"> Email Extraction & Automated mails </p>
            </header>

            {/* Steps Indicator - Hide for maps or keep? Keeping it creates continuity */}
            {appState !== 'IDLE' && (
                <div className="steps fade-in">
                    {STEPS.map((step) => (
                        <div key={step.id} className={`step ${getStepStatus(step.id)}`}>
                            <div className="step-number">
                                {getStepStatus(step.id) === 'completed' ? <CheckCircle size={14} /> : step.number}
                            </div>
                            <span>{step.label}</span>
                            {step.id !== 'COMPLETED' && <ChevronRight size={14} style={{ opacity: 0.3, marginLeft: '0.5rem' }} />}
                        </div>
                    ))}
                </div>
            )}

            {/* STEP 1: TARGET (Single & Batch & Maps) */}
            {appState === 'IDLE' && (
                <div className="glass-panel fade-in">
                    <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                        <Zap size={48} color="#8b5cf6" style={{ marginBottom: '1rem' }} />
                        <h2>Start New Campaign</h2>
                        <p style={{ color: '#94a3b8' }}>Choose your data source.</p>

                        {/* Mode Switcher */}
                        <div style={{ display: 'inline-flex', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', padding: '4px', margin: '1rem 0' }}>
                            <button
                                onClick={() => setMode('single')}
                                style={{
                                    border: 'none', background: mode === 'single' ? 'var(--primary)' : 'transparent',
                                    color: mode === 'single' ? 'white' : 'var(--text-muted)',
                                    padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
                                }}
                            >
                                Single URL
                            </button>
                            <button
                                onClick={() => setMode('batch')}
                                style={{
                                    border: 'none', background: mode === 'batch' ? 'var(--primary)' : 'transparent',
                                    color: mode === 'batch' ? 'white' : 'var(--text-muted)',
                                    padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
                                }}
                            >
                                Batch CSV
                            </button>
                            <button
                                onClick={() => setMode('maps')}
                                style={{
                                    border: 'none', background: mode === 'maps' ? 'var(--primary)' : 'transparent',
                                    color: mode === 'maps' ? 'white' : 'var(--text-muted)',
                                    padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
                                    display: 'flex', alignItems: 'center', gap: '6px'
                                }}
                            >
                                <MapPin size={14} /> Google Maps
                            </button>
                        </div>
                    </div>

                    <form onSubmit={handleScrape}>
                        {mode === 'single' && (
                            <div className="input-wrapper">
                                <label>Target Website URL</label>
                                <input
                                    type="url"
                                    placeholder="https://company.com"
                                    value={formData.url}
                                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                                    required={mode === 'single'}
                                    autoFocus
                                />
                            </div>
                        )}

                        {mode === 'batch' && (
                            <div className="input-wrapper">
                                <label>Upload CSV List (One URL per line)</label>
                                <div style={{
                                    border: '2px dashed var(--border)', borderRadius: '12px', padding: '2rem',
                                    textAlign: 'center', cursor: 'pointer', background: 'rgba(0,0,0,0.2)'
                                }}>
                                    <input
                                        type="file"
                                        accept=".csv,.txt"
                                        onChange={(e) => setFile(e.target.files[0])}
                                        style={{ display: 'none' }}
                                        id="csv-upload"
                                        required={mode === 'batch'}
                                    />
                                    <label htmlFor="csv-upload" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                        {file ? (
                                            <>
                                                <FileText size={40} color="#22d3ee" style={{ marginBottom: '10px' }} />
                                                <span style={{ color: '#fff' }}>{file.name}</span>
                                            </>
                                        ) : (
                                            <>
                                                <Upload size={40} color="#94a3b8" style={{ marginBottom: '10px' }} />
                                                <span style={{ color: '#94a3b8' }}>Click to upload .csv or .txt</span>
                                            </>
                                        )}
                                    </label>
                                </div>
                            </div>
                        )}

                        {mode === 'maps' && (
                            <>
                                <div className="input-wrapper">
                                    <label>Search Query</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Restaurants in Delhi"
                                        value={mapsData.query}
                                        onChange={(e) => setMapsData({ ...mapsData, query: e.target.value })}
                                        required={mode === 'maps'}
                                        autoFocus
                                    />
                                </div>
                                <div className="input-wrapper">
                                    <label>Max Results</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="50"
                                        value={mapsData.limit}
                                        onChange={(e) => setMapsData({ ...mapsData, limit: e.target.value })}
                                        required={mode === 'maps'}
                                    />
                                </div>
                            </>
                        )}

                        <button type="submit" className="btn btn-primary btn-lg" style={{ width: '100%' }}>
                            {mode === 'single' ? 'Scan Website' : mode === 'batch' ? 'Process Batch' : 'Start Scraping'} <ArrowRight size={20} />
                        </button>
                    </form>
                </div>
            )}

            {/* STEP 2: SCRAPING (Single) */}
            {mode === 'single' && appState === 'SCRAPING' && (
                <div className="glass-panel fade-in loader-container">
                    <div className="spinner"></div>
                    <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Scanning Site...</h3>
                    <p style={{ color: '#94a3b8' }}>
                        Identifying contact pages, decoding emails, and validating addresses.
                    </p>
                </div>
            )}

            {/* STEP 2: BATCH DASHBOARD */}
            {mode === 'batch' && appState === 'BATCH_SCRAPING' && (
                <div className="glass-panel fade-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h2>Batch Scrape Progress</h2>
                        <button onClick={reset} className="btn btn-secondary btn-sm">Start Over</button>
                    </div>

                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                                    <th style={{ padding: '1rem' }}>URL</th>
                                    <th style={{ padding: '1rem' }}>Status</th>
                                    <th style={{ padding: '1rem' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {batchCampaigns.map((camp) => {
                                    const currStatus = status[camp.id] || "Pending";
                                    let statusColor = "#94a3b8"; // Pending
                                    if (currStatus === 'Scraping') statusColor = "#facc15"; // Yellow
                                    if (currStatus === 'Scraped') statusColor = "#4ade80"; // Green
                                    if (currStatus === 'Failed') statusColor = "#f87171"; // Red

                                    return (
                                        <tr key={camp.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                            <td style={{ padding: '1rem', fontFamily: 'monospace' }}>{camp.url}</td>
                                            <td style={{ padding: '1rem' }}>
                                                <span style={{
                                                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                                                    color: statusColor, fontWeight: 500, background: 'rgba(255,255,255,0.05)',
                                                    padding: '4px 10px', borderRadius: '12px', fontSize: '0.85rem'
                                                }}>
                                                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusColor }}></div>
                                                    {currStatus}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1rem' }}>
                                                {currStatus === 'Scraped' ? (
                                                    <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => {
                                                        setCampaignId(camp.id);
                                                        // Fetch results safely
                                                        axios.get(`/api/campaign/${camp.id}/results`)
                                                            .then(res => {
                                                                if (res.data) {
                                                                    setResults(res.data);
                                                                    setAppState('REVIEW');
                                                                }
                                                            })
                                                            .catch(err => {
                                                                console.error(err);
                                                                alert("Failed to load results. Please try again.");
                                                            });
                                                    }}>
                                                        View Results
                                                    </button>
                                                ) : (
                                                    <span style={{ color: '#64748b', fontSize: '0.9rem' }}>...</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* STEP 2: MAPS PROGRESS */}
            {mode === 'maps' && appState === 'MAPS_SCRAPING' && (
                <div className="glass-panel fade-in" style={{ textAlign: 'center', padding: '3rem 2rem', position: 'relative' }}>
                    {mapsStatus === 'Completed' ? (
                        <>
                            <div style={{ position: 'absolute', top: '1.5rem', left: '1.5rem' }}>
                                <button
                                    onClick={() => {
                                        setAppState('IDLE');
                                        setMapsTaskId(null);
                                        setMapsStatus(null);
                                        setMapsResults([]);
                                    }}
                                    style={{
                                        background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer',
                                        display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 500, fontSize: '0.9rem'
                                    }}
                                >
                                    <ArrowRight size={16} transform="rotate(180)" /> Back
                                </button>
                            </div>

                            <div style={{
                                background: 'linear-gradient(135deg, #10b981, #059669)',
                                width: '80px', height: '80px', borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem',
                                boxShadow: '0 10px 30px -10px rgba(16, 185, 129, 0.5)'
                            }}>
                                <CheckCircle size={40} color="white" />
                            </div>
                            <h3>Scraping Completed!</h3>
                            <p style={{ color: '#cad5e1', marginBottom: '2rem' }}>
                                Found {mapsResults.length} leads for "{mapsData.query}".
                            </p>

                            {mapsResults.length > 0 && (
                                <div style={{ marginBottom: '2rem', maxHeight: '400px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '12px', background: 'rgba(0,0,0,0.2)' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                                        <thead style={{ position: 'sticky', top: 0, background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(10px)', zIndex: 10 }}>
                                            <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                                                <th style={{ padding: '1rem' }}>Name</th>
                                                <th style={{ padding: '1rem' }}>Website</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {mapsResults.map((row, idx) => (
                                                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <td style={{ padding: '0.8rem 1rem', fontWeight: 500 }}>{row.Name}</td>
                                                    <td style={{ padding: '0.8rem 1rem', fontFamily: 'monospace', color: '#22d3ee' }}>
                                                        {row.Website && row.Website !== 'N/A' ? (
                                                            <a href={row.Website} target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'none', borderBottom: '1px dotted' }}>
                                                                {row.Website}
                                                            </a>
                                                        ) : (
                                                            <span style={{ color: '#64748b' }}>N/A</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                                <button onClick={downloadMapsCsv} className="btn btn-primary btn-lg">
                                    <Download size={20} /> Download CSV
                                </button>
                                <button onClick={reset} className="btn btn-secondary btn-lg">
                                    Start New
                                </button>
                            </div>
                        </>
                    ) : (mapsStatus === 'Failed' || mapsStatus === 'Not Found') ? (
                        <>
                            <div style={{
                                background: 'rgba(239, 68, 68, 0.2)',
                                width: '80px', height: '80px', borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem'
                            }}>
                                <Zap size={40} color="#f87171" />
                            </div>
                            <h3>Scraping Failed</h3>
                            <p style={{ color: '#94a3b8', marginBottom: '2rem' }}>
                                An error occurred while contacting Google Maps.
                            </p>
                            <button onClick={reset} className="btn btn-secondary btn-lg">
                                Try Again
                            </button>
                        </>
                    ) : (
                        <>
                            <div className="spinner"></div>
                            <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Scraping Google Maps...</h3>
                            <p style={{ color: '#94a3b8' }}>
                                Searching for "{mapsData.query}". This may take a minute.
                            </p>
                        </>
                    )}
                </div>
            )}

            {/* STEP 3: REVIEW & SEND (Reuse existing single view) */}
            {appState === 'REVIEW' && results && (
                <div className="fade-in">
                    <div className="glass-panel">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                            <div>
                                <button
                                    onClick={() => {
                                        if (mode === 'batch') {
                                            setAppState('BATCH_SCRAPING');
                                            setResults(null);
                                        } else {
                                            reset();
                                        }
                                    }}
                                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                                >
                                    <ArrowRight size={16} transform="rotate(180)" /> Back
                                </button>
                                <h2 style={{ margin: 0, fontSize: '1.8rem' }}>Campaign Results</h2>
                                <p style={{ color: '#94a3b8' }}>{results.metadata.title}</p>
                            </div>
                            <div className="badge" style={{ background: 'rgba(6, 182, 212, 0.2)', color: '#22d3ee', padding: '0.5rem 1rem', borderRadius: '20px' }}>
                                {results.emails.length} Valid Emails
                            </div>
                        </div>

                        {results.emails.length > 0 ? (
                            <>
                                <label>Discovered Contacts</label>
                                <div className="results-grid">
                                    {results.emails.map(email => (
                                        <div key={email} className="email-card" onClick={() => copyToClipboard(email)} style={{ cursor: 'pointer' }}>
                                            <div style={{ background: 'rgba(139, 92, 246, 0.2)', padding: '8px', borderRadius: '50%' }}>
                                                <Mail size={16} color="#c4b5fd" />
                                            </div>
                                            <span style={{ fontSize: '0.9rem', flex: 1 }}>{email}</span>
                                            <Copy size={14} color="#64748b" />
                                        </div>
                                    ))}
                                </div>

                                <div style={{ height: '1px', background: 'var(--border)', margin: '2rem 0' }}></div>

                                <div style={{ marginBottom: '2rem' }}>
                                    <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <Sparkles color="#e879f9" size={24} />
                                        Craft Your Message
                                    </h3>

                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '1.5rem' }}>
                                        {Object.entries(TEMPLATES).map(([key, t]) => (
                                            <button
                                                key={key}
                                                className={`btn ${templateKey === key ? 'btn-primary' : 'btn-secondary'}`}
                                                onClick={() => setTemplateKey(key)}
                                                style={{ justifyContent: 'flex-start', fontSize: '0.9rem' }}
                                            >
                                                {t.name}
                                            </button>
                                        ))}
                                    </div>

                                    <div className="input-wrapper">
                                        <label>Subject Line</label>
                                        <input
                                            type="text"
                                            value={formData.subject}
                                            onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                                        />
                                    </div>

                                    <div className="input-wrapper">
                                        <label>Email Body</label>
                                        <textarea
                                            rows={8}
                                            value={formData.message}
                                            onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                                            style={{ lineHeight: '1.6' }}
                                        />
                                    </div>
                                </div>

                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <button onClick={handleSend} className="btn btn-primary btn-lg" style={{ flex: 1 }}>
                                        Send Campaign ({results.emails.length} Emails) <Send size={20} />
                                    </button>
                                    <button onClick={() => {
                                        if (mode === 'batch') {
                                            setAppState('BATCH_SCRAPING');
                                            setResults(null);
                                        } else {
                                            reset();
                                        }
                                    }} className="btn btn-secondary btn-lg">
                                        Cancel
                                    </button>
                                </div>
                            </>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '3rem 0' }}>
                                <div style={{ background: 'rgba(255,255,255,0.05)', width: '80px', height: '80px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
                                    <Search size={40} color="#64748b" />
                                </div>
                                <h3>No Emails Discovered</h3>
                                <p style={{ color: '#94a3b8', maxWidth: '400px', margin: '0 auto 2rem' }}>
                                    We scanned the homepage and contact pages but couldn't find any visible email addresses.
                                </p>
                                <button onClick={() => {
                                    if (mode === 'batch') {
                                        setAppState('BATCH_SCRAPING');
                                        setResults(null);
                                    } else {
                                        reset();
                                    }
                                }} className="btn btn-secondary">
                                    <RefreshCw size={16} /> Return
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* STEP 4: SENDING / COMPLETED */}
            {(appState === 'SENDING' || appState === 'COMPLETED') && (
                <div className="glass-panel fade-in" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                    {appState === 'SENDING' ? (
                        <>
                            <div className="spinner"></div>
                            <h3>Dispatching Emails...</h3>
                            <p style={{ color: '#94a3b8' }}>Queueing messages in Redis backend.</p>
                        </>
                    ) : (
                        <>
                            <div style={{
                                background: 'linear-gradient(135deg, #10b981, #059669)',
                                width: '100px', height: '100px',
                                borderRadius: '50%',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                margin: '0 auto 2rem',
                                boxShadow: '0 10px 30px -10px rgba(16, 185, 129, 0.5)'
                            }}>
                                <CheckCircle size={50} color="white" />
                            </div>
                            <h2 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Campaign Launched!</h2>
                            <p style={{ color: '#cad5e1', fontSize: '1.2rem', marginBottom: '3rem' }}>
                                Successfully queued {results?.emails.length} emails. Check your dashboard for engagement stats.
                            </p>
                            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                                <button onClick={() => setAppState('REVIEW')} className="btn btn-secondary btn-lg">
                                    <ArrowRight size={20} transform="rotate(180)" /> Back
                                </button>
                                {mode === 'batch' && (
                                    <button onClick={() => {
                                        setAppState('BATCH_SCRAPING');
                                        setResults(null);
                                        setCampaignId(null);
                                    }} className="btn btn-secondary btn-lg">
                                        Back to Batch List
                                    </button>
                                )}
                                <button onClick={reset} className="btn btn-primary btn-lg">
                                    Start Next Campaign <ArrowRight size={20} />
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

export default App;
