"""Fetch portable, checksum-verified Java build tools into the approved D: workspace."""
import hashlib,json,urllib.request,zipfile
from pathlib import Path
ROOT=Path(r'D:\BankingResearch\Tools\JavaValidation')
ROOT.mkdir(parents=True,exist_ok=True)
SOURCES={
 'jdk':('https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip','https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip.sha256sum.txt','sha256'),
 'maven':('https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip','https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.9/apache-maven-3.9.9-bin.zip.sha512','sha512'),
}
receipt={}
for name,(url,checksum_url,algorithm) in SOURCES.items():
    path=ROOT/(name+'.zip')
    expected=urllib.request.urlopen(checksum_url,timeout=60).read().decode().split()[0].lower()
    if not path.exists():
        with urllib.request.urlopen(url,timeout=120) as response,path.open('wb') as output:
            while chunk:=response.read(1024*1024):output.write(chunk)
    actual=hashlib.new(algorithm,path.read_bytes()).hexdigest()
    if actual!=expected:raise ValueError(f'{name} download checksum mismatch')
    target=ROOT/name
    if not target.exists():
        target.mkdir()
        with zipfile.ZipFile(path) as archive:archive.extractall(target)
    receipt[name]={'url':url,'checksum_url':checksum_url,'algorithm':algorithm,'checksum':actual,'directory':str(target),'verified':True}
    print(name,'verified and extracted',flush=True)
(ROOT/'tools.json').write_text(json.dumps(receipt,indent=2))
