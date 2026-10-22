"""Recovery requires later measured performance and transaction correctness."""
def verify_recovery(incident_time,reference,measurements,intervention=None,integrity=None):
    if not intervention or not intervention.get('approved') or not intervention.get('executed_at'):
        return {'status':'not_verified','reason':'No approved, executed intervention is recorded.'}
    if intervention['executed_at']<=incident_time:
        return {'status':'not_verified','reason':'Intervention must occur after the incident observation.'}
    later=[p for p in measurements if p['timestamp']>intervention['executed_at'] and p.get('value') is not None]
    if len(later)<3:return {'status':'not_verified','reason':'At least three later performance observations are required.'}
    tolerance=max(abs(reference)*.2,1.)
    if any(p['value']>reference+tolerance for p in later[-3:]):
        return {'status':'still_abnormal','reason':'Later measured performance remains above the frozen reference tolerance.'}
    required={'pending_payments_consistent','no_duplicate_processing','ledger_reconciled'}
    if not integrity or integrity.get('measured_at',0)<=intervention['executed_at'] or any(integrity.get(k) is not True for k in required):
        return {'status':'not_verified','reason':'Performance improved, but later banking correctness checks are incomplete or failed.'}
    return {'status':'recovered','reason':'Three later measurements returned toward baseline and measured transaction-integrity checks passed.'}
