"""Opt-in import of pinned RCAEval RE2 logs for the retained benchmark cases.

No AWS access, model training, dataset labels, or telemetry upload. Existing
metrics and traces are unchanged. Default: fetch at most one case for a quick demo.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.re2_log_evidence import MAX_FILE_BYTES, file_sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case-id', help='Optional opaque recording ID as shown by the API')
    parser.add_argument('--limit', type=int, default=1, help='Number of selected cases (default 1)')
    parser.add_argument('--all', action='store_true', help='Process all 15 pinned RE2 cases')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.limit <= 15:
        parser.error('--limit must be between 1 and 15')
    config = ROOT / 'configs/re2-reproduction'
    index = json.loads((config / 'index.json').read_text())
    revision = index['revision']
    if not re.fullmatch(r'[a-fA-F0-9]{40}', revision):
        raise ValueError('Dataset revision must be a pinned 40-hex-character commit')
    cases = []
    for collection in ('research_v4', 'research_probe'):
        manifest_bytes = (config / (collection + '-manifest.json')).read_bytes()
        manifest = json.loads(manifest_bytes)
        if manifest['revision'] != revision:
            raise ValueError('Mismatch in dataset revision')
        installed_manifest = ROOT / 'dataset/raw' / collection / 'manifest.json'
        if not installed_manifest.is_file() or installed_manifest.read_bytes() != manifest_bytes:
            raise ValueError('Restore the original pinned RE2 inputs before optional logs')
        for entry in manifest['cases']:
            name = entry['display_name']
            if not re.fullmatch(r'[a-zA-Z0-9_.-]+', name):
                raise ValueError('Unsafe recording directory')
            cases.append((entry['id'], name, ROOT / 'dataset/raw' / collection / name))
    if args.case_id:
        cases = [entry for entry in cases if entry[0] == args.case_id]
        if not cases:
            parser.error('No imported RE2 recording has that opaque ID')
    elif not args.all:
        cases = cases[:args.limit]

    for opaque_id, name, folder in cases:
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / 'logs.parquet'
        seal = folder / 'logs.parquet.sha256'
        if output.exists():
            if not seal.exists() or file_sha256(output) != seal.read_text().strip():
                raise ValueError('Existing RE2 logs lack a matching import checksum: ' + name)
            print('Verified', opaque_id, 'SHA256', seal.read_text().strip())
            continue
        if args.verify_only:
            print('Not imported:', opaque_id)
            continue
        source = ('https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/'
                  + revision + '/' + quote(name) + '/logs.parquet')
        partial = folder / 'logs.parquet.partial'
        try:
            with urlopen(source, timeout=60) as response, partial.open('wb') as stream:
                amount = 0
                while block := response.read(1024 * 1024):
                    amount += len(block)
                    if amount > MAX_FILE_BYTES:
                        raise ValueError('RE2 log download exceeds configured size cap')
                    stream.write(block)
            import pyarrow.parquet as pq
            with pq.ParquetFile(partial) as parquet:
                if not {'timestamp', 'container_name', 'message'}.issubset(set(parquet.schema.names)):
                    raise ValueError('Unexpected RE2 log schema')
            checksum = file_sha256(partial)
            partial.replace(output)
            seal.write_text(checksum + '\n', encoding='ascii')
            print('Imported', opaque_id, 'SHA256', checksum)
        except HTTPError as error:
            if error.code == 404:
                print('Official RE2 logs unavailable for', opaque_id)
            else:
                raise
        finally:
            if partial.exists():
                partial.unlink()


if __name__ == '__main__':
    main()
