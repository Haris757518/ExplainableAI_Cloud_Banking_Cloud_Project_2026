"""Analytical log fixtures only; never presented as actual RCAEval results."""
import hashlib

import pyarrow as pa
import pyarrow.parquet as pq

from analysis.re2_log_evidence import extract_log_evidence


def write_logs(tmp_path, timestamps, messages, containers=None):
    path = tmp_path / 'logs.parquet'
    pq.write_table(pa.table({'timestamp': timestamps,
                             'container_name': containers or ['frontend'] * len(timestamps),
                             'message': messages}), path)
    (tmp_path / 'logs.parquet.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest())
    return path


def test_only_past_messages_appear_and_future_labels_are_not_inputs(tmp_path):
    path = write_logs(tmp_path, [1700000000, 1700000040, 1700000100],
                      ['old normal message', 'observed warning', 'future revelation'])
    result = extract_log_evidence(path, as_of=1700000050, resource='frontend', window_seconds=60)
    assert result['status'] == 'available'
    assert [r['message'] for r in result['messages']] == ['observed warning', 'old normal message']
    assert result['causal_confirmation'] is False
    assert result['identity_attribution'] == 'unavailable'


def test_millisecond_timestamps_and_resource_prioritization(tmp_path):
    path = write_logs(tmp_path, [1700000100000, 1700000102000],
                      ['db message', 'frontend message'], ['ledger-db', 'frontend'])
    result = extract_log_evidence(path, as_of=1700000105, resource='ledger-db', max_results=1)
    assert result['messages'][0]['message'] == 'db message'


def test_mismatched_checksum_causes_abstention(tmp_path):
    path = write_logs(tmp_path, [1700000000], ['warning'])
    (tmp_path / 'logs.parquet.sha256').write_text('0' * 64)
    result = extract_log_evidence(path, as_of=1700000001)
    assert result['status'] == 'integrity_failure'
    assert result['messages'] == []


def test_missing_log_file_is_explicit(tmp_path):
    result = extract_log_evidence(tmp_path / 'logs.parquet', as_of=1700000001)
    assert result['status'] == 'not_imported'
    assert result['messages'] == []


def test_bounded_scan_is_explicit(tmp_path, monkeypatch):
    import analysis.re2_log_evidence as reader
    path = write_logs(tmp_path, [1700000000, 1700000001], ['first', 'unscanned'])
    monkeypatch.setattr(reader, 'MAX_SCAN_ROWS', 1)
    result = extract_log_evidence(path, as_of=1700000002)
    assert result['scan_complete'] is False
    assert result['rows_scanned'] == 1
    assert [row['message'] for row in result['messages']] == ['first']


def test_corrupt_parquet_is_unavailable(tmp_path):
    path = tmp_path / 'logs.parquet'
    path.write_bytes(b'not parquet')
    (tmp_path / 'logs.parquet.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest())
    assert extract_log_evidence(path, as_of=1700000001)['status'] == 'read_error'
