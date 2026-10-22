"""Prepare an isolated manifest bundle only. Never invokes Kubernetes or AWS."""
from pathlib import Path
import subprocess,json,argparse,shutil
import yaml

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,default=ROOT/'vendor/bank-of-anthos')
args=parser.parse_args()
source=args.source.resolve()
target=ROOT/'deploy/anthos-prepared';target.mkdir(parents=True,exist_ok=True)
revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
documents=[]
for path in sorted((source/'kubernetes-manifests').glob('*.yaml')):
    for doc in yaml.safe_load_all(path.read_text(encoding='utf-8')):
        if not doc:continue
        kind=doc.get('kind')
        if kind=='ServiceAccount':doc['metadata'].pop('annotations',None)
        if kind=='Service':doc.get('spec',{})['type']='ClusterIP'
        if kind in ('Deployment','StatefulSet'):
            if doc['metadata']['name']=='loadgenerator':doc['spec']['replicas']=0
            template=doc['spec']['template']
            template['metadata'].pop('annotations',None)
            for container in template['spec'].get('containers',[]):
                for env in container.get('env',[]):
                    if env['name'] in ('ENABLE_TRACING','ENABLE_METRICS'):env['value']='false'
                if doc['metadata']['name']=='frontend':
                    container['command']=['gunicorn']
                    container['args']=['-b',':8080','--threads','4','--log-config','logging.conf','--log-level','info','research_frontend:create_app()']
                    container.setdefault('volumeMounts',[]).append({'name':'research-frontend','mountPath':'/app/research_frontend.py','subPath':'research_frontend.py','readOnly':True})
            if doc['metadata']['name']=='frontend':
                template['spec'].setdefault('volumes',[]).append({'name':'research-frontend','configMap':{'name':'research-frontend'}})
            # Existing GCP exporters are disabled until explicit provider-neutral
            # instrumentation is configured and its output is verified.
        documents.append(doc)
documents.append({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'research-frontend'},
                  'data':{'research_frontend.py':(ROOT/'deploy/anthos_frontend_telemetry.py').read_text(encoding='utf-8')}})
(target/'resources.yaml').write_text(yaml.safe_dump_all(documents,sort_keys=False),encoding='utf-8')
(target/'namespace.yaml').write_text('apiVersion: v1\nkind: Namespace\nmetadata:\n  name: banking-probe-research\n',encoding='utf-8')
shutil.copyfile(source/'extras/jwt/jwt-secret.yaml',target/'demo-jwt-secret.yaml')
(target/'kustomization.yaml').write_text('apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nnamespace: banking-probe-research\nresources:\n  - namespace.yaml\n  - resources.yaml\n  - demo-jwt-secret.yaml\n',encoding='utf-8')
(target/'preparation.json').write_text(json.dumps({'source_revision':revision,'deployed':False,'runtime_verified':False,
    'public_load_balancers':False,'loadgenerator_replicas':0,'demo_secret':'Upstream public demo key; isolated local namespace only.',
    'source_directory':str(source),'instrumentation_status':'Prepared local stdout frontend server/client spans; runtime not verified. Backend server, database, queue and capacity instrumentation still required before measured experiments.',
    'source_url':'https://github.com/GoogleCloudPlatform/bank-of-anthos','source_license':'Apache-2.0; upstream copyright retained in vendor source',
    'budget_inr':0,'cloud_resources_created':0},indent=2))
print('Prepared manifest bundle; no deployment or cloud API call performed.')
