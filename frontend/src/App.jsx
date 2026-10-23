import React,{useState} from 'react';
import CloudOverview from './CloudOverview.jsx';
import ProbeResearch from './ProbeResearch.jsx';

export default function App(){const [tab,setTab]=useState('Banking Investigation');return <div className="shell"><header className="top"><div><span className="eyebrow">BANKING MONITOR</span><h1>Cloud Banking</h1></div><span className="badge">Research demo</span></header><nav className="primary-nav" aria-label="Primary navigation">{['Banking Investigation','Research & Validation'].map(name=><button key={name} aria-current={name===tab?'page':undefined} onClick={()=>setTab(name)}>{name}</button>)}</nav>{tab==='Banking Investigation'?<CloudOverview onResearch={()=>setTab('Research & Validation')}/>:<ProbeResearch/>}</div>}
