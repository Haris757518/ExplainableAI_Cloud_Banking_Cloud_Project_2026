"""Explicit operator CLI for the isolated normal workload or bounded delay."""
import argparse,time,json
import httpx
def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--normal',action='store_true');group.add_argument('--application-delay',action='store_true');parser.add_argument('--confirm-local-test',action='store_true');parser.add_argument('--per-operation',type=int,default=90);parser.add_argument('--duration',type=int,default=12);parser.add_argument('--delay-ms',type=int,default=150);args=parser.parse_args()
    if args.application_delay and not args.confirm_local_test:parser.error('Use --confirm-local-test to explicitly trigger a bounded local condition.')
    endpoint='/workload' if args.normal else '/experiments/application-delay'
    body={'confirm_local_test':True,'per_operation':args.per_operation} if args.normal else {'confirm_local_test':True,'duration_seconds':args.duration,'delay_ms':args.delay_ms}
    with httpx.Client(base_url='http://127.0.0.1:8000/api/banking',timeout=60,trust_env=False) as client:
        response=client.post(endpoint,json=body);response.raise_for_status();identifier=response.json()['job_id'];print('Local measured workload:',identifier,flush=True)
        deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            state=client.get('/state');state.raise_for_status();job=next(j for j in state.json()['jobs'] if j['id']==identifier)
            if job['status'] not in ('running','stopping'):
                print(json.dumps(job,indent=2));
                if job['status']!='completed':raise SystemExit(1)
                if args.application_delay:print(json.dumps(client.get('/verify/'+identifier).json(),indent=2))
                return
            time.sleep(1)
        raise SystemExit('Timed out awaiting local workload; inspect /api/banking/state or use Stop.')
if __name__=='__main__':main()
