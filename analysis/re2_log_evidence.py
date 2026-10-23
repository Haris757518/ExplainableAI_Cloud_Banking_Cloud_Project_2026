"""Read-only, time-bounded RCAEval RE2 application-log evidence.

Log text is contextual evidence only. It cannot identify a Kubernetes audit actor,
prove causality, or replace the frozen metric/trace model ranking. Injection labels
are never read by this module. Files must match their local import checksum.
"""
from __future__ import annotations

import hashlib
import heapq
import re
from pathlib import Path

LOG_COLUMNS = ('timestamp', 'container_name', 'message')
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_SCAN_ROWS = 2_000_000


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _epoch_seconds(value):
    """Support seconds, milliseconds, microseconds and nanoseconds by magnitude."""
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (timestamp == timestamp and abs(timestamp) != float('inf')):
        return None
    magnitude = abs(timestamp)
    divisor = 1e9 if magnitude >= 1e17 else 1e6 if magnitude >= 1e14 else 1e3 if magnitude >= 1e11 else 1
    return timestamp / divisor


def _name(value):
    # Pod hashes and punctuation must not determine a false container identity.
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower()).replace('frontendservice', 'frontend')


def _unavailable(status, detail):
    return {'status': status, 'explanation': detail, 'messages': [],
            'causal_confirmation': False, 'identity_attribution': 'unavailable'}


def extract_log_evidence(log_path: Path, *, as_of: float, resource: str | None = None,
                         window_seconds: int = 180, max_results: int = 8):
    """Inspect ONLY logs at or before as_of; choose nearest messages in a bounded window.

    Does not use fault labels, injection timestamps, or benchmark directory names as
    candidate predictions. Checksums come from the explicit optional import step.
    """
    log_path = Path(log_path)
    if not log_path.is_file():
        return _unavailable('not_imported', 'Optional RCAEval application logs have not been imported for this recording.')
    seal = log_path.with_name(log_path.name + '.sha256')
    if not seal.is_file():
        return _unavailable('not_verified', 'Local log file has no import checksum; it will not be used.')
    if log_path.stat().st_size > MAX_FILE_BYTES:
        return _unavailable('too_large', 'The optional log file exceeds the bounded reader size limit.')
    expected = seal.read_text(encoding='ascii').strip()
    if not re.fullmatch(r'[a-fA-F0-9]{64}', expected) or file_sha256(log_path) != expected.lower():
        return _unavailable('integrity_failure', 'RCAEval log checksum mismatch; these logs were not used.')
    if log_path.stat().st_size > MAX_FILE_BYTES:
        return _unavailable('too_large', 'The optional log file exceeds the bounded reader size limit.')
    if not (0 < window_seconds <= 3600 and 1 <= max_results <= 25):
        raise ValueError('Unsupported log investigation limits')
    try:
        import pyarrow.parquet as pq
        with pq.ParquetFile(log_path) as parquet:
            if not set(LOG_COLUMNS).issubset(set(parquet.schema.names)):
                return _unavailable('unsupported_schema', 'The log file does not have the official RE2 log columns.')
            chosen = []
            scanned = 0
            in_window = 0
            desired = _name(resource)
            for batch in parquet.iter_batches(batch_size=4096, columns=list(LOG_COLUMNS)):
                rows = batch.to_pydict()
                for ts, container, msg in zip(*(rows[k] for k in LOG_COLUMNS)):
                    scanned += 1
                    observed = _epoch_seconds(ts)
                    if observed is not None and as_of - window_seconds <= observed <= as_of:
                        in_window += 1
                        service = str(container or '')[:100]
                        text = str(msg or '').replace('\x00', ' ')[:350]
                        if text:
                            # Keep latest evidence, slightly prioritize the suspected resource.
                            is_same = bool(desired and desired in _name(service))
                            priority = (int(is_same), observed, scanned)
                            item = (priority, {'timestamp': observed, 'container': service,
                                               'message': text, 'same_resource': is_same})
                            if len(chosen) < max_results:
                                heapq.heappush(chosen, item)
                            elif priority > chosen[0][0]:
                                heapq.heapreplace(chosen, item)
                    if scanned >= MAX_SCAN_ROWS:
                        break
                if scanned >= MAX_SCAN_ROWS:
                    break
    except (OSError, ValueError, TypeError, ImportError) as exc:
        return _unavailable('read_error', 'The stored log file could not be parsed safely: ' + type(exc).__name__)
    messages = [v for _, v in sorted(chosen, reverse=True)]
    return {'status': 'available', 'source': 'RCAEval RE2 application logs (recorded benchmark)',
            'sha256': expected.lower(), 'window_seconds': window_seconds, 'as_of': as_of,
            'messages_in_window': in_window, 'rows_scanned': scanned,
            'scan_complete': scanned < MAX_SCAN_ROWS,
            'messages': messages, 'causal_confirmation': False,
            'identity_attribution': 'unavailable',
            'explanation': ('Timestamp-nearby application messages are supporting context, not proof '
                            'of a root cause or evidence of who changed Kubernetes settings.')}


def get_re2_log_evidence(case_id: str, *, as_of: float, resource: str | None = None):
    """Resolve only an already imported opaque case ID to its optional log file."""
    from dataset.re2 import V4, entries
    from dataset.benchmarks import ROOT
    record = next((r for r in entries()['cases'] if r['id'] == case_id), None)
    if record is None:
        return _unavailable('unknown_recording', 'The selected RE2 recording is unavailable.')
    folder = ROOT.parent / record['storage_collection'] if record.get('storage_collection') else V4
    # This directory name is used only for file location, never as a diagnostic input.
    folder = folder / record['display_name']
    return extract_log_evidence(folder / 'logs.parquet', as_of=as_of, resource=resource)
