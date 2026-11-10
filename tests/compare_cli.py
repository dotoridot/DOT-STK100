#!/usr/bin/env python3
"""Compare actual CLI entrypoints, input bytes, renderer writes and error exits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from compare_python import verify_baseline

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True,type=Path);p.add_argument('--binary',required=True,type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=verify_baseline(a.baseline);rows=[]
    def run(command,options,root,files=(),json_output=False):
        script={'lint':'lint_text.py','evaluate':'evaluate_linter.py','render':'render_rules.py','validate':'validate_package.py'}[command]
        before={str(f):f.read_bytes() for f in files if f.exists()}
        # Renderer calls both implementations on identical throwaway package bytes.
        spec=root/'references/DOT-STK100-SPEC.md';original=spec.read_bytes() if spec.exists() else None
        native=subprocess.run([str(a.binary.resolve()),command,'--root',str(root),*options],capture_output=True)
        after_native=spec.read_bytes() if spec.exists() else None
        if original is not None:spec.write_bytes(original)
        python=subprocess.run([sys.executable,str(a.baseline.resolve()/'scripts'/script),*(['--root',str(root)] if command in ('render','validate') else []),*options],capture_output=True)
        after_python=spec.read_bytes() if spec.exists() else None
        same=native.returncode==python.returncode and native.returncode in (0,1,2)
        if native.returncode==0:
            if json_output:
                n=json.loads(native.stdout);b=json.loads(python.stdout)
                if command=='evaluate':
                    for obj in (n,b):obj.pop('implementation_sha256',None);obj.pop('implementation_kind',None)
                same &= n==b
            elif command=='validate':
                n=native.stdout.decode().splitlines();b=python.stdout.decode().splitlines();same &= n[0]==b[0] and json.loads(n[1])==json.loads(b[1]) and n[2:]==b[2:]
            else:same &= native.stdout==python.stdout
        else:
            # argparse and OS/JSON libraries use different diagnostic prose, but
            # all errors must be visible, with empty stdout and no traceback.
            same &= bool(native.stderr.strip()) and not native.stdout and b'Traceback' not in native.stderr
            if command=='render' and python.returncode==1:same &= native.stderr==python.stderr
            if command=='validate':same &= native.stderr==python.stderr
        same &= after_native==after_python
        unchanged=all(f.exists() and f.read_bytes()==raw for name,raw in before.items() for f in [Path(name)])
        same &= unchanged
        rows.append({'command':command,'options':options,'python_exit':python.returncode,'native_exit':native.returncode,'equal':bool(same),'inputs_unchanged':unchanged,'python_stderr':python.stderr.decode(errors='replace'),'native_stderr':native.stderr.decode(errors='replace')})
    with tempfile.TemporaryDirectory(prefix='stk-cli-') as tmp:
        root=Path(tmp)/'package';shutil.copytree(a.baseline,root,ignore=shutil.ignore_patterns('__pycache__','.git'))
        src=root/'source.txt';dst=root/'candidate.txt';config=root/'terms.json'
        src.write_bytes('😀e\u0301\r\n3회 실행할 수 있습니다.'.encode());dst.write_bytes('😀e\u0301\r\n5회 실행합니다.'.encode())
        run('lint',['--source',str(src),'--candidate',str(dst)],root,[src,dst],True)
        run('lint',['--candidate',str(dst)],root,[src,dst],True)
        for options in [[],['--candidate',str(root/'missing')],['--candidate',str(dst),'--format','xml'],['--unknown']]:run('lint',options,root,[src,dst])
        dst.write_bytes(b'\xff');run('lint',['--candidate',str(dst)],root,[src,dst]);dst.write_text('3회')
        for raw in ['{bad','{}','{"groups": []}']:
            config.write_text(raw);run('lint',['--candidate',str(dst),'--terms',str(config)],root,[src,dst,config],True)
        config.unlink()
        run('evaluate',[],root,json_output=True);run('evaluate',['--terminology-examples'],root,json_output=True)
        for raw in ['', '{}', '{bad', '{"case_id":"x","split":"holdout"}']:
            cases=root/'cases.jsonl';cases.write_text(raw);run('evaluate',['--cases',str(cases)],root,[cases]);cases.unlink()
        run('evaluate',['--cases',str(root/'missing')],root)
        run('evaluate',['--cases',str(root/'missing'),'--terminology-examples'],root)
        run('render',['--check'],root)
        spec=root/'references/DOT-STK100-SPEC.md';valid=spec.read_bytes()
        spec.write_bytes(valid.replace(b'<!-- BEGIN GENERATED RULES -->',b'<!-- BEGIN GENERATED RULES -->\nstale'))
        run('render',['--check'],root,[spec]);run('render',[],root)
        spec.write_text('no markers');run('render',[],root,[spec]);spec.write_bytes(valid)
        spec.write_bytes(valid.replace(b'\n',b'\r\n'));run('render',['--check'],root,[spec]);run('render',[],root);spec.write_bytes(valid)
        run('validate',[],root)
        (root/'README.md').unlink();run('validate',[],root)
    summary={'baseline_manifest_sha256':manifest,'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest(),'comparisons':len(rows),'failures':sum(not r['equal'] for r in rows)}
    a.output.write_text(json.dumps({'summary':summary,'rows':rows},ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary))
    for row in rows:
        if not row['equal']:print(json.dumps(row,ensure_ascii=False))
    return bool(summary['failures'])
if __name__=='__main__':sys.exit(main())
