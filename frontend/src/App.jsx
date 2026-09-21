import React, { useEffect, useMemo, useRef, useState } from 'react';

const SCENARIOS = [
  'NORMAL',
  'CPU_SPIKE',
  'DATABASE_LATENCY',
  'SERVICE_OVERLOAD',
  'NETWORK_DEGRADATION',
  'CASCADING_FAILURE',
];

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = text;
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.message || payload || `HTTP ${response.status}`;
    throw new Error(String(detail));
  }

  return payload;
}

function StatusDot({ ok }) {
  return <span className={`status-dot ${ok ? 'ok' : 'bad'}`} />;
}

function App() {
  const [scenario, setScenario] = useState('DATABASE_LATENCY');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [backendOk, setBackendOk] = useState(false);
  const [error, setError] = useState('');
  const autoRunDone = useRef(false);

  const runScenario = async (selectedScenario = scenario) => {
    setLoading(true);
    setError('');
    try {
      const result = await apiFetch(
        `/api/simulate?scenario=${encodeURIComponent(selectedScenario)}&seed=42`,
        { method: 'POST' },
      );
      setData(result);
      setBackendOk(true);
    } catch (err) {
      setError(err.message || 'Unable to contact the FastAPI backend.');
      setBackendOk(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const checkBackend = async () => {
      try {
        await apiFetch('/api/health');
        if (!cancelled) setBackendOk(true);
      } catch {
        if (!cancelled) setBackendOk(false);
      }
    };

    checkBackend();
    const timer = window.setInterval(checkBackend, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (backendOk && !data && !autoRunDone.current) {
      autoRunDone.current = true;
      runScenario('DATABASE_LATENCY');
    }
  }, [backendOk, data]);

  const rootCause = data?.root_causes?.[0];
  const frontier = data?.cfao?.causal_frontier || [];
  const policy = data?.cfao?.telemetry_policy?.resolution_seconds || {};

  const graphNodes = useMemo(() => data?.graph?.nodes || [], [data]);
  const graphEdges = useMemo(() => data?.graph?.edges || [], [data]);
  const nodeScores = useMemo(
    () => Object.fromEntries((data?.affected_nodes || []).map((n) => [n.node, n.score])),
    [data],
  );

  return (
    <div className="page">
      <header className="hero">
        <div>
          <div className="eyebrow">AWS • GNN • XAI</div>
          <h1>Digital Banking Cloud Performance Analytics</h1>
          <p>Explainable anomaly detection across banking service dependencies.</p>
        </div>
        <div className="header-actions">
          <div className="badge">Baseline V1</div>
          <div className="connection"><StatusDot ok={backendOk} /> Backend {backendOk ? 'Connected' : 'Offline'}</div>
        </div>
      </header>

      <section className="control panel">
        <div className="control-group">
          <label htmlFor="scenario">Test scenario</label>
          <select
            id="scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
          >
            {SCENARIOS.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <button className="primary" onClick={() => runScenario()} disabled={loading}>
          {loading ? 'Running…' : 'Run Scenario'}
        </button>
        <button className="secondary" onClick={() => runScenario('DATABASE_LATENCY')} disabled={loading}>
          Quick Demo
        </button>
      </section>

      {error && (
        <section className="error panel">
          <strong>Backend request failed</strong>
          <p>{error}</p>
          <small>Start FastAPI with <code>uvicorn backend.main:app --reload</code> and refresh this page.</small>
        </section>
      )}

      {!data && !error && (
        <section className="empty panel">
          <h2>Ready for analysis</h2>
          <p>
            The dashboard is connected to the FastAPI backend. Choose a scenario and click
            <strong> Run Scenario</strong>.
          </p>
        </section>
      )}

      {data && (
        <main>
          <div className="cards">
            <div className="card">
              <span>Status</span>
              <strong className={data.is_anomaly ? 'danger-text' : 'success-text'}>
                {data.is_anomaly ? 'ANOMALY' : 'NORMAL'}
              </strong>
            </div>
            <div className="card">
              <span>Anomaly Score</span>
              <strong>{(Number(data.anomaly_score || 0) * 100).toFixed(1)}%</strong>
            </div>
            <div className="card">
              <span>Root Cause</span>
              <strong>{rootCause?.node || 'None'}</strong>
            </div>
            <div className="card">
              <span>Source</span>
              <strong>{data.source || 'simulation'}</strong>
            </div>
          </div>

          <div className="scenario-strip panel">
            <div><span>Transaction</span><strong>{data.transaction?.type || '—'}</strong></div>
            <div><span>Scenario</span><strong>{data.scenario || '—'}</strong></div>
            <div><span>Trigger</span><strong>{data.cfao?.trigger || '—'}</strong></div>
          </div>

          <div className="grid">
            <section className="panel">
              <div className="panel-title"><h2>Affected components</h2><span>Node anomaly scores</span></div>
              {(data.affected_nodes || []).slice(0, 7).map((node) => (
                <div className="metric-row" key={node.node}>
                  <div>
                    <strong>{node.node}</strong>
                    <small>{node.node_type}</small>
                  </div>
                  <div className="bar-wrap"><div className="bar" style={{ width: `${Math.min(100, Number(node.score || 0) * 100)}%` }} /></div>
                  <b>{(Number(node.score || 0) * 100).toFixed(1)}%</b>
                </div>
              ))}
            </section>

            <section className="panel">
              <div className="panel-title"><h2>Root cause</h2><span>Ranked evidence</span></div>
              {(data.root_causes || []).map((root, index) => (
                <div className={`root-item ${index === 0 ? 'selected' : ''}`} key={root.node}>
                  <div><strong>#{index + 1} {root.node}</strong><small>{root.reason}</small></div>
                  <b>{(Number(root.score || 0) * 100).toFixed(1)}%</b>
                </div>
              ))}
              <div className="reason-box">
                <strong>Dependency path</strong>
                <div className="path">{data.explanation?.dependency_path?.join(' → ') || 'No path available'}</div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-title"><h2>Explainable AI</h2><span>Feature importance</span></div>
              {(data.explanation?.important_features || []).map((item) => (
                <div className="metric-row compact" key={item.feature}>
                  <span>{item.feature}</span>
                  <div className="bar-wrap"><div className="bar" style={{ width: `${Math.min(100, Number(item.importance || 0) * 100)}%` }} /></div>
                  <b>{Number(item.importance || 0).toFixed(3)}</b>
                </div>
              ))}
            </section>

            <section className="panel">
              <div className="panel-title"><h2>Infrastructure graph</h2><span>{graphNodes.length} nodes · {graphEdges.length} edges</span></div>
              <div className="graph-view">
                {graphNodes.map((node) => {
                  const score = Number(nodeScores[node.id] || 0);
                  const isRoot = node.id === rootCause?.node;
                  return (
                    <div className={`graph-node ${score >= 0.5 ? 'hot' : ''} ${isRoot ? 'root' : ''}`} key={node.id}>
                      <strong>{node.label}</strong>
                      <small>{node.type}</small>
                      {score > 0 && <b>{(score * 100).toFixed(0)}%</b>}
                    </div>
                  );
                })}
              </div>
              <div className="path"><strong>Flow:</strong> API Gateway → Payment Service → EC2-01 → RDS-01</div>
            </section>

            <section className="panel full">
              <div className="panel-title"><h2>TC-CFAO</h2><span>Adaptive telemetry policy</span></div>
              <p className="muted">Focus higher-resolution monitoring on the suspected causal frontier.</p>
              <div className="frontier">{frontier.map((node) => <span key={node}>{node}</span>)}</div>
              <div className="policy-grid">
                {Object.entries(policy).map(([node, seconds]) => (
                  <div className={`policy-item ${frontier.includes(node) ? 'focused' : ''}`} key={node}>
                    <span>{node}</span>
                    <b>{seconds}s</b>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
