"""No child process; task invokes pythonw directly from a stable user directory."""
from pathlib import Path
from datetime import datetime, timezone
import contextlib
import io
import json
import runpy
import sys

def main():
    root = Path(__file__).resolve().parent
    capture = io.StringIO()
    code = 0
    try:
        controller = root / 'petctl.py'
        if not controller.is_file() or not (root / 'bundle/manifest.json').is_file():
            raise FileNotFoundError('Stable runtime missing; re-register the task.')
        sys.argv = [str(controller), 'repair', '--bundle', str(root / 'bundle')]
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            try:
                runpy.run_path(str(controller), run_name='__main__')
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        code = 1
        capture.write(type(e).__name__ + ': ' + str(e))
    result = {'time': datetime.now(timezone.utc).isoformat(), 'exitCode': code,
              'output': capture.getvalue()[-8000:]}
    try:
        tmp = root / 'launcher-status.tmp'
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(root / 'launcher-status.json')
    except OSError:
        pass
    return code

if __name__ == '__main__':
    sys.exit(main())
