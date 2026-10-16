import {ResearchEvidence} from './ResearchEvidence.jsx';
import ResearchWorkbench, {IncidentIntelligence} from './ResearchWorkbench.jsx';
import React, { useEffect, useMemo, useState } from 'react';

const SCENARIOS = ['NORMAL','CPU_SPIKE','DATABASE_LATENCY','SERVICE_OVERLOAD','NETWORK_DEGRADATION','CASCADING_FAILURE'];
const TX_TYPES = ['UPI_PAYMENT','FUND_TRANSFER','CARD_PAYMENT','BALANCE_INQUIRY','BILL_PAYMENT'];

async function apiFetch(path, options={}) {
  const response = await fetch(path, { ...options, headers: { Accept:'application/json', ...(options.headers||{}) } });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }
  if (!response.ok) {
    const detail = payload?.detail?.message || payload?.detail || payload?.message || payload || `HTTP ${response.status}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return payload;
}

function Status({ok,label}) { return <span className="status"><i className={ok?'dot ok':'dot'}></i>{label}</span>; }

function Graph({nodes=[],edges=[],scores={},root,transactionType='UPI_PAYMENT',path=[], mode='simulation'}){
  const layerOrder={transaction:0,application:1,service:1,compute:2,data:3,messaging:3,infrastructure:3};
  const levels={};
  nodes.forEach(n=>{const l=layerOrder[n.layer]??1;(levels[l]??=[]).push(n)});
  Object.values(levels).forEach(arr=>arr.sort((a,b)=>{
    const ai=path.indexOf(a.id), bi=path.indexOf(b.id);
    if(ai>=0&&bi>=0)return ai-bi; if(ai>=0)return -1; if(bi>=0)return 1; return a.id.localeCompare(b.id)
  }));
  const positions={};
  const isGrid = mode === 'alibaba' || nodes.length > 15;
  if (isGrid) {
    const cols = Math.ceil(Math.sqrt(nodes.length));
    nodes.forEach((n, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        positions[n.id] = [150 + col * 200, 100 + row * 100];
    });
  } else {
    Object.entries(levels).forEach(([l,arr])=>arr.forEach((n,i)=>{positions[n.id]=[110+Number(l)*190,90+i*90]}));
  }
  const width = isGrid ? 150 + Math.ceil(Math.sqrt(nodes.length)) * 200 : Math.max(820,120+Math.max(...Object.values(levels).map((a)=>a.length),1)*0+3*190);
  const height = isGrid ? 100 + Math.ceil(nodes.length / Math.ceil(Math.sqrt(nodes.length))) * 100 : Math.max(300,100+Math.max(...Object.values(levels).map((a)=>a.length),1)*90);
  return <svg className="graph" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Transaction-conditioned infrastructure graph">
    <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z"/></marker></defs>
    {edges.map((e,i)=>{const a=positions[e.source],b=positions[e.target];if(!a||!b)return null;const active=path.includes(e.source)&&path.includes(e.target);const secondary=path.includes(e.source)||path.includes(e.target);return <g key={i}><line x1={a[0]+55} y1={a[1]} x2={b[0]-55} y2={b[1]} className={active?'edge active':secondary?'edge secondary':'edge'} markerEnd="url(#arrow)"/><text x={(a[0]+b[0])/2} y={(a[1]+b[1])/2-7} className="edge-label">{e.relationship}</text></g>})}
    {nodes.map(n=>{const p=positions[n.id];if(!p)return null;const score=Number(scores[n.id]||0);const hot=score>=.5,isRoot=n.id===root;return <g key={n.id} transform={`translate(${p[0]},${p[1]})`}><rect x="-58" y="-29" width="116" height="58" rx="12" className={isRoot?'node root':hot?'node hot':'node'}/><text textAnchor="middle" y="-4" className="node-title">{n.label}</text><text textAnchor="middle" y="14" className="node-sub">{n.type}</text>{score>0&&<text textAnchor="middle" y="38" className="score">deviation {score.toFixed(3)}</text>}</g>})}
    {path.length > 0 && mode !== 'alibaba' && <g transform={`translate(${Math.min(width-130,120)},${height-30})`}><rect x="-66" y="-17" width="132" height="34" rx="10" className="tx-node"/><text textAnchor="middle" y="4" className="tx-title">{transactionType}</text></g>}
  </svg>;
}

function Trends({series={}}){
 const rows=Object.entries(series).flatMap(([node,metrics])=>Object.entries(metrics).map(([metric,points])=>({node,metric,points:points.filter(p=>Number.isFinite(p.value)&&Number.isFinite(p.timestamp_ms))}))).filter(r=>r.points.length>1).slice(0,12);
 return <section className="panel full"><h2>Observed metric histories</h2>{!rows.length&&<p>No measured history is available.</p>}{rows.map(({node,metric,points})=>{
 const min=Math.min(...points.map(p=>p.value)),max=Math.max(...points.map(p=>p.value)),first=points[0].timestamp_ms,last=points.at(-1).timestamp_ms;
 const coords=points.map(p=>`${10+580*(p.timestamp_ms-first)/(last-first||1)},${90-75*(p.value-min)/(max-min||1)}`).join(' ');
 return <div key={node+metric}><b>{node} · {metric}</b><svg viewBox="0 0 600 110" role="img" aria-label={`${node} ${metric} observed history`} style={{width:'100%',maxHeight:140}}><polyline points={coords} fill="none" stroke="#59d8bd" strokeWidth="2"/><text x="10" y="108" fill="currentColor">min {min.toFixed(3)} · max {max.toFixed(3)} · {points.length} recorded points</text></svg><small>Timestamp range (source milliseconds): {first} to {last}. Lines connect recorded points; gaps are not measurements.</small></div>})}</section>
}

function App(){
  const [mode,setMode]=useState('alibaba');
  const [view,setView]=useState('Incident Investigation');
  const [data,setData]=useState(null);
  const [health,setHealth]=useState(null);
  const [aws,setAws]=useState(null);
  const [db,setDb]=useState(null);
  const [cloudDb,setCloudDb]=useState(null);
  const [study,setStudy]=useState(null);
  const [refined,setRefined]=useState(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  useEffect(()=>{apiFetch('/api/research/observed').then(setStudy).catch(()=>{});apiFetch('/api/health').then(setHealth).catch(e=>setError(e.message))},[]);
  const run=async()=>{
    setLoading(true);setError('');setData(null);setRefined(null);
    try{
      if(mode==='aws'){
        const status=await apiFetch('/api/aws/status');setAws(status);
        if(!status.connected)throw new Error(status.error||'AWS session unavailable.');
      }
      setData(await apiFetch(mode==='aws'?'/api/aws/analyze':'/api/alibaba/analyze',{method:'POST'}));
    }catch(e){setError(e.message)}finally{setLoading(false)}
  };
  const inspectCloudDb=async()=>{setLoading(true);setError('');try{const id=data?.aws_discovery?.ec2?.[0]?.id;if(!id)throw new Error('Collect AWS resources first.');setCloudDb(await apiFetch(`/api/aws/database/diagnostics?instance_id=${encodeURIComponent(id)}`,{method:'POST'}))}catch(e){setError(e.message)}finally{setLoading(false)}};
  const diagnose=async()=>{setLoading(true);setError('');try{setDb(await apiFetch('/api/diagnostics/database'))}catch(e){setError(e.message)}finally{setLoading(false)}};
  const refine=async()=>{setLoading(true);setError('');try{setRefined(await apiFetch(`/api/aws/refine?run_id=${data.run_id}`,{method:'POST'}))}catch(e){setError(e.message)}finally{setLoading(false)}};
  const assessment=data?.assessment||{};
  const root=data?.root_causes?.[0];
  const scores=Object.fromEntries((data?.affected_nodes||[]).map(n=>[n.node,n.score]));
  const evidence=assessment.evidence||[];
  const observations=(data?.graph?.telemetry||[]).flatMap(t=>t.observed_metrics.map(metric=>({node:t.node_id,metric,value:t[metric]})));
  return <div className="shell">
    <header className="top"><div><div className="eyebrow">MEASURED DATA · EXPLAINABLE DIAGNOSIS</div><h1>Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks</h1><p>Trace latency, inspect database evidence, and decide what to measure next.</p></div><div className="badges"><Status ok={health?.status==='ok'} label={health?.status==='ok'?'Backend connected':'Backend unavailable'}/><span className="badge">Observed data only</span></div></header>
    <nav className="primary-nav" aria-label="Primary navigation">{['Incident Investigation','Live Monitoring','Research Evidence'].map(v=><button key={v} aria-current={view===v?'page':undefined} onClick={()=>{setView(v);if(v==='Live Monitoring'){setMode('aws');setData(null)}}}>{v}</button>)}</nav>
    <section className="toolbar"><label>Data source<select value={mode} disabled={loading} onChange={e=>{setMode(e.target.value);setData(null);setError('');setRefined(null)}}><option value="alibaba">Alibaba production trace</option><option value="aws">Live AWS telemetry</option><option value="microsoft">Microsoft labelled benchmark</option><option value="rcaeval">RCAEval recorded incidents</option></select></label>{(mode==='alibaba'||mode==='aws')&&<button onClick={run} disabled={loading||mode==='microsoft'||mode==='rcaeval'}>{loading?'Collecting evidence…':'Analyze observed data'}</button>}<button className="ghost" onClick={diagnose} disabled={loading}>Inspect analytics database</button><span className="toolbar-hint">{mode==='lab'?'Isolated controlled faults; independently measured telemetry.':mode==='alibaba'?'Production microservices; no banking or failure labels.':mode==='microsoft'?'Official expert-labelled series; no service graph.':mode==='rcaeval'?'Published recorded controlled cases; chronological replay.':'Read-only EC2, RDS and CloudWatch. Requires an active AWS session.'}</span></section>
    {error&&<section className="error"><b>{mode==='aws'?'Cloud resource monitoring unavailable.':'Evidence unavailable'}</b><p>{error}</p></section>}
    {mode==='aws'&&aws&&<section className="panel mini"><div><span>AWS credentials</span><b>{aws.connected?'Authenticated':'Unavailable'}</b></div><div><span>Region</span><b>{aws.region}</b></div><div><span>Resource access</span><b>{error?'Unavailable':data?'Measurements collected':'Not checked'}</b></div></section>}
    {(mode==='microsoft'||mode==='rcaeval')&&<ResearchWorkbench source={mode} view={view}/>}
    {view==='Research Evidence'&&mode!=='microsoft'&&mode!=='rcaeval'&&<ResearchEvidence/>}
    {view!=='Research Evidence'&&mode!=='microsoft'&&mode!=='rcaeval'&&mode!=='lab'&&!data&&<section className="empty"><h2>Select a source and collect evidence</h2><p>Missing measurements stay unknown. No simulated telemetry is used.</p></section>}
    {view!=='Research Evidence'&&data&&<>
      {data.assessment?.incident&&<IncidentIntelligence incident={data.assessment.incident}/>}
      {mode==='aws'&&data.aws_discovery?.ec2?.length===1&&<section className="panel"><h2>Collect discriminating AWS evidence</h2><button onClick={inspectCloudDb} disabled={loading}>Inspect PostgreSQL on EC2</button><button className="ghost" onClick={refine} disabled={loading||!data.cfao?.causal_frontier.length}>Recollect frontier evidence</button><p>Read-only collection. New evidence is compared with its original measured reference; no resource changes are executed.</p>{refined&&<p>{refined.note} New observations: {refined.new_observations_available?'yes':'no'}.</p>}</section>}
      <details className="panel"><summary>Source-specific metrics, topology and reconstruction evidence</summary>
      <section className="cards"><article><span>Assessment</span><strong className={data.is_anomaly?'danger':''}>{assessment.status?.replaceAll('_',' ')||'Unknown'}</strong></article><article><span>Relative deviation index</span><strong>{data.anomaly_score==null?'Unknown':Number(data.anomaly_score).toFixed(3)}</strong><small>Not a failure probability</small></article><article><span>Leading candidate</span><strong>{root?.node?.slice(0,18)||'Not established'}</strong></article><article><span>Measured series with history</span><strong>{assessment.eligible_metric_series??0}</strong></article></section>
      <section className="panel"><h2>Evidence and limits</h2><p>{data.explanation?.narrative}</p><p>{assessment.gnn_reason}</p>{(assessment.measurement_gaps||[]).map((g,i)=><p key={i}>{g}</p>)}<p>{data.graph?.metadata?.application_timing_scope}</p><p>Ground-truth failure labels: {assessment.ground_truth_available?'available':'unavailable'}. Causal confirmation: {assessment.causal_confirmation?'confirmed':'pending'}.</p><p>Latest eligible observation (source milliseconds): {Math.max(...evidence.map(e=>e.timestamp_ms),0)||"unavailable"}. Collection interval: {(data.aws_collection?.period_seconds??(data.graph?.metadata?.window_ms/1000))||"unknown"} seconds.</p><p>{data.aws_collection?.exclusion_policy?.reason}</p><p>Source: {data.source}. {data.graph?.metadata?.timestamp_kind==='relative_trace_milliseconds'?'Trace times are relative milliseconds, not calendar dates.':''}</p></section>
      <div className="grid"><Trends series={data.graph?.metadata?.series}/><section className="panel full"><h2>Freshness and evidence availability</h2><p>{assessment.freshness_rule}</p><p>Excluded stale or future series: {assessment.excluded_series?.length||0}. Recovery requires subsequent new measurements and is not inferred from a repeated overlapping window.</p>{(assessment.excluded_series||[]).map((e,i)=><p key={i}>{e.node} · {e.metric}: {e.freshness}, age {Math.round(e.age_seconds)} seconds</p>)}</section>
        <section className="panel full"><div className="title"><h2>Observed dependency graph</h2><span>{data.graph?.nodes.length} nodes · {data.graph?.edges.length} relationships</span></div><Graph nodes={data.graph?.nodes} edges={data.graph?.edges} scores={scores} root={root?.node} path={data.transaction?.path||[]} mode={mode}/><small>AWS dependencies appear only when explicitly configured. Alibaba DB nodes are identified by recorded DB call protocol.</small></section>
        <section className="panel"><h2>Suspected causes</h2>{!data.root_causes.length&&<p>No candidate is supported by the available history.</p>}{data.root_causes.map(r=><div className="root" key={r.node}><div><b>{r.node}</b><p>{r.reason}</p>{r.evidence.map((v,i)=><p key={i}>{v}</p>)}</div></div>)}</section>
        <section className="panel"><h2>Next evidence to collect</h2>{(assessment.next_evidence||[]).map((q,i)=><p key={i}>{q}</p>)}<div className="chips">{(data.cfao?.causal_frontier||[]).map(n=><span key={n}>{n.slice(0,18)}</span>)}</div><p>Sampling remains at the source's available resolution. Savings have not been measured.</p>{mode==='aws'&&data.aws_discovery?.ec2?.length===1&&<button onClick={inspectCloudDb} disabled={loading}>Inspect PostgreSQL on EC2</button>}{mode==='aws'&&<button onClick={refine} disabled={loading||!data.cfao?.causal_frontier.length}>Recollect frontier evidence</button>}{refined&&<p>{refined.note} New observations: {refined.new_observations_available?'yes':'no'}. {(refined.followup||[]).map(e=>`${e.metric}: ${e.status} (${e.new_points} newer points)`).join('; ')}</p>}</section>
        {assessment.gnn_evidence?.status==='evaluated'&&<section className="panel full"><h2>Measured-data GNN explanation</h2><p>Held-out window reconstruction MSE: {Number(assessment.gnn_evidence.latest_masked_mse).toFixed(4)} from {assessment.gnn_evidence.latest_measured_targets} measured features.</p><p>{assessment.gnn_evidence.interpretation}</p>{assessment.gnn_evidence.contributions.slice(0,6).map((e,i)=><div className="metric" key={i}><span title={e.node}>{e.node.slice(0,14)} · {e.feature}</span><b>{Number(e.squared_error).toFixed(4)}</b></div>)}</section>}
        <section className="panel full"><h2>Temporal explanation</h2><p>Rule: positive robust z ≥ 3.5; scale=max(1.4826×MAD, 5% of median, 0.000001). This identifies relative changes, not verified incidents.</p><div style={{overflowX:'auto'}}><table style={{width:'100%',textAlign:'left'}}><thead><tr><th>Resource</th><th>Measured signal</th><th>Latest</th><th>Earlier median</th><th>Robust deviation</th><th>Earlier windows</th></tr></thead><tbody>{evidence.slice(0,30).map((e,i)=><tr key={i}><td title={e.node}>{e.node.slice(0,18)}</td><td>{e.metric}</td><td>{Number(e.latest).toFixed(3)}</td><td>{Number(e.reference_median).toFixed(3)}</td><td>{Number(e.robust_z).toFixed(2)}</td><td>{e.history_count}</td></tr>)}</tbody></table></div>{!evidence.length&&<p>At least six observations per resource and metric are needed.</p>}</section>
        <section className="panel full"><h2>Measured values</h2><div style={{overflowX:'auto'}}><table style={{width:'100%',textAlign:'left'}}><thead><tr><th>Resource</th><th>Metric</th><th>Value</th></tr></thead><tbody>{observations.slice(0,80).map((e,i)=><tr key={i}><td title={e.node}>{e.node.slice(0,18)}</td><td>{e.metric}</td><td>{e.value==null?'Unknown':Number(e.value).toFixed(3)}</td></tr>)}</tbody></table></div></section>
      </div>
      </details>
    </>}
    {view==='Research Evidence'&&study&&<section className="panel"><h2>Separate Alibaba GNN study (original observed slice)</h2><p>{study.rows_scanned} source rows; {study.measured_calls} recorded calls; {study.gnn.train_windows} training, {study.gnn.validation_windows} validation and {study.gnn.test_windows} held-out windows.</p><p>Held-out reconstruction MSE: {Number(study.gnn.test_masked_mse).toFixed(4)}. Training-mean baseline: {Number(study.gnn.train_mean_baseline_test_mse).toFixed(4)}.</p><p>{study.gnn.limitations}</p><p>This GNN is evaluated separately; the current diagnosis uses the measured-series deviation method.</p></section>}
    {cloudDb&&<section className="panel"><h2>Live PostgreSQL on EC2</h2><p>Source: AWS Systems Manager, read-only system views. Observed: {cloudDb.observation.observed_at}.</p><p>Blocked sessions: {cloudDb.observation.blocked_sessions}. I/O timing: {cloudDb.observation.track_io_timing}.</p><p>Active/idle client groups: {cloudDb.observation.activity.length}. This snapshot does not prove absence of intermittent problems.</p><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(cloudDb.observation.activity,null,2)}</pre><p>{cloudDb.limitations}</p><p>Investigation: {cloudDb.investigation?.cause_status}. {cloudDb.investigation?.limitation}</p>{(cloudDb.investigation?.findings||[]).map((f,i)=><p key={i}>{f.kind}: {f.finding}. Supports: {f.supports||"not established"}. Contradicts: {f.contradicts||"not established"}.</p>)}</section>}
    {db&&<section className="panel"><h2>Database investigation</h2><p>Analytics storage: {db.analytics_store.connected?'connected':'unavailable'}. Read probe: {db.analytics_store.ping_ms??'unknown'} ms. Dashboard queries: {db.analytics_store.dashboard_query_ms??'unknown'} ms.</p><p>{db.analytics_store.note}</p><p>Monitored application database: {db.monitored_database.status}. {db.monitored_database.next_step||db.monitored_database.error}</p>{db.monitored_database.status==='observed'&&<><p>Blocked sessions: {db.monitored_database.blocked_sessions}</p><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(db.monitored_database.activity,null,2)}</pre><p>{db.monitored_database.limitations}</p></>}</section>}
    <footer>Research hypothesis: evidence-constrained causal-frontier observability. Candidate ranking is not causal proof.</footer>
  </div>
}
export default App;
