"""Attach later corrective evidence without rewriting the original recording."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROOF=ROOT/'results/correctness_fix/aws-proof'

def verified_final_study():
    folder=ROOT/'results/final_validation'
    try:
        manifest=json.loads((folder/'verified-results.json').read_text())
        if set(manifest['files'])!={'report.json','predictions-before-label-scoring.json','aws-cleanup.json'}:return None
        for name,sha in manifest['files'].items():
            path=folder/name
            if path.resolve().parent!=folder.resolve():return None
            if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:return None
        report=json.loads((folder/'report.json').read_text())
        cleanup=json.loads((folder/'aws-cleanup.json').read_text())
        if report['status']!='evaluated' or cleanup['status']!='terminated' or not cleanup['root_volume_deleted']:return None
        if report['export_sha256']!=cleanup['final_export_sha256'] or report['export_sha256']!=manifest['source_archive_sha256']:return None
        return report
    except (OSError,ValueError,KeyError,TypeError):return None

def verified_corrective_code(folder=None):
    folder=folder or PROOF
    try:
        manifest=json.loads((folder/'manifest.json').read_text())
        data={}
        for name,sha in manifest['files'].items():
            payload=(folder/name).read_bytes()
            if hashlib.sha256(payload).hexdigest()!=sha:return None
            data[name]=json.loads(payload)
        baseline=data['baseline-trials.json'];patched=data['patched-trials.json'];restart=data['after-restart.json'];classes=data['deployed-class-checksums.json']
        def correct(trial):
            if trial['held_process_exit']!=0 or trial['earlier_id']>=trial['later_id']:return False
            accounts=trial['after']['accounts']
            return len(accounts)==2 and all(a['api_cents']==a['ledger_cents'] and a['gap_cents']==0 and a['history_ids'].count(trial['earlier_id'])==1 and a['history_ids'].count(trial['later_id'])==1 and len(a['history_ids'])==len(set(a['history_ids'])) for a in accounts)
        all_ids={t[k] for t in patched for k in ('earlier_id','later_id')}
        restarted=len(restart['accounts'])==2 and all(a['api_cents']==a['ledger_cents'] and a['gap_cents']==0 and all_ids<=set(a['history_ids']) and len(a['history_ids'])==len(set(a['history_ids'])) for a in restart['accounts'])
        expected=json.loads((ROOT/'deploy/correctness-fix/class-checksums.json').read_text())
        hashes=classes['expected']==classes['observed']==expected
        passed=len(patched)==3 and len(all_ids)==6 and all(correct(t) for t in patched) and restarted and hashes
        return {'verified':passed,'source':manifest['source'],'source_instance':manifest['source_instance'],
                'baseline_trials':len(baseline),'baseline_incorrect_trials':sum(not correct(t) for t in baseline),
                'patched_trials':len(patched),'patched_correct_trials':sum(correct(t) for t in patched),'restart_verified':restarted,
                'deployed_hashes_verified':hashes,'export_sha256':manifest['export_sha256'],
                'scope':'Implemented code verified in these repeated AWS tests; production capacity and universal correctness are not certified.'}
    except (OSError,ValueError,KeyError,TypeError):return None

def attach_followups(result):
    proof=verified_corrective_code()
    result['corrective_code']=proof or {'verified':False,'reason':'Later corrective-code proof is absent or failed verification.'}
    result['model_status']='Banking GNNs have been trained and evaluated. Their symptom rankings are retained separately from evidence-guided localization. See Research and Validation for results and limits.'
    if proof and proof['verified']:
        for incident in result['incidents']:
            if incident['id']!='balance':continue
            incident.update(status='Corrective code verified in AWS tests',permanent_fix_verified=True,
                recommendation='The corrected balance and history readers now read committed ledger records directly, so they do not depend on the order in which transaction numbers finish. The code was deployed and tested in the isolated AWS application.',
                prevention='Keep the commit-order and restart regression tests. Monitor database load because authoritative reads perform more database work than cached reads.',
                recovery='The original readers failed all three new commit-order trials. The corrected readers passed all three: both balances matched the ledger, and each tested transfer appeared once in both histories. The same checks passed after restarting the readers. This verifies the implemented correction within these tests.',
                origin='Original investigator-assisted discovery, followed by repeated before-and-after AWS/PostgreSQL verification of the corrective code')
    final=verified_final_study()
    if final:
        result['latest_validation']={k:final[k] for k in ('status','source','execution_id','submitted_requests','ledger_matches','acknowledged_success','uncertain_requests','method_summary','corrective_code','limitations')}
    return result


def readable_followup_report(result):
    from analysis.banking_replay import readable_report
    text=readable_report(result)
    proof=result.get('corrective_code',{})
    if proof.get('verified'):
        text+='\n\n## Implemented correction verification\n\n'
        text+=f"The original readers were incorrect in {proof['baseline_incorrect_trials']} of {proof['baseline_trials']} controlled commit-order trials. The corrected readers passed {proof['patched_correct_trials']} of {proof['patched_trials']}. Both account balances matched the ledger after restart, and the tested transfers remained present once in both histories. Deployed build hashes matched the validated code.\n\n"
        text+=proof['scope']
    final=result.get('latest_validation')
    if final:
        text+='\n\n## Separate later AWS validation\n\n'
        text+=f"The later run submitted {final['submitted_requests']:,} requests, with {final['ledger_matches']:,} matching ledger records. Callers received {final['acknowledged_success']:,} recorded success acknowledgements; {final['uncertain_requests']:,} outcomes were uncertain. Ledger presence and caller acknowledgement are separate checks.\n\n"
        other=final['submitted_requests']-final['acknowledged_success']-final['uncertain_requests']
        if other:text+=f"Another {other:,} responses were not classified as successful acknowledgements.\n\n"
        text+='The table counts fixed CPU and database fault checkpoints in this later workload. It does not change the source of the incident explanations above.\n\n'
        text+='| Model variant | Seed | GNN service ranking correct | Evidence-guided service localization correct | Fault checkpoints detected |\n| --- | --- | --- | --- | --- |\n'
        for method in ('graph','identity'):
            results=final['method_summary'][method];n=results['independent_executed_fault_repetitions']
            for row in results['seed_results']:
                text+=f"| {method} | {row['seed']} | {row['gnn_top1_count']} of {n} | {row['refined_top1_count']} of {n} | {row['detected_count']} of {n} |\n"
        text+='\n'+'\n'.join('- '+limit for limit in final['limitations'])
    return text+'\n'
