"""Restore exactly the public inputs used by the retained 15-case RE2 study.

No selection, training, AWS access, or local evidence upload is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(1024*1024):h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    config=ROOT/'configs/re2-reproduction'
    index=json.loads((config/'index.json').read_text())
    revision=index['revision']
    base=f'https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{revision}/'
    total=0

    def fetch(relative,destination,expected):
        nonlocal total
        if destination.exists():
            if sha(destination)!=expected:raise ValueError('Existing input checksum mismatch: '+str(destination))
        else:
            if args.verify_only:raise FileNotFoundError(destination)
            destination.parent.mkdir(parents=True,exist_ok=True)
            partial=destination.with_name(destination.name+'.partial')
            try:
                with urlopen(base+relative,timeout=60) as response, partial.open('wb') as stream:
                    while block:=response.read(1024*1024):stream.write(block)
                if sha(partial)!=expected:raise ValueError('Downloaded input checksum mismatch: '+relative)
                partial.replace(destination)
            finally:
                if partial.exists():partial.unlink()
        total+=1

    fetch('cases.parquet',ROOT/'dataset/raw/research/rcaeval/cases.parquet',index['cases_parquet_sha256'])
    for collection in ['research_v4','research_probe']:
        manifest_bytes=(config/(collection+'-manifest.json')).read_bytes()
        manifest=json.loads(manifest_bytes)
        assert manifest['revision']==revision
        target=ROOT/'dataset/raw'/collection
        for entry in manifest['cases']:
            name=entry['display_name']
            assert '/' not in name and '\\' not in name and '..' not in name
            for filename,digest in entry['checksums'].items():
                assert filename in ('metrics.parquet','traces.parquet','inject_time.txt')
                fetch(name+'/'+filename,target/name/filename,digest)
        existing=target/'manifest.json'
        if existing.exists() and existing.read_bytes()!=manifest_bytes:
            raise ValueError('Do not overwrite a different case selection')
        if not args.verify_only:
            target.mkdir(parents=True,exist_ok=True)
            existing.write_bytes(manifest_bytes)
    print(f'Verified {total} pinned public files for exactly 15 RE2 recordings.')


if __name__=='__main__':main()
