"""Native dispatch shared by the compatibility APIs. Never builds or downloads."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def executable():
    override = os.environ.get('DOT_STK100_BIN')
    candidates = [Path(override)] if override else [ROOT/'bin/dot-stk100', ROOT/'target/release/dot-stk100']
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise OSError('Native executable missing; build explicitly with cargo build --release --locked and install bin/dot-stk100')


def call(operation, *args):
    run = subprocess.run([executable(), 'bridge', operation, '--root', str(ROOT)],
                         input=json.dumps(args, ensure_ascii=False), text=True,
                         encoding='utf-8', capture_output=True)
    if run.returncode:
        raise ValueError(run.stderr.removeprefix('ERROR: ').strip())
    return json.loads(run.stdout)


def main(command, argv=None):
    import sys
    try:
        return subprocess.call([executable(), command, '--root', str(ROOT), *(sys.argv[1:] if argv is None else argv)])
    except OSError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
