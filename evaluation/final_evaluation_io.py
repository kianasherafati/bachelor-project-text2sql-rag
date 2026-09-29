"""Canonical UTF-8 artifacts, immutable case journal and fail-closed resume."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from contextlib import contextmanager

from evaluation.final_evaluation_contracts import IntegrityError, OUTCOMES


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf8')).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


_SECRET = re.compile(r'(?i)(?:password|pwd|uid|user\s*id|username|connection\s*string|'
                     r'access[_ -]?token|api[_ -]?key|authorization|server|data\s+source)\s*[:=]'
                     r'|(?:postgres(?:ql)?|mssql|mysql)://|\bBearer\s+\S+')


def safe_text(text):
    # Whole-field suppression avoids partial connection-string/credential leakage.
    return '[REDACTED_SENSITIVE_TEXT]' if _SECRET.search(text) else text


def clean(value):
    if isinstance(value, str):
        return safe_text(value)
    if isinstance(value, dict):
        return {safe_text(str(k)): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def atomic_new(path, data):
    """Publish a fully flushed file with no replacement, even across writers."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # atomic exclusive publication on NTFS/POSIX
    finally:
        os.unlink(temporary)


def publish(path, value):
    atomic_new(path, (canonical(clean(value)) + '\n').encode('utf8'))


@contextmanager
def run_lock(directory):
    """OS lock is released on process death. The lock file is never unlinked."""
    with (Path(directory) / '.writer.lock').open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise IntegrityError('RUN_ALREADY_ACTIVE') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class RunStore:
    def __init__(self, directory, manifest, resume=False):
        self.directory = Path(directory)
        self.manifest = manifest
        self.records = []
        self.chain = digest(manifest)
        target = self.directory / 'run_manifest.json'
        manifest_checksum = self.directory / 'run_manifest.sha256'
        if resume:
            try:
                if file_sha(target) != manifest_checksum.read_text(encoding='ascii').strip():
                    raise IntegrityError('CORRUPT_MANIFEST_CHECKSUM')
                existing = json.loads(target.read_text(encoding='utf8'))
                # Creation time belongs to the original run, not the resume attempt.
                wanted = dict(manifest, timestamp_utc=existing['timestamp_utc'])
                if existing != wanted:
                    raise IntegrityError('RESUME_MANIFEST_MISMATCH')
                self.manifest = existing
                self.chain = digest(existing)
            except (OSError, ValueError, KeyError) as exc:
                raise IntegrityError('CORRUPT_MANIFEST') from exc
        else:
            publish(target, manifest)
            atomic_new(manifest_checksum, (file_sha(target) + '\n').encode('ascii'))
        self.case_dir = self.directory / 'cases'
        self.case_dir.mkdir(exist_ok=resume)
        self.receipt_dir = self.directory / 'completion_receipts'
        self.receipt_dir.mkdir(exist_ok=resume)
        expected = self.manifest['case_order']
        paths = sorted(self.case_dir.glob('*.json'))
        receipts = sorted(self.receipt_dir.glob('*.sha256'))
        if [p.stem for p in paths] != [p.stem for p in receipts]:
            # A receipt is published BEFORE its case. A crash in that narrow
            # interval is deliberately blocked, never silently regenerated.
            raise IntegrityError('INCOMPLETE_OR_DELETED_COMPLETION')
        for i, path in enumerate(paths):
            try:
                entry = json.loads(path.read_text(encoding='utf8'))
                record = entry['record']
                if (path.name != f'{i:05d}.json' or i >= len(expected)
                        or record['case_id'] != expected[i]
                        or entry['previous_sha256'] != self.chain
                        or entry['sha256'] != digest({'previous_sha256': self.chain, 'record': record})
                        or receipts[i].read_text(encoding='ascii').strip() != file_sha(path)
                        or record['case_input_sha256'] != self.manifest['case_input_sha256'][i]):
                    raise IntegrityError('CORRUPT_CASE_JOURNAL')
                self.records.append(record)
                self.chain = entry['sha256']
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise IntegrityError('CORRUPT_CASE_JOURNAL') from exc
        if (self.directory / 'summary.json').exists() and len(self.records) != len(expected):
            raise IntegrityError('COMPLETED_JOURNAL_TRUNCATED')

    def append(self, record):
        i = len(self.records)
        if i >= len(self.manifest['case_order']) or record['case_id'] != self.manifest['case_order'][i]:
            raise IntegrityError('CASE_ORDER_OR_DUPLICATE')
        record = clean(record)
        entry = {'previous_sha256': self.chain, 'record': record}
        entry['sha256'] = digest(entry)
        encoded = (canonical(entry) + '\n').encode('utf8')
        atomic_new(self.receipt_dir / f'{i:05d}.sha256',
                   (hashlib.sha256(encoded).hexdigest() + '\n').encode('ascii'))
        publish(self.case_dir / f'{i:05d}.json', entry)
        self.chain = entry['sha256']
        self.records.append(record)

    def export(self):
        summary = aggregate(self.records, self.manifest['case_count'], self.manifest['label'])
        artifacts = {
            'per_case_results.jsonl': ''.join(canonical(r) + '\n' for r in self.records),
            'errors.jsonl': ''.join(canonical(r) + '\n' for r in self.records if r['error_stage']),
            'summary.json': canonical(summary) + '\n',
            'retrieval_metrics.json': canonical({'label': self.manifest['label'], 'cases': [
                {'case_id': r['case_id'], **r['retrieval_metrics']} for r in self.records]}) + '\n',
            'execution_accuracy_summary.json': canonical(summary) + '\n',
        }
        for name, data in artifacts.items():
            path = self.directory / name
            encoded = data.encode('utf8')
            if path.exists():
                if path.read_bytes() != encoded:
                    raise IntegrityError('CORRUPT_AGGREGATE')
            else:
                atomic_new(path, encoded)
        return summary


def aggregate(records, denominator, label):
    counts = {name: sum(r['execution_accuracy_outcome'] == name for r in records) for name in OUTCOMES}
    blocked = counts['EVALUATION_BLOCKED'] > 0 or len(records) != denominator
    metrics = [r['retrieval_metrics'] for r in records]
    return {'label': label, 'case_count': denominator, 'completed_count': len(records),
            'publication_status': 'BLOCKED' if blocked else 'COMPLETE',
            'outcome_counts': counts,
            'execution_accuracy': None if blocked else counts['EXECUTION_CORRECT'] / denominator,
            'valid_sql_count': sum(r['validation_status'] == 'SUCCESS' for r in records),
            'prediction_execution_success_count': sum(r['prediction_execution_status'] == 'SUCCESS' for r in records),
            'resource_censored_count': counts['EVALUATION_LIMIT'],
            'insufficient_schema_count': sum(r['generation_status'] == 'INSUFFICIENT_SCHEMA' for r in records),
            'mean_recall_at_10': math.fsum(m['recall_at_10'] or 0 for m in metrics) / denominator,
            'full_schema_coverage_rate': sum(m['full_schema_coverage'] is True for m in metrics) / denominator,
            'gold_strata': {name: {'count': sum(r['gold_result_metadata'].get('complete') is True and
                                              r['gold_result_metadata'].get('empty') is empty for r in records),
                                  'correct': sum(r['gold_result_metadata'].get('complete') is True and
                                                 r['gold_result_metadata'].get('empty') is empty and
                                                 r['execution_accuracy_outcome'] == 'EXECUTION_CORRECT' for r in records)}
                            for name, empty in [('empty', True), ('nonempty', False)]}}
