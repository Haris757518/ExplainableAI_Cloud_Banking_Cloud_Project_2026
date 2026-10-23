import React from 'react';
import './probe.css';
import BankingReplay from './BankingReplay.jsx';
import LiveBanking from './LiveBanking.jsx';
export default function CloudOverview(){
 return <main className="probe-layout"><LiveBanking/><details className="probe-section"><summary>Recorded tests</summary><BankingReplay/></details></main>;
}
