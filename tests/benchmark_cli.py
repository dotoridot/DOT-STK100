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

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--binary',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--runs',type=int,default=11);a=p.parse_args()
    if a.runs<11:p.error('at least 11 runs required')
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
            times={k:[] for k in commands};outputs={}
            for argv in commands.values():subprocess.run(argv,capture_output=True,check=True)
            for i in range(a.runs):
                keys=list(commands)
                if i%2:keys.reverse()
                for key in keys:
                    start=time.perf_counter_ns();r=subprocess.run(commands[key],capture_output=True,check=True);times[key].append((time.perf_counter_ns()-start)/1e6);outputs[key]=r.stdout
            equivalent=True
            for key,raw in outputs.items():
                expected=outputs['python']
                if name.startswith('evaluate'):
                    actual=json.loads(raw);reference=json.loads(expected)
                    for obj in (actual,reference):obj.pop('implementation_sha256',None);obj.pop('implementation_kind',None)
                    equivalent &= actual==reference
                elif name.startswith('lint'):equivalent &= json.loads(raw)==json.loads(expected)
                elif name=='validate':
                    aa=raw.decode().splitlines();bb=expected.decode().splitlines();equivalent &= aa[0]==bb[0] and json.loads(aa[1])==json.loads(bb[1]) and aa[2:]==bb[2:]
                else:equivalent &= raw==expected
            rows.append({'scenario':name,'durations_ms':times,'median_ms':{k:statistics.median(v) for k,v in times.items()},'outputs_equivalent':equivalent,'output_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in outputs.items()}})
    result={'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'runs':a.runs,'warmup_runs':1,'build':'release when native present','rows':rows}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scenarios':len(rows),'runs':a.runs,'all_equivalent':all(r['outputs_equivalent'] for r in rows)}))
    return not all(r['outputs_equivalent'] for r in rows)
if __name__=='__main__':sys.exit(main())
