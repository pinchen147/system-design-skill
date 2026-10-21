"""JSON storage with cooperating-writer exclusion and content-addressed preimages."""
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


class RuntimeErrorDetail(Exception):
    def __init__(self, code, message, action, needed=None):
        self.payload = {'code': code, 'message': message, 'nextAction': action,
                        'neededArgs': needed or []}
        super().__init__(message)


def reject(code, message, action='Correct the named record, then retry with the current design SHA.', needed=None):
    raise RuntimeErrorDetail(code, message, action, needed)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('non-finite number: ' + value)
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('non-finite number: ' + value)
        return number
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite)
    except (ValueError, UnicodeError) as error:
        reject('invalid_json', str(error), 'Preserve the damaged file; inspect sibling history snapshots and recover a verified preimage explicitly.')
    if not isinstance(value, dict):
        reject('invalid_record', 'Expected a JSON object.')
    return value


def read(path):
    raw = path.read_bytes()
    try:
        return raw, parse(raw)
    except RuntimeErrorDetail as error:
        error.payload['observedSha256'] = digest(raw)
        error.payload['historyDirectory'] = str(path.parent / (path.stem + '.history'))
        raise


def relative_path(relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        reject('invalid_path', 'Source paths must be nonempty root-relative paths.')
    if '..' in Path(relative).parts:
        reject('invalid_path', 'Parent traversal is not a source path.')
    return Path(relative)


def safe_path(root, relative):
    path = root / relative_path(relative)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        reject('invalid_path', 'Source escapes the declared root.')
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            reject('invalid_path', 'Symlink source paths are not admitted.')
        cursor = cursor.parent
    return path


def sync_directory(directory):
    if os.name == 'nt':
        return
    fd = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def snapshot(path, raw):
    directory = path.parent / (path.stem + '.history')
    if directory.is_symlink():
        reject('invalid_path', 'History directory must not be a symlink.')
    directory.mkdir(exist_ok=True)
    target = directory / (digest(raw) + '.json')
    if target.is_symlink():
        reject('invalid_path', 'History record must not be a symlink.')
    if target.exists():
        if target.read_bytes() != raw:
            reject('checkpoint_corrupt', 'Existing checkpoint does not match its digest.', 'Preserve the corrupt checkpoint and repair it from verified bytes; do not overwrite it.')
        return target
    # Publish only a complete synced snapshot. Cooperating writers hold the design lock.
    atomic_write(target, raw)
    return target


def atomic_write(path, raw):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def lock(path):
    lock_path = path.with_name('.' + path.name + '.lock')
    if lock_path.is_symlink():
        reject('invalid_path', 'Lock path must not be a symlink.')
    with lock_path.open('a+b') as stream:
        if os.name == 'nt':
            import msvcrt
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b'\0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                reject('busy', 'Another process owns the design lock.', 'Wait for the owner to finish; then reread status before retrying. Never delete the lock file.')
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                reject('busy', 'Another process owns the design lock.', 'Wait for the owner to finish; then reread status before retrying. Never delete the lock file.')
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
