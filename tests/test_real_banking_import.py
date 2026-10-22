from pathlib import Path
import hashlib
import pytest
from dataset.real_banking.parser import parse
from dataset.real_banking.starling_importer import extract
from dataset.real_banking.validate import validate

FIXTURES=Path(__file__).resolve().parents[1]/'dataset/real_banking'

def test_monzo_official_snapshot_and_known_measurement():
    data=(FIXTURES/'monzo.html').read_bytes()
    rows=parse(data.decode(),'monzo','2026-10-22',hashlib.sha256(data).hexdigest())
    validate(rows)
    actual=[r for r in rows if r['date']=='2026-04-01' and r['metric']=='latency' and r['service']=='Open Banking Payment Initiation']
    assert len(actual)==1 and actual[0]['value']==174
    assert any(r['record_status']=='unsupported_value_or_unit' and r['value'] is None for r in rows)
    assert any('CBPII' in r['service'] and r['value'] is None for r in rows)
    assert min(r['date'] for r in rows)=='2019-09-14'

def test_starling_quarter_payload_not_misleading_initial_heading():
    data=(FIXTURES/'starling.html').read_bytes()
    rows=extract(data.decode(),'2026-10-22',hashlib.sha256(data).hexdigest())
    validate(rows)
    assert min(r['date'] for r in rows)=='2019-07-01'
    assert max(r['date'] for r in rows)=='2026-06-30'
    assert len({r['source_report'] for r in rows})==28
    assert all(r['value'] is not None for r in rows)
    assert any(r['date']=='2019-07-01' and r['source_field']=='partnerAisp' and r['value']==97 for r in rows)

def test_bad_quarter_cannot_receive_invented_dates():
    html='<h3>Q2 2026</h3><table><tr><td>Day</td><td>Uptime mobile (%)</td></tr><tr><td>1</td><td>100</td></tr></table>'
    with pytest.raises(ValueError,match='calendar'): parse(html,'starling','2026-10-22','checksum')

def test_duplicate_rejected():
    row={'bank':'Monzo','service':'app','metric':'latency','date':'2026-01-01','value':1,'unit':'milliseconds'}
    with pytest.raises(ValueError,match='Duplicate'): validate([row,row])

def test_changed_table_schema_rejected():
    with pytest.raises(ValueError,match='No recognized'): parse('<html>Changed</html>','monzo','2026-10-22','x')
