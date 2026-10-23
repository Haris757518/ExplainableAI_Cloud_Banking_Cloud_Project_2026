import React,{useState,useEffect} from 'react';
import './probe.css';
import BankingReplay from './BankingReplay.jsx';
export default function CloudOverview({onResearch}){
 const [data,setData]=useState(null),[error,setError]=useState('');
 useEffect(()=>{fetch('/api/cloud-investigation/overview').then(r=>{if(!r.ok)throw Error('Monitoring status unavailable');return r.json();}).then(setData).catch(e=>setError(e.message));},[]);
 const measured=data?.monitoring_status==='recorded_aws_execution',workload=data?.workload;
 const metrics=measured?[
  ['Banking services','banking_services','Ready pods in the retained deployment snapshot'],
  ['Active issues','active_issues','No live incident count is measured'],
  ['Demo payment round trip','payment_latency_ms','Milliseconds; one transfer, including its redirect to history'],
  ['Verified demo transfers','verified_transfers','Matched ledger, history and measured service-call trace']
 ]:[['Banking services','banking_services'],['Active issues','active_issues'],['Payment latency','payment_latency_ms'],['Transaction success','transaction_success_percent']];
 return <main className="probe-layout">
  <section className="cloud-intro"><span className="stage-label">{measured?'AWS BANKING EXECUTION VERIFIED':'BANKING INVESTIGATION'}</span>
   <h2>Banking Investigation Monitor</h2><p>Detect a problem, investigate its measured cause, recommend a response and verify recovery.</p>
   <div className="connection-state"><b>{measured?'Bank of Anthos · AWS · measured execution':`AWS storage ${data?.aws.storage==='uploaded_and_verified'?'verified':'not verified'}`}</b><span>{measured?'Retained measurements · not a live health feed':'Banking workload not yet verified'}</span></div>
   {workload&&<p>Evidence recorded {new Date(workload.recorded_at).toLocaleString('en-IN',{timeZone:'Asia/Kolkata'})} IST.</p>}
   {error&&<p role="alert">{error}</p>}
  </section>
  <BankingReplay/>
  <section className="health-metrics" aria-label="Measured banking health">{metrics.map(([title,key,caption])=><article key={key}><span>{title}</span><strong>{data?.summary[key]??'Unknown'}</strong><small>{caption||'Requires executed banking workload telemetry'}</small></article>)}</section>
  <section className="probe-section"><h2>{measured?'Verified first AWS banking transfer':'Current banking investigation'}</h2>
   <p>{data?.explanation||'Reading monitoring status…'}</p>
   {workload&&<><ol className="why-chain"><li><b>Payment executed</b><p>A demo payment ran inside Bank of Anthos on the AWS research instance.</p></li><li><b>Ledger and history agree</b><p>Transaction {workload.transaction_id} has one matching new ledger record and is present in transaction history.</p></li><li><b>Service call measured</b><p>The payment request has an actual linked HTTP client span to the ledger-writing service.</p></li></ol><p className="evidence-limit">This first-transfer check establishes execution. The investigation above and the research results provide the separate incident, correction and recovery evidence.</p><details><summary>Technical details and evidence location</summary><p>{workload.trace_coverage}</p><p>Retained, checksum-verified evidence: <code>{workload.evidence_location}</code></p></details></>}
   <button onClick={onResearch}>Explore recorded root-cause investigations</button>
  </section>
  <section className="probe-section"><h2>Workload setup and spending</h2>
   <p>{measured?'The research instance has been terminated after exporting the measurements and final database backup to D:. The approved experiment limit was $5 and at most two hours. The dashboard displays retained evidence.':'No executed banking evidence is verified yet. Existing public bank statistics cannot establish internal service root causes.'}</p>
   <h3>What still needs validation</h3><ul>{data?.blockers.map(b=><li key={b}>{b}</li>)}</ul>
   <p>Published Monzo and Starling statistics, RCAEval research recordings, and actual AWS banking measurements retain separate source identities.</p>
  </section>
 </main>;
}
