#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import subprocess,json,time,uuid
from pathlib import Path
prefix=['/usr/local/bin/kubectl','-n','banking-probe-research']
pod=json.loads(subprocess.check_output(prefix+['get','pods','-l','app=ledgerwriter','-o','json'],text=True))['items'][0]
container=pod['spec']['containers'][0]
original=container['resources']
reduced=json.loads(json.dumps(original))
reduced.setdefault('limits',{})['cpu']='20m'
reduced.setdefault('requests',{})['cpu']='20m'
def command(resources):
    return prefix+['patch','pod',pod['metadata']['name'],'--subresource=resize','--type=strategic','-p',json.dumps({'spec':{'containers':[{'name':container['name'],'resources':resources}]}})]
restore=command(original)
# Independent restoration remains scheduled even if this SSM command is interrupted.
subprocess.run(['systemd-run','--unit=faculty-cpu-restore-'+uuid.uuid4().hex[:8],'--on-active=35s','--collect',*restore],check=True,timeout=10)
busy=None
try:
    subprocess.run(command(reduced),check=True,timeout=12)
    # Bounded contention in this exact container cgroup, never the existing host.
    cid=pod['status']['containerStatuses'][0]['containerID'].split('://')[1]
    info=json.loads(subprocess.check_output(['k3s','crictl','inspect',cid],text=True,timeout=5))
    relative=Path('/proc/'+str(info['info']['pid'])+'/cgroup').read_text().split('0::',1)[1].strip()
    group=Path('/sys/fs/cgroup'+relative)
    busy=subprocess.Popen(['/usr/bin/python3','-c','import time; end=time.monotonic()+25; exec("while time.monotonic()<end: pass")'])
    (group/'cgroup.procs').write_text(str(busy.pid))
    time.sleep(30)
finally:
    if busy and busy.poll() is None:busy.terminate();busy.wait(timeout=3)
    subprocess.run(restore,check=True,timeout=12)
print('CPU allowance restored')
PY
