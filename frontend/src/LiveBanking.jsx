import React,{useEffect,useState} from 'react';
export default function LiveBanking(){
 const [data,setData]=useState(null),[history,setHistory]=useState([]),[action,setAction]=useState({}),[sending,setSending]=useState(false),[points,setPoints]=useState([]),[fault,setFault]=useState('fault');
 async function control(operation){setSending(true);try{const r=await fetch('/api/live-banking/action/'+operation,{method:'POST'});const v=await r.json();setAction(r.ok?v:{status:'failed',message:v.detail||'Action unavailable'});}catch{setAction({status:'failed',message:'Connection unavailable'});}finally{setSending(false);}}
 useEffect(()=>{let active=true;const poll=()=>fetch('/api/live-banking/action').then(r=>r.json()).then(v=>{if(active&&v.status)setAction(v);}).catch(()=>{});const timer=setInterval(poll,3000);return()=>{active=false;clearInterval(timer);};},[]);
 useEffect(()=>{let active=true;const read=()=>fetch('/api/live-banking/status').then(r=>{if(!r.ok)throw Error();return r.json();}).then(v=>{if(active){setData(v);if(Number.isFinite(v.p95_ms))setPoints(previous=>previous.at(-1)?.time===v.received_at?previous:[...previous,{time:v.received_at,value:v.p95_ms,threshold:v.threshold_ms}].slice(-90));setHistory(previous=>{if(previous.at(-1)?.status===v.status)return previous;return [...previous,{status:v.status,time:Date.now()}].slice(-6);});}}).catch(()=>{if(active)setData({status:'disconnected',explanation:'Live monitoring connection is unavailable.'});});read();const timer=setInterval(read,3000);return()=>{active=false;clearInterval(timer);};},[]);
 const labels={normal:'Normal',anomaly:'Anomaly',stale:'Paused',not_connected:'Offline',disconnected:'Offline',warming_up:'Learning baseline',insufficient_data:'Collecting',invalid_baseline:'Check baseline'};
 const fresh=data?.p95_ms!=null;
 const blocked=data?.cause?.startsWith('Database blocking');
 return <section className="probe-section live-simple" aria-label="Live AWS monitoring">
  <div className="live-heading"><h2>Live AWS monitoring</h2><span className={'live-state '+(data?.status||'connecting')} role="status">{labels[data?.status]||'Connecting'}</span></div>
  <p>{fresh?'AWS banking payments   updates automatically':data?.status==='stale'?'Monitoring paused. Waiting for fresh AWS data.':data?.status==='warming_up'?'Measuring normal payments ':'Waiting for the AWS connection.'}</p>
  <div className="demo-controls"><button disabled={sending||action.status==='running'} onClick={()=>control('run')}>Run test</button><select aria-label="Fault type" value={fault} onChange={e=>setFault(e.target.value)} disabled={sending||action.status==='running'}><option value="fault">Database lock   30 seconds</option><option value="fault-cpu">CPU pressure   30 seconds</option></select><button disabled={sending||action.status==='running'||data?.status!=='normal'} onClick={()=>control(fault)}>Inject fault</button><button disabled={sending||action.status==='running'||!fresh} onClick={()=>control('verify')}>Verify recovery</button></div>
  {action.message&&<p role="note">{action.message}</p>}
  {fresh&&<><div className="health-metrics"><article><span>Payment latency</span><strong>{data.p95_ms} <small>ms</small></strong></article><article><span>Alert threshold</span><strong>{data.threshold_ms} <small>ms</small></strong></article><article><span>Recent requests</span><strong>{data.requests}</strong></article></div>
  <LiveChart points={points} live={fresh}/>
  {data.status==='anomaly'&&<div className="safety-note"><p><b>Cause:</b> {blocked?'Database blocking observed.':'Needs investigation.'}</p><p><b>Next:</b> {blocked?'Inspect the blocking transaction; verify balances after it clears.':'Check service and database measurements.'}</p></div>}
  <small>Updated {new Date(data.received_at*1000).toLocaleTimeString()}</small></>}
  {data?.investigation&&<section className="live-finding"><h3>Latest supported finding</h3><small>Observed {new Date(data.investigation.as_of*1000).toLocaleTimeString()}</small><p><b>GNN:</b> {data.investigation.gnn.status==='evaluated'?'Symptom rank: '+data.investigation.gnn.ranking.slice(0,2).map(r=>r.service).join('   '):'Waiting for compatible measurements'}</p>{data.investigation.probe_xai.causes.length?data.investigation.probe_xai.causes.map(c=><div key={c.service}><p><b>PROBE-XAI:</b> {c.service}   {c.cause}</p><p><b>Deeper cause:</b> {c.deeper_cause}</p><p><b>Action:</b> {c.recommendation}</p></div>):<p>Deeper cause not established by current evidence.</p>}</section>}
  <details><summary>Details</summary><p>Baseline alert followed by GNN inference on live measurements and direct-evidence PROBE-XAI investigation. The frozen model comes from the prior AWS study; live ranking accuracy is not established.</p><p>Faster responses alone do not confirm financial recovery.</p>{fresh&&<p>{data.cause}</p>}<ol>{history.map((item,i)=><li key={i}>{new Date(item.time).toLocaleTimeString()}   {labels[item.status]||item.status}</li>)}</ol>{data?.instance_id&&<small>Instance: {data.instance_id}</small>}</details>
 </section>;
}

function LiveChart({points,live}){
 const w=760,h=230,left=55,right=18,top=20,bottom=35;
 const max=Math.max(100,...points.flatMap(p=>[p.value,p.threshold]))*1.15;
 const first=points[0]?.time||0,last=points.at(-1)?.time||first+1;
 const x=t=>left+(t-first)/Math.max(1,last-first)*(w-left-right);
 const y=v=>h-bottom-v/max*(h-top-bottom);
 const line=key=>points.map(p=>`${x(p.time)},${y(p[key])}`).join(' ');
 return <figure style={{margin:'24px 0'}} aria-label="Live payment latency graph"><figcaption>Payment latency <small>  blue line   threshold   dashed</small></figcaption><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Measured payment latency and alert threshold over time" style={{width:'100%',height:'auto',maxHeight:280}}>
 {[0,.5,1].map(f=><g key={f}><line x1={left} x2={w-right} y1={y(max*f)} y2={y(max*f)} stroke="#e2e8f0"/><text x={left-8} y={y(max*f)+4} textAnchor="end" fontSize="11" fill="#64748b">{Math.round(max*f)}</text></g>)}
 <text x="5" y="12" fontSize="11" fill="#64748b">ms</text>
 {points.length>0&&<><polyline points={line('threshold')} fill="none" stroke="#d97706" strokeWidth="2" strokeDasharray="7 5"/><polyline points={line('value')} fill="none" stroke="#2563eb" strokeWidth="3"/>{points.filter(p=>p.value>p.threshold).map(p=><circle key={p.time} cx={x(p.time)} cy={y(p.value)} r="4" fill="#dc2626"/>)}<text x={left} y={h-8} fontSize="11" fill="#64748b">{new Date(first*1000).toLocaleTimeString()}</text><text x={w-right} y={h-8} textAnchor="end" fontSize="11" fill="#64748b">{new Date(last*1000).toLocaleTimeString()}</text></>}
 </svg>{points.length<2&&<small>Collecting live graph points </small>}</figure>;
}
