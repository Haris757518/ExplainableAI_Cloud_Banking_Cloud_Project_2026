"""Strict table extraction with heading context; fail on changed schemas."""
from html.parser import HTMLParser
import re
from datetime import date, timedelta
from .schema import Observation, SOURCES

class Tables(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.tables=[]; self.headings=[]; self.heading=None; self.cell=None; self.table=None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag in ('h1','h2','h3','h4'): self.heading=[]
        if tag == 'table': self.table={'headings':list(self.headings),'rows':[]}
        if tag == 'tr' and self.table is not None: self.row=[]
        if tag in ('td','th') and self.table is not None:
            self.cell=[]; self.span=int(dict(attrs).get('colspan',1))
        if tag == 'br' and self.cell is not None: self.cell.append(' ')
    def handle_data(self, data):
        if self.heading is not None: self.heading.append(data)
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ('h1','h2','h3','h4') and self.heading is not None:
            self.headings.append(' '.join(''.join(self.heading).split())); self.heading=None
        if tag in ('td','th') and self.cell is not None:
            self.row.extend([' '.join(''.join(self.cell).split())]*self.span); self.cell=None
        if tag == 'tr' and self.table is not None: self.table['rows'].append(self.row)
        if tag == 'table' and self.table is not None:
            self.tables.append(self.table); self.table=None

def number(raw, unit):
    if raw.strip().lower() in {'n/a','na','-','—',''}: return None
    pattern = r'\d+(?:\.\d+)?' + (r'\s*ms' if unit=='milliseconds' else r'\s*%?')
    if not re.fullmatch(pattern, raw.strip(), re.I):
        raise ValueError(f'Unsupported value/unit: {raw!r} ({unit})')
    return float(re.match(r'\d+(?:\.\d+)?',raw.strip())[0])

def parse(html, bank, retrieved_at, checksum):
    observations=[]
    for table in Tables(html).tables:
        rows=table['rows']
        if not rows or not rows[0] or rows[0][0] not in ('Date','Day'): continue
        headers=rows[0]; data=rows[1:]
        # Official Monzo tables advertise CBPII but omit the trailing cells.
        # Preserve these explicitly as null, never shift or impute measurements.
        if bank=='monzo' and 'CBPII' in headers[-1]:
            data=[r+[''] if len(r)==len(headers)-1 else r for r in data]
        if any(len(row)!=len(headers) for row in data): raise ValueError('Table column count changed')
        if bank=='starling':
            periods=[re.search(r'Q([1-4])\s+(20\d{2})',h) for h in table['headings']]
            periods=[p for p in periods if p]
            if not periods: raise ValueError('Missing Starling reporting quarter')
            q,y=map(int,periods[-1].groups()); start=date(y,3*q-2,1)
            end=date(y+1,1,1) if q==4 else date(y,3*q+1,1)
            if [r[0] for r in data]!=[str(i) for i in range(1,(end-start).days+1)]:
                raise ValueError('Starling day indices do not match quarter calendar length')
        for row in data:
            day=date.fromisoformat(row[0]) if bank=='monzo' else start+timedelta(days=int(row[0])-1)
            for header,raw in zip(headers[1:],row[1:]):
                h=header.lower(); heading=table['headings'][-1].lower()
                if bank=='monzo':
                    service=header
                    if 'uptime' in heading: metric,unit='availability','percent'
                    elif 'response' in heading or 'request' in heading: metric,unit='latency','milliseconds'
                    elif 'error' in heading: metric,unit='errors','percent'
                    else: raise ValueError(f'Unknown Monzo metric heading: {heading}')
                else:
                    if 'uptime' in h: metric,unit='availability','percent'
                    elif 'downtime' in h: metric,unit='downtime','percent'
                    elif 'error' in h: metric,unit='errors','percent'
                    elif 'response' in h or '(ms)' in h: metric,unit='latency','milliseconds'
                    else: raise ValueError(f'Unknown Starling header: {header}')
                    service=re.sub(r'\s*\([^)]*\)','',header)
                    service=re.sub(r'(?i)uptime|downtime|error rate|average response time|average response|response time','',service).strip()
                try:
                    value=number(raw,unit)
                    status='missing' if value is None else 'observed'
                except ValueError:
                    value=None; status='unsupported_value_or_unit'
                observations.append(Observation(bank.title(),bank.title()+' Service Information',day.isoformat(),service,metric,value,unit,'daily','published_real_bank',SOURCES[bank],retrieved_at,status,raw,checksum).dict())
    if not observations: raise ValueError('No recognized daily performance tables; source structure may have changed')
    return observations
