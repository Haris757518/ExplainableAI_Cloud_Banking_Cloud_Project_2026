"""Use quarter-addressed reports embedded by the official quarter selector.

The server-rendered initial table can disagree with its displayed heading.
Dates therefore come from validated report filenames, never that initial label.
"""
from .parser import number, Tables
from .schema import Observation, SOURCES
from html.parser import HTMLParser
from datetime import date, timedelta
import json
import re

class ReportData(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.active=False; self.parts=[]; self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag=='script' and dict(attrs).get('id')=='__NEXT_DATA__': self.active=True
    def handle_endtag(self, tag):
        if tag=='script': self.active=False
    def handle_data(self, data):
        if self.active: self.parts.append(data)

FIELDS={
    'mobileUptime':('Mobile','availability','percent'),
    'mobileDowntime':('Mobile','downtime','percent'),
    'mobilePisp':('Payment Initiation (Mobile)','latency','milliseconds'),
    'mobileAisp':('Account Information (Mobile)','latency','milliseconds'),
    'mobileErrorRate':('Mobile','errors','percent'),
    'partnerUptime':('Dedicated','availability','percent'),
    'partnerDowntime':('Dedicated','downtime','percent'),
    'partnerPisp':('Payment Initiation (Dedicated)','latency','milliseconds'),
    'partnerAisp':('Account Information (Dedicated)','latency','milliseconds'),
    'cbpii':('Funds Check (Dedicated)','latency','milliseconds'),
    'errorRate':('Dedicated','errors','percent'),
    'openbankingUptime':('Open Banking','availability','percent'),
    'openbankingDowntime':('Open Banking','downtime','percent'),
    'openbankingPisp':('Payment Initiation (Open Banking)','latency','milliseconds'),
    'openbankingAisp':('Account Information (Open Banking)','latency','milliseconds'),
    'openbankingCbpii':('Funds Check (Open Banking)','latency','milliseconds'),
    'openbankingErrorRate':('Open Banking','errors','percent'),
}

def extract(html, retrieved_at, checksum):
    payload=ReportData(html)
    if not payload.parts: raise ValueError('Official quarter-selector report payload unavailable')
    reports=json.loads(''.join(payload.parts))['props']['pageProps']['dataset']
    result=[]
    for report in reports:
        match=re.search(r'api_perf_data_(20\d{2})_([1-4])\.json$',report['filePath'])
        if not match: raise ValueError('Unrecognized quarterly report identifier')
        year,quarter=map(int,match.groups()); start=date(year,quarter*3-2,1)
        end=date(year+1,1,1) if quarter==4 else date(year,quarter*3+1,1)
        rows=report['content']['dataset']
        if [str(r['day']) for r in rows]!=[str(i) for i in range(1,(end-start).days+1)]:
            raise ValueError(f'Quarter calendar mismatch: {match[0]}')
        for row in rows:
            if set(row)-set(FIELDS)-{'day'}: raise ValueError('Unexpected report fields')
            for field,raw in row.items():
                if field=='day': continue
                service,metric,unit=FIELDS[field]; raw=str(raw)
                try:
                    parsed=raw+' ms' if unit=='milliseconds' and re.fullmatch(r'\d+(?:\.\d+)?',raw) else raw
                    value=number(parsed,unit); status='observed' if value is not None else 'missing'
                except ValueError: value=None; status='unsupported_value_or_unit'
                record=Observation('Starling','Starling API Performance',(start+timedelta(days=int(row['day'])-1)).isoformat(),service,metric,value,unit,'daily','published_real_bank',SOURCES['starling'],retrieved_at,status,raw,checksum).dict()
                record['source_report']=match[0]; record['source_field']=field
                result.append(record)
    if not result: raise ValueError('No quarterly observations')
    return result
