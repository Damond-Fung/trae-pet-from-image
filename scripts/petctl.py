"""TRAE pet: stdlib snapshot, immutable bundle, guarded deployment and recovery.

This does not generate artwork or write a renderer. The invoking TRAE Agent does.
No process termination, network calls or user-setting edits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
from datetime import datetime, timezone

MEDIA_REL = Path('out/vs/platform/iCubeFloatingChat/electron-main/media')
CONTRACT = ['floatingButton.html', 'floatingButton-preload.js', 'traebao/renderer.js',
            '@app/out/main.js', '@app/package.json', '@app/product.json']


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.pet-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save(path, data):
    atomic(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def contained(root, rel):
    p = PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts or '\\' in rel or ':' in rel:
        raise ValueError('Unsafe relative path: ' + rel)
    target = (Path(root) / rel).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError('Path escaped root: ' + rel)
    return target


def app_root(media):
    p = media.resolve()
    for parent in p.parents:
        if (parent / MEDIA_REL).resolve() == p:
            return parent
    raise ValueError('Media must be the iCubeFloatingChat/electron-main/media directory')


def contract_path(media, key):
    return contained(app_root(media), key[5:]) if key.startswith('@app/') else contained(media, key)


def discover(explicit):
    if explicit:
        result = Path(explicit).resolve()
    else:
        local = os.environ.get('LOCALAPPDATA', '')
        candidates = [Path(local) / 'Programs/Trae CN/resources/app' / MEDIA_REL,
                      Path(local) / 'Programs/Trae/resources/app' / MEDIA_REL]
        result = next((p for p in candidates if (p / 'floatingButton.html').is_file()), None)
        if result is None:
            raise ValueError('Cannot discover installation; inspect running executable and use --media')
    app_root(result)
    if not (result / 'floatingButton.html').is_file():
        raise ValueError('Missing floatingButton.html')
    return result


def inspect(args):
    media = discover(args.media)
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Snapshot directory must be new or empty')
    hashes = {}
    for key in CONTRACT:
        source = contract_path(media, key)
        if not source.is_file():
            raise ValueError('Required contract file missing: ' + key)
        hashes[key] = digest(source)
        dest = contained(out / 'source', key.replace('@app/', '_app/'))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    assets = []
    root = media / 'icons/traebao'
    for source in sorted(root.rglob('*')):
        if source.is_file():
            assets.append({'file': source.relative_to(media).as_posix(),
                           'sha256': digest(source), 'bytes': source.stat().st_size})
    save(out / 'snapshot.json', {'schema': 1, 'media': str(media), 'contract': hashes,
                               'assets': assets, 'created': datetime.now(timezone.utc).isoformat()})
    return {'snapshot': str(out), 'media': str(media), 'contractFiles': len(hashes),
            'nativeAssets': len(assets)}


def payload_paths(root):
    result = []
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Payload symlinks forbidden')
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if rel != 'floatingButton.html' and not rel.startswith('custom-pet/'):
                raise ValueError('Payload may only change HTML and custom-pet/: ' + rel)
            contained(root, rel)
            result.append(rel)
    if 'floatingButton.html' not in result or 'custom-pet/renderer.js' not in result:
        raise ValueError('Payload needs floatingButton.html and custom-pet/renderer.js')
    return result


def bundle(args):
    snapshot, payload, out = map(lambda p: Path(p).resolve(), [args.snapshot, args.payload, args.out])
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new bundle directory; bundles are immutable')
    snap = read(snapshot / 'snapshot.json')
    if set(snap['contract']) != set(CONTRACT):
        raise ValueError('Incomplete native contract')
    # Verify all snapshot files too, so a hand-edited snapshot cannot become a baseline.
    for key, expected in snap['contract'].items():
        if digest(contained(snapshot / 'source', key.replace('@app/', '_app/'))) != expected:
            raise ValueError('Snapshot has changed: ' + key)
    paths = payload_paths(payload)
    if digest(payload / 'floatingButton.html') == snap['contract']['floatingButton.html']:
        raise ValueError('Payload entry equals native entry; no adapter was produced')
    # Copy frozen input; deployment never reads a mutable working payload.
    shutil.copytree(snapshot, out / 'native')
    shutil.copytree(payload, out / 'payload')
    manifest = {'schema': 1, 'media': snap['media'], 'contract': snap['contract'],
                'payload': {rel: digest(contained(out / 'payload', rel)) for rel in paths}}
    save(out / 'manifest.json', manifest)
    return {'bundle': str(out), 'payloadFiles': len(paths)}


def load_bundle(path):
    root = Path(path).resolve()
    m = read(root / 'manifest.json')
    if m.get('schema') != 1 or set(m['contract']) != set(CONTRACT):
        raise ValueError('Invalid manifest')
    if set(payload_paths(root / 'payload')) != set(m['payload']):
        raise ValueError('Payload inventory changed')
    media = discover(m['media'])
    for rel, expected in m['payload'].items():
        if digest(contained(root / 'payload', rel)) != expected:
            raise ValueError('Payload checksum mismatch: ' + rel)
    return root, m, media


def compatibility(m, media):
    mismatches = []
    for key, expected in m['contract'].items():
        path = contract_path(media, key)
        allowed = {expected}
        if key == 'floatingButton.html':
            allowed.add(m['payload']['floatingButton.html'])
        if not path.is_file() or digest(path) not in allowed:
            mismatches.append(key)
    return mismatches


def status_data(m, media):
    mismatch = compatibility(m, media)
    if mismatch:
        return {'state': 'needs-adaptation', 'changedContract': mismatch}
    changed = [rel for rel, expected in m['payload'].items()
               if not contained(media, rel).is_file() or digest(contained(media, rel)) != expected]
    return {'state': 'installed' if not changed else 'repairable', 'changedPayload': changed,
            'activation': 'not-verified-by-this-script'}


def event(root, result):
    result = dict(result, time=datetime.now(timezone.utc).isoformat())
    save(root / 'update-status.json', result)
    with (root / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')


def apply_bundle(root, m, media):
    mismatch = compatibility(m, media)
    if mismatch:
        raise ValueError('Unknown installation contract; refusing overwrite: ' + ', '.join(mismatch))
    # Pre-read everything before touching the client; HTML is published last.
    paths = sorted(m['payload'], key=lambda rel: rel == 'floatingButton.html')
    originals, data = {}, {}
    for rel in paths:
        path = contained(media, rel)
        originals[rel] = path.read_bytes() if path.exists() else None
        data[rel] = contained(root / 'payload', rel).read_bytes()
    backup = root / 'backup'
    if not (backup / 'index.json').exists():
        # Never adopt already patched HTML as native backup.
        if hashlib.sha256(originals['floatingButton.html']).hexdigest() != m['contract']['floatingButton.html']:
            raise ValueError('Native backup missing for already patched entry')
        index = {}
        for rel, content in originals.items():
            index[rel] = hashlib.sha256(content).hexdigest() if content is not None else None
            if content is not None:
                atomic(contained(backup / 'files', rel), content)
        save(backup / 'index.json', index)
    written = []
    try:
        for rel in paths:
            # Detect an updater racing this operation, rather than overwrite new files.
            if compatibility(m, media):
                raise ValueError('Installation changed during deployment')
            target = contained(media, rel)
            atomic(target, data[rel])
            written.append(rel)
            if digest(target) != m['payload'][rel]:
                raise ValueError('Installed checksum mismatch: ' + rel)
    except Exception:
        for rel in reversed(written):
            target = contained(media, rel)
            # Do not undo an updater or unrelated editor that won the race.
            if target.is_file() and digest(target) == m['payload'][rel]:
                if originals[rel] is None:
                    target.unlink()
                else:
                    atomic(target, originals[rel])
        raise
    return status_data(m, media)


def restore(root, m, media):
    index = read(root / 'backup/index.json')
    if set(index) != set(m['payload']):
        raise ValueError('Backup inventory mismatch')
    # An unknown client version must not receive even an old native HTML backup.
    if compatibility(m, media):
        raise ValueError('Unknown updated contract; leave current client untouched')
    for rel, expected in index.items():
        if expected is not None and digest(contained(root / 'backup/files', rel)) != expected:
            raise ValueError('Backup checksum mismatch: ' + rel)
        path = contained(media, rel)
        allowed = {m['payload'][rel], expected}
        if path.exists() and digest(path) not in allowed:
            raise ValueError('File changed since install; restore stopped: ' + rel)
    # Restore entry first, then its private dependencies.
    for rel in sorted(index, key=lambda rel: rel != 'floatingButton.html'):
        path = contained(media, rel)
        if path.exists() and digest(path) == m['payload'][rel]:
            if index[rel] is None:
                path.unlink()
            else:
                atomic(path, contained(root / 'backup/files', rel).read_bytes())
    return {'state': 'restored', 'activation': 'reload-pet-required'}


def run(args):
    if args.command == 'inspect':
        return inspect(args)
    if args.command == 'bundle':
        return bundle(args)
    root, m, media = load_bundle(args.bundle)
    lock = root / '.operation.lock'
    # OS advisory lock releases on crash; all mutations use it.
    with lock.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if lock.stat().st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = status_data(m, media)
        if args.command == 'restore':
            result = restore(root, m, media)
        elif args.command == 'apply':
            result = apply_bundle(root, m, media)
        elif args.command == 'repair' and state['state'] == 'repairable':
            result = dict(apply_bundle(root, m, media), action='reapplied', reloadRequired=True)
        else:
            result = state
        if args.command != 'status':
            # Do not spam unchanged periodic status into the journal.
            previous = read(root / 'update-status.json') if (root / 'update-status.json').exists() else {}
            comparable = {k: v for k, v in previous.items() if k != 'time'}
            if comparable != result:
                event(root, result)
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('inspect'); q.add_argument('--media'); q.add_argument('--out', required=True)
    q = sub.add_parser('bundle')
    for name in ['snapshot', 'payload', 'out']:
        q.add_argument('--' + name, required=True)
    for command in ['apply', 'status', 'repair', 'restore']:
        q = sub.add_parser(command); q.add_argument('--bundle', required=True)
    args = p.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result.get('state') == 'needs-adaptation' else 0
    except Exception as e:
        result = {'state': 'error', 'error': str(e)}
        if getattr(args, 'bundle', None):
            root = Path(args.bundle).resolve()
            if root.is_dir():
                event(root, result)
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
