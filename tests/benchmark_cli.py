#!/usr/bin/env python3
"""Alternate baseline/native CLI runs; record all durations, medians and output checks."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

from compare_python import verify_baseline

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--binary',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--runs',type=int,default=11);a=p.parse_args()
    if a.runs<11:p.error('at least 11 runs required')
    provenance=verify_baseline(a.baseline)
    rows=[]
    with tempfile.TemporaryDirectory(prefix='stk-bench-') as tmp:
        tmp=Path(tmp)
        scenarios=[]
        for size,n in [('small',1),('medium',30),('large',150)]:
            source=tmp/f'{size}-source.md';candidate=tmp/f'{size}-candidate.md'
            source.write_text('앱은 3회 재시도할 수 있습니다.\n'*n);candidate.write_text('앱은 5회 재시도합니다.\n'*n)
            scenarios.append((f'lint-{size}','lint_text.py','lint',['--source',str(source),'--candidate',str(candidate)]))
        scenarios += [('evaluate-seed','evaluate_linter.py','evaluate',[]),('evaluate-terms','evaluate_linter.py','evaluate',['--terminology-examples']),('render-check','render_rules.py','render',['--check']),('validate','validate_package.py','validate',[])]
        for name,script,command,options in scenarios:
            commands={'python':[sys.executable,str(a.baseline.resolve()/'scripts'/script),*options]}
            if a.binary:
                # Both tools inspect identical baseline assets, including structure.
                commands['native']=[str(a.binary.resolve()),command,'--root',str(a.baseline.resolve()),*options]
                commands['adapter']=[sys.executable,str(ROOT/'scripts'/script),*options]
            def equivalent(raw,expected):
                if name.startswith('evaluate'):
                    actual=json.loads(raw);reference=json.loads(expected)
                    for obj in (actual,reference):
                        for field in ('implementation_sha256','implementation_kind','evaluation_schema_version'):obj.pop(field,None)
                    return actual==reference
                if name.startswith('lint'):return json.loads(raw)==json.loads(expected)
                if name=='validate':
                    aa=raw.decode().splitlines();bb=expected.decode().splitlines()
                    return aa[0]==bb[0] and json.loads(aa[1])==json.loads(bb[1]) and aa[2:]==bb[2:]
                return raw==expected
            times={k:[] for k in commands};outputs={k:[] for k in commands};mismatches=[]
            reference=subprocess.run(commands['python'],capture_output=True,check=True).stdout
            for key,argv in commands.items():
                warmup=subprocess.run(argv,capture_output=True,check=True).stdout
                if not equivalent(warmup,reference):mismatches.append({'implementation':key,'run':'warmup','stdout':warmup.decode(errors='replace')})
            for i in range(a.runs):
                keys=list(commands)
                if i%2:keys.reverse()
                for key in keys:
                    start=time.perf_counter_ns();r=subprocess.run(commands[key],capture_output=True,check=True)
                    times[key].append((time.perf_counter_ns()-start)/1e6)
                    outputs[key].append(hashlib.sha256(r.stdout).hexdigest())
                    if not equivalent(r.stdout,reference):mismatches.append({'implementation':key,'run':i+1,'stdout':r.stdout.decode(errors='replace')})
            rows.append({'scenario':name,'durations_ms':times,'median_ms':{k:statistics.median(v) for k,v in times.items()},'outputs_equivalent':not mismatches,'output_sha256_by_run':outputs,'mismatches':mismatches})
    result={'baseline_manifest_sha256':provenance,'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest() if a.binary else None,'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'runs':a.runs,'warmup_runs':1,'build':'release when native present','rows':rows}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scenarios':len(rows),'runs':a.runs,'all_equivalent':all(r['outputs_equivalent'] for r in rows)}))
    return not all(r['outputs_equivalent'] for r in rows)
if __name__=='__main__':sys.exit(main())
