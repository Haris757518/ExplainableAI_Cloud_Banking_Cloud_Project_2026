"""Start/reuse the three loopback processes. No workloads or faults start here."""
from pathlib import Path
import sys,os,time,subprocess,signal
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from banking import store

def main():
    store.initialize();children=[];logs=[]
    services=[('account',8101,'banking.service:app','/health'),('ledger',8102,'banking.service:app','/health'),('gateway',8000,'backend.main:app','/api/health')]
    try:
        for role,port,module,endpoint in services:
            url=f'http://127.0.0.1:{port}{endpoint}'
            try:
                r=httpx.get(url,timeout=1);r.raise_for_status();value=r.json()
                if role!='gateway' and value.get('role')!=role:raise RuntimeError(f'Port {port} is occupied by a different service.')
                print(f'Reusing existing {role} at 127.0.0.1:{port}',flush=True);continue
            except httpx.TransportError:pass
            env=os.environ.copy();env['BANKING_SERVICE_ROLE']=role
            log=(store.root()/(role+'-server.log')).open('a',encoding='utf-8');logs.append(log)
            child=subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0);children.append(child)
            for attempt in range(100):
                if child.poll() is not None:raise RuntimeError(f'{role} failed to start. See {log.name}.')
                try:httpx.get(url,timeout=.5).raise_for_status();break
                except httpx.HTTPError:time.sleep(.2)
            else:raise RuntimeError(f'{role} startup timed out.')
            print(f'Started {role} at 127.0.0.1:{port}',flush=True)
        httpx.get('http://127.0.0.1:8000/api/banking/state',timeout=30).raise_for_status()
        print('Ready: http://127.0.0.1:8000/ — Digital Banking. No workload or fault was started.',flush=True)
        print('Keep this window open. Ctrl+C stops only processes started by this launcher.',flush=True)
        while True:
            for child in children:
                if child.poll() is not None:raise RuntimeError('A banking process stopped unexpectedly. Inspect its server log.')
            time.sleep(1)
    except KeyboardInterrupt:print('\nStopping owned local services; bounded conditions expire independently.',flush=True)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        for log in logs:log.close()
if __name__=='__main__':main()
