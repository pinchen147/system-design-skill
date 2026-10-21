#!/usr/bin/env python3
"""Durable, host-driven investigation records; no model calls or command execution."""
import argparse
import json
import re
from pathlib import Path
import sys
import uuid

from session_runtime.records import KINDS, normalize, refresh, validate
from session_runtime.storage import RuntimeErrorDetail, atomic_write, digest, lock, parse, read, reject, snapshot


class Parser(argparse.ArgumentParser):
    def error(self, message):
        reject('invalid_arguments', message, 'Run design_session.py --help and supply the required arguments.')


def arguments():
    parser = Parser(description=__doc__, epilog='Bootstrap: status reads the raw design SHA; init with --expected-sha256 SHA adds investigation state. Mutations snapshot previous bytes. Records are JSON files, or stdin with --record -. See ../RUNTIME.md.')
    parser.add_argument('command', choices=['init', 'status', 'validate', 'checkpoint', 'resume', 'recover'] + list(KINDS))
    parser.add_argument('--design', required=True, type=Path)
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Root for repository-relative evidence paths (default: cwd)')
    parser.add_argument('--expected-sha256', help='Exact SHA returned by status; required for every mutation')
    parser.add_argument('--checkpoint-sha256', help='Exact history digest to restore; recover only')
    parser.add_argument('--record', help='JSON record file or - for stdin')
    return parser.parse_args()


