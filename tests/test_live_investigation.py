from analysis import live_investigation as module

def test_live_lock_mechanism_requires_current_direct_evidence(monkeypatch):
    monkeypatch.setattr(module,'rank',lambda value,now:{'status':'evaluated','ranking':[{'service':'frontend','score':3}]})
    value={'database':{'timestamp':99,'blocked_sessions':2,'locks':[{'granted':True,'mode':'AccessExclusiveLock','relation':'transactions'}]}}
    result=module.investigate_live(value,now=100)
    cause=result['probe_xai']['causes'][0]
    assert cause['service']=='ledger-db'
    assert 'exclusive lock' in cause['deeper_cause']
    assert result['gnn']['ranking'][0]['service']=='frontend'
    assert result['probe_xai']['driver_attribution'].startswith('Not established')
    assert len(result['probe_xai']['queries'])<=8

def test_missing_and_stale_measurements_do_not_invent_causes(monkeypatch):
    monkeypatch.setattr(module,'rank',lambda value,now:{'status':'unavailable'})
    for value in ({},{'database':{'timestamp':1,'blocked_sessions':2}}):
        assert module.investigate_live(value,now=100)['probe_xai']['causes']==[]
