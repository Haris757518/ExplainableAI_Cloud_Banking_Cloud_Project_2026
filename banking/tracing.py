"""Wall-clock trace coordinates plus monotonic durations; local child union subtraction."""
import contextvars,time,uuid,os
from banking import store
CURRENT=contextvars.ContextVar('banking_span',default=None)

def interval_union(intervals):
    total=0;end=None
    for a,b in sorted(intervals):
        if end is None or a>end:total+=b-a
        elif b>end:total+=b-end
        end=max(end or b,b)
    return total

class Span:
    def __init__(self,service,kind,operation,trace_id=None,parent_id=None,caller=None):
        self.parent=CURRENT.get();self.id=uuid.uuid4().hex;self.trace_id=trace_id or (self.parent.trace_id if self.parent else uuid.uuid4().hex)
        self.parent_id=parent_id or (self.parent.id if self.parent else None);self.service=service;self.kind=kind;self.operation=operation;self.caller=caller;self.children=[];self.records=[];self.status=200;self.metrics={}
    def __enter__(self):
        self.start=time.time();self.tick=time.perf_counter();self.cpu=time.process_time();self.token=CURRENT.set(self);return self
    def __exit__(self,typ,value,tb):
        finish=time.perf_counter();self.end=time.time();self.duration_ms=(finish-self.tick)*1000;self.exclusive_ms=max(0,self.duration_ms-interval_union(self.children)*1000)
        CURRENT.reset(self.token)
        if self.parent:self.parent.children.append((self.tick,finish))
        if typ:self.status=getattr(value,'status',500)
        self.payload={'id':self.id,'trace_id':self.trace_id,'parent_id':self.parent_id,'service':self.service,'caller':self.caller,'kind':self.kind,'operation':self.operation,'start':self.start,'end':self.end,'duration_ms':self.duration_ms,'exclusive_ms':self.exclusive_ms,'process_cpu_ms':(time.process_time()-self.cpu)*1000,'status':self.status,'pid':os.getpid(),'metrics':self.metrics}
        if self.parent:self.parent.records.extend(self.records+[self.payload])
        else:store.insert_spans(self.records+[self.payload])

def sql(db,statement,params=()):
    parent=CURRENT.get()
    with Span('banking-db','database',parent.operation,caller=parent.service):
        result=db.execute(statement,params)
        # Fetch queries inside the measured database span, not after stopping its timer.
        if result.description:
            values=result.fetchall()
            class Result:
                rowcount=len(values)
                def fetchone(self):return values[0] if values else None
                def fetchall(self):return values
            return Result()
        return result

def database_connection(operation,caller):
    with Span('banking-db','connection',operation,caller=caller):return store.connect('accounts.db')
