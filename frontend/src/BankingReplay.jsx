import React,{useState} from 'react';
export default function BankingReplay(){
 const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[selected,setSelected]=useState('');
 async function run(){setBusy(true);setError('');try{const response=await fetch('/api/cloud-investigation/banking-replay',{method:'POST'});const data=await response.json();if(!response.ok)throw Error(data.detail||'Investigation unavailable');setResult(data);setSelected(data.incidents.find(i=>i.id==='balance')?.id||data.incidents[0]?.id||'');}catch(e){setError(e.message);}finally{setBusy(false);}}
 const incident=result?.incidents.find(i=>i.id===selected);
 return <section className="probe-section banking-replay" aria-label="Banking test and investigation">
  <span className="stage-label">TEST → FIND → EXPLAIN → ACT → VERIFY</span>
  <h2>Understand the banking test results</h2>
  <p>Replay the measurements from the completed AWS banking test. Find what went wrong, follow the explanation and see which recovery checks passed.</p>
  <p>No cloud resources are started. The research instance is terminated.</p>
  <button disabled={busy} onClick={run}>{busy?'Checking the recorded evidence…':'Run banking investigation'}</button>
  {error&&<p role="alert">{error}</p>}
  {result&&<div aria-live="polite">
   <p className="replay-summary"><b>Test completed:</b> {result.submitted_requests.toLocaleString()} payment requests and {result.ledger_matches.toLocaleString()} matching ledger records. The original test did not reliably record whether each caller received a success message.</p>
   <label className="replay-selector">Choose a finding<select value={selected} onChange={e=>setSelected(e.target.value)}>{result.incidents.map(i=><option key={i.id} value={i.id}>{i.title}</option>)}</select></label>
   {incident&&<article className="replay-finding">
    <h3>{incident.title}</h3><p><b>{incident.status}</b> · {incident.confidence}</p>
    <ol className="replay-chain">
     <li><h4>What went wrong?</h4><p>{incident.what}</p></li>
     <li><h4>Where did it start?</h4><p>{incident.location}</p></li>
     <li><h4>Why did it happen?</h4><p>{incident.mechanism}</p></li>
     <li><h4>What is the deeper cause?</h4><p>{incident.deeper_cause}</p></li>
     <li><h4>What should be done?</h4><p>{incident.recommendation}</p><p><b>Prevent it returning:</b> {incident.prevention}</p></li>
     <li><h4>Did recovery work?</h4><p>{incident.recovery}</p></li>
    </ol><p className="evidence-limit">How this was established: {incident.origin}.</p>
   </article>}
   <a className="report-download" href="/api/cloud-investigation/banking-report" download>Download the readable investigation report</a>
   <details><summary>Evidence, method and limits</summary><p>{result.mode}. {result.model_status}</p><ul>{result.limitations.map(t=><li key={t}>{t}</li>)}</ul><p>Archive checksum: <code>{result.evidence_sha256}</code></p></details>
  </div>}
 </section>;
}
