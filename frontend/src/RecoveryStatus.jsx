import React from 'react';
export default function RecoveryStatus({recovery}){
 const labels={recovered:'Recovered',still_abnormal:'Still abnormal',not_verified:'Not verified'};
 return <section className="probe-section"><h2>Did it work?</h2><strong className="recovery-state">{labels[recovery.status]||'Not verified'}</strong><p>{recovery.reason}</p><p>A recommendation does not count as a fix. Recovery requires an approved intervention, later performance measurements and successful transaction-integrity checks.</p></section>
}