def execute(args):
    path = args.design.absolute()
    if path.is_symlink():
        reject('invalid_path', 'Design must not be a symlink.')
    path = path.resolve()
    root = args.root.resolve()
    if not root.is_dir():
        reject('invalid_path', 'Root must be an existing directory.')
    command = args.command
    mutation = command not in ('status', 'validate')
    if mutation and not args.expected_sha256:
        reject('missing_argument', 'Mutation requires --expected-sha256.', 'Read status, inspect its records, and retry with that SHA.', ['--expected-sha256'])
    if command in KINDS and not args.record:
        reject('missing_argument', 'Record command requires --record.', 'Supply the JSON record file or stdin.', ['--record'])
    if command == 'recover' and not args.checkpoint_sha256:
        reject('missing_argument', 'Recovery requires --checkpoint-sha256.', 'Inspect the named history records and select a verified checkpoint explicitly.', ['--checkpoint-sha256'])
    if args.checkpoint_sha256 and command != 'recover':
        reject('invalid_arguments', '--checkpoint-sha256 is only accepted by recover.')
    if args.record and command not in KINDS:
        reject('invalid_arguments', '--record is only accepted by record commands.')
    if not mutation:
        raw, document = read(path)
        try:
            validate(document, root)
        except RuntimeErrorDetail as error:
            error.payload['observedSha256'] = digest(raw)
            error.payload['historyDirectory'] = str(path.parent / (path.stem + '.history'))
            raise
        result = {'ok': True, 'command': command, 'design': str(path), 'sha256': digest(raw),
                  'initialized': 'investigation' in document,
                  'investigation': document.get('investigation'),
                  'verification': 'Structural validation only; recorded judgments are not independently proven.'}
        if 'investigation' in document:
            # Inspect on a parsed copy; status never changes canonical state.
            projected = parse(raw)
            refresh(projected, root)
            result['freshnessChangesPending'] = projected != document
            result['investigation'] = projected['investigation']
            if result['freshnessChangesPending']:
                result['nextAction'] = 'Run resume with --expected-sha256 ' + digest(raw) + ' to persist these inspected invalidations.'
            if command == 'validate' and result['freshnessChangesPending']:
                reject('stale_evidence', 'Source bytes changed or became unavailable.', 'Run resume with the current design SHA, then re-evaluate affected claims.', ['--expected-sha256'])
        return result
    with lock(path):
        raw = path.read_bytes()
        if digest(raw) != args.expected_sha256:
            reject('conflict', 'Design changed since the supplied SHA.', 'Read status and reconcile your intended change with current records; retry with the new SHA.', ['--expected-sha256'])
        if command == 'recover':
            checkpoint_sha = args.checkpoint_sha256
            if not re.fullmatch('[0-9a-f]{64}', checkpoint_sha):
                reject('invalid_arguments', 'Checkpoint SHA must be 64 lowercase hexadecimal characters.')
            directory = path.parent / (path.stem + '.history')
            target = directory / (checkpoint_sha + '.json')
            if directory.is_symlink() or target.is_symlink():
                reject('invalid_path', 'Recovery history must not contain symlinks.')
            saved = target.read_bytes()
            if digest(saved) != checkpoint_sha:
                reject('checkpoint_corrupt', 'Checkpoint bytes do not match the requested digest.')
            document = parse(saved)
            validate(document, root)
            if 'investigation' not in document:
                reject('not_initialized', 'Recovery checkpoint has no investigation.', 'Select an initialized checkpoint; recover legacy design content explicitly outside this command.')
            refresh(document, root)
            for kind, success, pending in [('checks', 'pass', 'unknown'), ('questions', 'answered', 'partial'), ('unknowns', 'resolved', 'open')]:
                for record in document['investigation'][kind]:
                    if record['status'] == success:
                        record['status'] = pending
        else:
            document = parse(raw)
        validate(document, root)
        if command == 'checkpoint':
            return {'ok': True, 'command': command, 'design': str(path), 'sha256': digest(raw),
                    'checkpoint': str(snapshot(path, raw))}
        if command == 'init':
            if 'investigation' in document:
                reject('already_initialized', 'Investigation already exists.', 'Use status or resume; initialization never resets existing records.')
            document['investigation'] = {'session': {'id': 'session-' + uuid.uuid4().hex, 'revision': 0},
                                         'evidence': [], 'unknowns': [], 'questions': [], 'checks': []}
        else:
            if 'investigation' not in document:
                reject('not_initialized', 'Legacy design has no investigation.', 'Run init explicitly with the current design SHA.', ['--expected-sha256'])
            refresh(document, root)
            if command in KINDS:
                record = parse(sys.stdin.read() if args.record == '-' else Path(args.record).read_bytes())
                kind = KINDS[command]
                normalized = normalize(kind, record, root)
                records = document['investigation'][kind]
                previous = next((i for i, item in enumerate(records) if item['id'] == normalized['id']), None)
                if previous is not None and kind == 'evidence':
                    reject('immutable_evidence', 'Evidence id already exists.', 'Reuse the existing evidence reference, or capture new evidence under a new id.')
                if previous is None:
                    records.append(normalized)
                else:
                    records[previous] = normalized
            document['investigation']['session']['revision'] += 1
        validate(document, root)
        payload = (json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        checkpoint = snapshot(path, raw)
        # Catch noncooperating edits made while preparing the mutation.
        if digest(path.read_bytes()) != digest(raw):
            reject('conflict', 'Design changed while preparing the write.', 'Read status and reconcile before retrying.', ['--expected-sha256'])
        atomic_write(path, payload)
        return {'ok': True, 'command': command, 'design': str(path), 'sha256': digest(payload),
                'session': document['investigation']['session'], 'checkpoint': str(checkpoint)}


def main():
    try:
        result = execute(arguments())
    except RuntimeErrorDetail as error:
        result = {'ok': False, 'error': error.payload}
    except UnicodeError as error:
        result = {'ok': False, 'error': {'code': 'invalid_encoding', 'message': str(error),
                  'nextAction': 'Use valid UTF-8 Unicode text in the document and records.', 'neededArgs': []}}
    except OSError as error:
        result = {'ok': False, 'error': {'code': 'io_error', 'message': str(error),
                  'nextAction': 'Inspect the named path and permissions; preserve history. Read status before retrying because publication may already have completed.', 'neededArgs': []}}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
