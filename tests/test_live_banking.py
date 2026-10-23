from analysis.live_banking import assess

def row(t,latency=10):return {'timestamp':t-1,'completed_at':t,'latency_ms':latency,'outcome':'acknowledged_success'}

def test_live_normal_fault_recovery_and_staleness():
    baseline=[row(i) for i in range(1,31)]
    normal=[row(i) for i in range(80,101)]
    assert assess(normal,baseline,now=100)['status']=='normal'
    fault=[row(i,1000) for i in range(80,101)]
    assert assess(fault,baseline,now=100)['status']=='anomaly'
    assert assess(normal,baseline,now=100)['status']=='normal'
    assert assess(normal,baseline,now=130)['status']=='stale'

def test_future_data_and_unfrozen_reference_do_not_establish_health():
    assert assess([row(101)],[],now=100)['status']=='stale'
    assert assess([row(99)],[],now=100)['status']=='warming_up'
