"""Dedicated test balances, measured spans, calibration and immutable snapshots."""
import os,json,sqlite3,time,uuid
from pathlib import Path

def root():
    path=Path(os.environ.get('BANKING_DATA_DIR',str(Path(__file__).resolve().parents[1]/'results/runtime/banking'))).resolve()
    path.mkdir(parents=True,exist_ok=True);return path

def connect(name='telemetry.db'):
    connection=sqlite3.connect(root()/name,timeout=15,isolation_level=None)
    connection.row_factory=sqlite3.Row
    connection.execute('PRAGMA busy_timeout=15000');connection.execute('PRAGMA foreign_keys=ON')
    return connection

def initialize():
    with connect('accounts.db') as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY,name TEXT NOT NULL,balance_cents INTEGER NOT NULL CHECK(balance_cents>=0));
        CREATE TABLE IF NOT EXISTS transfers(id TEXT PRIMARY KEY,sender TEXT NOT NULL REFERENCES accounts(id),recipient TEXT NOT NULL REFERENCES accounts(id),amount_cents INTEGER NOT NULL CHECK(amount_cents>0),created_at REAL NOT NULL);''')
        db.executemany('INSERT OR IGNORE INTO accounts VALUES(?,?,?)',[('test-a','Test Account A',10000000),('test-b','Test Account B',10000000)])
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''CREATE TABLE IF NOT EXISTS spans(id TEXT PRIMARY KEY,trace_id TEXT NOT NULL,operation TEXT NOT NULL,service TEXT NOT NULL,kind TEXT NOT NULL,start REAL NOT NULL,end REAL NOT NULL,payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS spans_trace ON spans(trace_id);
        CREATE TABLE IF NOT EXISTS requests(seq INTEGER PRIMARY KEY AUTOINCREMENT,trace_id TEXT UNIQUE NOT NULL,operation TEXT NOT NULL,ts REAL NOT NULL,duration_ms REAL NOT NULL,success INTEGER NOT NULL,status INTEGER NOT NULL,client_latency_ms REAL);
        CREATE TABLE IF NOT EXISTS calibration(id TEXT PRIMARY KEY,payload TEXT NOT NULL,created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,operation TEXT NOT NULL,ts REAL NOT NULL,payload TEXT NOT NULL);''')
    with connect('controls.db') as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,kind TEXT NOT NULL,target TEXT NOT NULL,started REAL NOT NULL,expires REAL NOT NULL,ended REAL,delay_ms INTEGER NOT NULL,status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL);''')

class BankingError(Exception):
    def __init__(self,status,message):self.status=status;self.message=message;super().__init__(message)

def transfer(sender,recipient,amount,transfer_id,execute,connection_factory=None):
    """BEGIN IMMEDIATE serializes writers; debit, credit and idempotency are atomic."""
    if sender==recipient or type(amount) is not int or not 0<amount<=1000000:raise BankingError(422,'Use distinct test accounts and 1–1,000,000 test cents.')
    db=connection_factory() if connection_factory else connect('accounts.db')
    try:
        execute(db,'BEGIN IMMEDIATE')
        previous=execute(db,'SELECT * FROM transfers WHERE id=?',(transfer_id,)).fetchone()
        if previous:
            if (previous['sender'],previous['recipient'],previous['amount_cents'])!=(sender,recipient,amount):raise BankingError(409,'Transfer identifier already used with different input.')
            execute(db,'COMMIT');return dict(previous)|{'duplicate':True}
        accounts=execute(db,'SELECT id,balance_cents FROM accounts WHERE id IN (?,?)',(sender,recipient)).fetchall()
        if len(accounts)!=2:raise BankingError(404,'Unknown fictitious test account.')
        if next(a['balance_cents'] for a in accounts if a['id']==sender)<amount:raise BankingError(409,'Insufficient test balance.')
        debit=execute(db,'UPDATE accounts SET balance_cents=balance_cents-? WHERE id=? AND balance_cents>=?',(amount,sender,amount))
        if debit.rowcount!=1:raise BankingError(409,'Insufficient test balance.')
        execute(db,'UPDATE accounts SET balance_cents=balance_cents+? WHERE id=?',(amount,recipient))
        created=time.time();execute(db,'INSERT INTO transfers VALUES(?,?,?,?,?)',(transfer_id,sender,recipient,amount,created));execute(db,'COMMIT')
        return {'id':transfer_id,'sender':sender,'recipient':recipient,'amount_cents':amount,'created_at':created,'duplicate':False}
    except Exception:
        if db.in_transaction:db.rollback()
        raise
    finally:db.close()

def rows(sql,params=(),name='telemetry.db'):
    with connect(name) as db:return [dict(row) for row in db.execute(sql,params)]

def insert_span(payload):
    insert_spans([payload])

def insert_spans(payloads):
    with connect() as db:
        db.execute('BEGIN')
        db.executemany('INSERT INTO spans VALUES(?,?,?,?,?,?,?,?)',[(p['id'],p['trace_id'],p['operation'],p['service'],p['kind'],p['start'],p['end'],json.dumps(p,allow_nan=False)) for p in payloads])
        db.commit()

def request_rows(operation=None,as_of=None):
    conditions=['1=1'];params=[]
    if operation:conditions.append('operation=?');params.append(operation)
    if as_of is not None:conditions.append('ts<=?');params.append(as_of)
    return rows('SELECT * FROM requests WHERE '+' AND '.join(conditions)+' ORDER BY seq',params)

def calibration():
    value=rows('SELECT payload FROM calibration ORDER BY created_at DESC LIMIT 1')
    return json.loads(value[0]['payload']) if value else None

def save_snapshot(incident,operation):
    with connect() as db:db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)',(incident['id'],operation,incident['observation_time'] or time.time(),json.dumps(incident,allow_nan=False)))

def experiment_start(duration=12,delay_ms=150):
    if not 3<=duration<=30 or not 50<=delay_ms<=250:raise BankingError(422,'Duration must be 3–30 seconds and delay 50–250 milliseconds.')
    with connect('controls.db') as db:
        db.execute('BEGIN IMMEDIATE');now=time.time()
        db.execute("UPDATE experiments SET ended=expires,status='expired' WHERE ended IS NULL AND expires<=?",(now,))
        if db.execute('SELECT 1 FROM experiments WHERE ended IS NULL').fetchone():db.rollback();raise BankingError(409,'A controlled local experiment is already active.')
        identifier=uuid.uuid4().hex
        db.execute('INSERT INTO experiments VALUES(?,?,?,?,?,?,?,?)',(identifier,'application_processing_delay','ledger-service',now,now+duration,None,delay_ms,'active'));db.commit()
    return identifier

def active_delay():
    """Only the isolated ledger execution reads control state; inference never does."""
    with connect('controls.db') as db:
        now=time.time();db.execute("UPDATE experiments SET ended=expires,status='expired' WHERE ended IS NULL AND expires<=?",(now,))
        row=db.execute('SELECT delay_ms,expires FROM experiments WHERE ended IS NULL AND expires>?',(now,)).fetchone()
    return min(row['delay_ms']/1000,max(0,row['expires']-now)) if row else 0

def stop_experiments():
    with connect('controls.db') as db:db.execute("UPDATE experiments SET ended=?,status='stopped' WHERE ended IS NULL",(time.time(),))

def experiment_labels():
    # Control plane and evaluator only; never called by the incident adapter/model.
    active_delay()
    return rows('SELECT * FROM experiments ORDER BY started DESC',name='controls.db')
