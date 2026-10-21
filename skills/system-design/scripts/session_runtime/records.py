"""Validate investigation records without asserting the truth of their claims."""
import re
from .storage import RuntimeErrorDetail, digest, reject, relative_path, safe_path

KINDS = {'record-evidence': 'evidence', 'record-unknown': 'unknowns',
         'record-question': 'questions', 'record-check': 'checks'}
FIELDS = {
    'evidence': {'id', 'claim', 'type', 'scope', 'limitations', 'sources', 'references', 'freshness'},
    'unknowns': {'id', 'question', 'status', 'evidenceRefs', 'resolution'},
    'questions': {'id', 'question', 'status', 'evidenceRefs', 'answer'},
    'checks': {'id', 'check', 'status', 'evidenceRefs', 'detail'},
}
STATUSES = {'unknowns': {'open', 'resolved'}, 'questions': {'open', 'partial', 'answered'},
            'checks': {'pass', 'fail', 'unknown'}}
TEXT = {'unknowns': 'resolution', 'questions': 'answer', 'checks': 'detail'}


def text(value, name, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        reject('invalid_record', name + ' must be a ' + ('string.' if empty else 'nonempty string.'))


def strings(value, name):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        reject('invalid_record', name + ' must be an array of nonempty strings.')


def shape(record, fields):
    if not isinstance(record, dict) or set(record) - fields:
        reject('invalid_record', 'Record contains unsupported fields or is not an object.')


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
        reject('invalid_record', 'id must use letters, digits, dot, underscore or hyphen.')


def normalize(kind, record, root):
    shape(record, FIELDS[kind] - ({'freshness'} if kind == 'evidence' else set()))
    value = dict(record)
    if kind == 'evidence':
        value.setdefault('references', [])
        value.setdefault('sources', [])
        sources = value['sources']
        if not isinstance(sources, list):
            reject('invalid_record', 'sources must be an array.')
        captured = []
        for source in sources:
            shape(source, {'path'})
            path = safe_path(root, source.get('path'))
            captured.append({'path': path.relative_to(root).as_posix(), 'sha256': digest(path.read_bytes())})
        value['sources'] = captured
        value['freshness'] = 'current' if captured else 'unknown'
    else:
        value.setdefault('status', {'checks': 'unknown', 'unknowns': 'open', 'questions': 'open'}[kind])
        value.setdefault('evidenceRefs', [])
        value.setdefault(TEXT[kind], '')
    validate_record(kind, value, root)
    return value


def validate_record(kind, value, root):
    shape(value, FIELDS[kind])
    if set(value) != FIELDS[kind]:
        reject('invalid_record', kind + ' record is missing required fields.')
    identity(value['id'])
    if kind == 'evidence':
        for field in ('claim', 'scope'):
            text(value[field], field)
        if value['type'] not in ('observed', 'derived', 'inferred'):
            reject('invalid_record', 'Unknown evidence type.')
        if value['freshness'] not in ('current', 'stale', 'unknown'):
            reject('invalid_record', 'Unknown evidence freshness.')
        strings(value['limitations'], 'limitations')
        strings(value['references'], 'references')
        if not isinstance(value['sources'], list):
            reject('invalid_record', 'sources must be an array.')
        for source in value['sources']:
            shape(source, {'path', 'sha256'})
            relative_path(source.get('path'))
            if not isinstance(source.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
                reject('invalid_record', 'Source requires its SHA-256.')
        if not value['sources'] and not value['references']:
            reject('invalid_record', 'Evidence requires a local source or an external reference.')
        if not value['sources'] and value['freshness'] == 'current':
            reject('invalid_record', 'External-only evidence freshness cannot be established locally.')
    else:
        text(value['check' if kind == 'checks' else 'question'], kind)
        text(value[TEXT[kind]], TEXT[kind], empty=True)
        strings(value['evidenceRefs'], 'evidenceRefs')
        if not isinstance(value['status'], str) or value['status'] not in STATUSES[kind]:
            reject('invalid_record', 'Unknown ' + kind + ' status.')


def is_success(kind, record):
    return record['status'] == {'checks': 'pass', 'unknowns': 'resolved', 'questions': 'answered'}[kind]


def validate(document, root):
    if 'investigation' not in document:
        return
    investigation = document['investigation']
    shape(investigation, {'session', 'evidence', 'unknowns', 'questions', 'checks'})
    if set(investigation) != {'session', 'evidence', 'unknowns', 'questions', 'checks'}:
        reject('invalid_record', 'Investigation requires session and all four record arrays.')
    session = investigation['session']
    shape(session, {'id', 'revision'})
    identity(session.get('id'))
    if set(session) != {'id', 'revision'} or type(session['revision']) is not int or session['revision'] < 0:
        reject('invalid_record', 'Session revision must be a nonnegative integer.')
    for kind in FIELDS:
        records = investigation[kind]
        if not isinstance(records, list):
            reject('invalid_record', kind + ' must be an array.')
        ids = set()
        for record in records:
            validate_record(kind, record, root)
            if record['id'] in ids:
                reject('invalid_record', 'Duplicate ' + kind + ' id: ' + record['id'])
            ids.add(record['id'])
    evidence = {record['id']: record for record in investigation['evidence']}
    for kind in ('unknowns', 'questions', 'checks'):
        for record in investigation[kind]:
            refs = record['evidenceRefs']
            if any(ref not in evidence for ref in refs):
                reject('dangling_reference', record['id'] + ' refers to missing evidence.')
            if is_success(kind, record):
                if not refs or not record[TEXT[kind]].strip():
                    reject('insufficient_evidence', record['id'] + ' requires evidence references and a written result.')
                if any(evidence[ref]['freshness'] != 'current' for ref in refs):
                    reject('insufficient_evidence', record['id'] + ' relies on stale or unknown evidence.', 'Capture new evidence and re-evaluate the claim; do not restore an older pass.')


def freshness(evidence, root):
    if evidence['freshness'] != 'current':
        return evidence['freshness']
    if not evidence['sources']:
        return 'unknown'
    for source in evidence['sources']:
        try:
            path = safe_path(root, source['path'])
            current = digest(path.read_bytes())
        except (OSError, RuntimeErrorDetail):
            return 'unknown'
        if current != source['sha256']:
            return 'stale'
    return 'current'


def refresh(document, root):
    investigation = document['investigation']
    invalid = set()
    for evidence in investigation['evidence']:
        evidence['freshness'] = freshness(evidence, root)
        if evidence['freshness'] != 'current':
            invalid.add(evidence['id'])
    for kind in ('unknowns', 'questions', 'checks'):
        for record in investigation[kind]:
            if is_success(kind, record) and invalid.intersection(record['evidenceRefs']):
                record['status'] = {'checks': 'unknown', 'unknowns': 'open', 'questions': 'partial'}[kind]
