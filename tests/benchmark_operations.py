#!/usr/bin/env python3
"""Compare pre/post native operations and sequential/batched document calls.

Synthetic documents exercise the real subprocess/CLI/compatibility API paths.
This does not measure an AI session, model latency, or user productivity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]

def normalize(value):
    if isinstance(value,dict) and 'implementation_sha256' in value:
        value=dict(value)
        for field in ('implementation_sha256','implementation_kind','evaluation_schema_version'):value.pop(field,None)
    return value

def worker(args):
    root=Path(args.root);binary=str(Path(args.binary).resolve());cases=[json.loads(line) for line in Path(args.cases).read_text().splitlines() if line.strip()]
    if args.mode.startswith('api'):
        sys.path.insert(0,str(root));os.environ['DOT_STK100_BIN']=binary
        from scripts import lint_text
        if args.mode=='api-batch':result=lint_text.review_many(cases)
        else:result=[lint_text.review(c.get('source'),c['candidate']) for c in cases]
    elif args.mode=='cli-batch':
        result=json.loads(subprocess.check_output([binary,'lint-batch','--root',str(root),'--cases',args.cases]))
    else:
        directory=Path(args.cases).parent/'documents'
        result=[json.loads(subprocess.check_output([binary,'lint','--root',str(root),'--source',str(directory/f'{i}-source.txt'),'--candidate',str(directory/f'{i}-candidate.txt')])) for i in range(len(cases))]
    print(json.dumps(result,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--before-root',type=Path);p.add_argument('--before-bin',type=Path);p.add_argument('--after-bin',type=Path);p.add_argument('--output',type=Path);p.add_argument('--runs',type=int,default=11)
    p.add_argument('--worker',action='store_true');p.add_argument('--root');p.add_argument('--binary');p.add_argument('--cases');p.add_argument('--mode',choices=['api-repeat','api-batch','cli-repeat','cli-batch'])
    a=p.parse_args()
    if a.worker:worker(a);return 0
    if not all((a.before_root,a.before_bin,a.after_bin,a.output)):p.error('before-root, before-bin, after-bin and output are required')
    if a.runs<11:p.error('at least 11 runs are required')
    before_root=a.before_root.resolve();before_bin=a.before_bin.resolve();after_bin=a.after_bin.resolve();rows=[]
    with tempfile.TemporaryDirectory(prefix='stk-operations-') as tmp:
        tmp=Path(tmp);seed=[json.loads(line) for line in (before_root/'eval/seed-cases.jsonl').read_text().splitlines() if line.strip()];cases_file=tmp/'cases.jsonl';cases_file.write_text('\n'.join(json.dumps(c,ensure_ascii=False) for c in seed)+'\n');directory=tmp/'documents';directory.mkdir()
        for i,c in enumerate(seed):
            (directory/f'{i}-source.txt').write_text(c['source']);(directory/f'{i}-candidate.txt').write_text(c['candidate'])
        scenarios=[]
        for name,command,options in [('evaluate-seed','evaluate',[]),('evaluate-terms','evaluate',['--terminology-examples']),('lint-single','lint',['--source',str(directory/'0-source.txt'),'--candidate',str(directory/'0-candidate.txt')]),('render-check','render',['--check']),('validate','validate',[])]:
            scenarios.append((name,{'before':[str(before_bin),command,'--root',str(before_root),*options],'after':[str(after_bin),command,'--root',str(before_root),*options]}))
        def cmd(root,binary,mode,path=cases_file):return [sys.executable,str(Path(__file__).resolve()),'--worker','--root',str(root),'--binary',str(binary),'--cases',str(path),'--mode',mode]
        scenarios.append(('56-document-cli',{'before-repeat':cmd(before_root,before_bin,'cli-repeat'),'after-repeat':cmd(ROOT,after_bin,'cli-repeat'),'after-batch':cmd(ROOT,after_bin,'cli-batch')}))
        scenarios.append(('56-document-python-api',{'before-repeat':cmd(before_root,before_bin,'api-repeat'),'after-repeat':cmd(ROOT,after_bin,'api-repeat'),'after-batch':cmd(ROOT,after_bin,'api-batch')}))
        document_paths=['README.md','docs/LINTER.md','docs/IMPLEMENTATION-PLAN.md','docs/RUST-MIGRATION.md','references/DOT-STK100-SPEC.md','references/profiles/lite.md','references/profiles/core.md','references/profiles/audit.md']
        public=tmp/'public-documents';(public/'documents').mkdir(parents=True)
        public_cases=[]
        for i,path in enumerate(document_paths):
            text=(before_root/path).read_text();public_cases.append({'source':text,'candidate':text})
            (public/'documents'/f'{i}-source.txt').write_text(text);(public/'documents'/f'{i}-candidate.txt').write_text(text)
        public_input=public/'cases.jsonl';public_input.write_text('\n'.join(json.dumps(c,ensure_ascii=False) for c in public_cases)+'\n')
        public_input_sha256=hashlib.sha256(public_input.read_bytes()).hexdigest()
        scenarios.append(('8-package-documents-cli',{'before-repeat':cmd(before_root,before_bin,'cli-repeat',public_input),'after-repeat':cmd(ROOT,after_bin,'cli-repeat',public_input),'after-batch':cmd(ROOT,after_bin,'cli-batch',public_input)}))
        for name,commands in scenarios:
            reference=None;durations={k:[] for k in commands};hashes={k:[] for k in commands};mismatches=[]
            def collect(key,run):
                start=time.perf_counter_ns();r=subprocess.run(commands[key],capture_output=True);elapsed=(time.perf_counter_ns()-start)/1e6
                if r.returncode:raise RuntimeError(f'{name}/{key}: exit {r.returncode}: {r.stderr.decode(errors="replace")}')
                raw=r.stdout
                if name in ('render-check',):value=raw.decode()
                elif name=='validate':
                    lines=raw.decode().splitlines();value=[lines[0],json.loads(lines[1]),*lines[2:]]
                else:value=normalize(json.loads(raw))
                return elapsed,raw,value
            for key in commands:
                _,raw,value=collect(key,'warmup')
                if reference is None:reference=value
                if value!=reference:mismatches.append({'implementation':key,'run':'warmup','stdout':raw.decode(errors='replace')})
            for i in range(a.runs):
                keys=list(commands)
                if i%2:keys.reverse()
                for key in keys:
                    elapsed,raw,value=collect(key,i+1);durations[key].append(elapsed);hashes[key].append(hashlib.sha256(raw).hexdigest())
                    if value!=reference:mismatches.append({'implementation':key,'run':i+1,'stdout':raw.decode(errors='replace')})
            rows.append({'scenario':name,'median_ms':{k:statistics.median(v) for k,v in durations.items()},'durations_ms':durations,'output_sha256_by_run':hashes,'all_equivalent':not mismatches,'mismatches':mismatches})
            print(name,rows[-1]['median_ms'],'equal',not mismatches,flush=True)
    result={'before_sha':'7fcfbb7a17049b852ffab89ac672eb2dd9ec2407','before_binary_sha256':hashlib.sha256(before_bin.read_bytes()).hexdigest(),'after_binary_sha256':hashlib.sha256(after_bin.read_bytes()).hexdigest(),'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'runs':a.runs,'warmup_runs':1,'seed_cases':56,'public_document_paths':document_paths,'public_input_sha256':public_input_sha256,'repeat_worker_overhead':'both repeat and batch include one Python controller startup; API repeat uses one Python interpreter with one native subprocess per document','rows':rows}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return any(not row['all_equivalent'] for row in rows)

if __name__=='__main__':sys.exit(main())
