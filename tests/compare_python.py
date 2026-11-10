#!/usr/bin/env python3
"""Compare native APIs to an immutable, separately archived Python baseline.

Only synthetic public fixtures are used. This proves parity for these inputs,
not semantic validity, host model behavior, or unobserved external consumers.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '71737d3d10885c77824defb35675405fa5657adb'
ORACLE = r'''
import dataclasses,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from scripts import lint_text as l, evaluate_linter as e, render_rules as r, validate_package as p
for line in sys.stdin:
    item=json.loads(line); op=item['op']; a=item['args']
    try:
        if op=='mask': a[1]=[l.Token(**x) for x in a[1]]
        if op=='validate': a[0]=Path(a[0])
        if op=='local_link_errors': a[:2]=[Path(x) for x in a[:2]]
        if op in ('validate_rules','validate_cases','validate_terminology','validate_expressions'): a[1]=set(a[1])
        module=l if op in ('review','protected','mask','validate_term_config') else e if op=='evaluate' else r if op in ('cell','render_table','render_document') else p
        result=getattr(module,op)(*a)
        print(json.dumps({'ok':result},ensure_ascii=False,default=lambda x:dataclasses.asdict(x)),flush=True)
    except Exception as ex:
        print(json.dumps({'error':str(ex),'error_type':type(ex).__name__}),flush=True)
'''

def inputs(baseline, section):
    load = lambda name: json.loads((baseline/name).read_text())
    if section in ('all','lint'):
        seed=[json.loads(x) for x in (baseline/'eval/seed-cases.jsonl').read_text().splitlines() if x.strip()]
        terms=load('references/terminology.json')
        expressions=load('references/preferred-expressions.json')
        cases=seed+[ex for d in (terms,expressions) for ent in d['entries'] for ex in ent['examples']]
        for case in cases:
            yield 'review',[case['source'],case['candidate'],None]
        edge=['', '3회', '😀e\u0301\r\n3회', '١٢회 １２초 ²3회', '가\u0301면\u200d 4회',
              '```py\r\n3회\r\n````\r\n끝', '~~~\n5회', '`a` ``b ` c``', '``x``` y`',
              '> 3회\r\n| 4회 |\nINFO x 5회', '[이름](a(b)c) https://a.example/x',
              '“3회” ‘4회’ "5회"', 'WARN\u001c3회\u0085끝', '```\u2028값 4회\u2029```',
              '전송됩니다. 이것 해당 프로세스', '캐시 cache 초기화를 수행합니다.', 'a_1 FOO fooBar',
              '\r', '\v', '\f', '\x1c', '\x1d', '\x1e', '\x85', '\u2028', '\u2029']
        for text in edge:
            for src in (None,'',text): yield 'review',[src,text,None]
            yield 'protected',[text]
        for sep in ['\n','\r\n','\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029']:
            yield 'review',[f'```{sep}3회{sep}```{sep}',f'```{sep}4회{sep}```{sep}',None]
        rng=random.Random(100)
        vocab=['3회','5회','API_CALL','허용하지 않습니다.','실행할 수 있습니다.','조건이면','😀','`x`']
        for _ in range(80):
            a=[rng.choice(vocab) for _ in range(rng.randrange(1,35))]; b=a.copy()
            for _ in range(rng.randrange(1,5)):
                b.insert(rng.randrange(len(b)+1),rng.choice(vocab))
                if b: b.pop(rng.randrange(len(b)))
            yield 'review',[' '.join(a),' '.join(b),None]
        for n in (199,200,250): yield 'review',['3회 '*n+'5회','5회 '+'3회 '*n,None]
        custom={'groups':[{'id':'CUSTOM','canonical':'캐시','variants':['cache']}], 'extra': {'z':1,'a':'한글'}}
        yield 'review',[None,'캐시 cache',custom]
        for literal in [r'\s',r'\b',r'\\b',r'\d',r'A\s']:
            yield 'review',[None,literal+' alias',{'groups':[{'id':'LITERAL','canonical':literal,'variants':['alias']}]}]
        for number in [0.1,1e-7,1e-5,1e16,1e20,-0.0,123456789012345678901234567890]:
            yield 'review',[None,'캐시 cache',dict(custom,extra={'number':number})]
        for bad in [None,[],{}, {'groups':None}, {'groups':[{}]}, {'groups':[{'id':'x','canonical':'a','variants':['a']}]}, {'groups':[{'id':'x','canonical':'a','variants':['b']}, {'id':'x','canonical':'b','variants':['c']}]}]:
            yield 'validate_term_config',[bad]
        yield 'evaluate',[[]]
        yield 'evaluate',[seed]
        yield 'evaluate',[[dict(ex,case_id=f'{en["id"]}-{i}',pair_id=en['id']) for en in terms['entries'] for i,ex in enumerate(en['examples'],1)]]
    if section in ('all','render'):
        rules=load('rules/rules.json')['rules']
        for value in ['A | B\r\nC\rD','한글 😀','']:
            yield 'cell',[value]
        for text in ['prefix\n<!-- BEGIN GENERATED RULES -->\nold\n<!-- END GENERATED RULES -->\nsuffix','no markers','<!-- END GENERATED RULES --><!-- BEGIN GENERATED RULES -->','<!-- BEGIN GENERATED RULES --><!-- BEGIN GENERATED RULES --><!-- END GENERATED RULES -->']:
            yield 'render_document',[text,rules]
        for value in [rules,[],[{}],[None],[dict(rules[0],requirement='A|B\r\nC\rD')]]:
            yield 'render_table',[value]
    if section in ('all','package'):
        objects=[('validate_sources',load('references/sources.json'),'sources'),('validate_rules',load('rules/rules.json'),'rules'),('validate_terminology',load('references/terminology.json'),'entries'),('validate_expressions',load('references/preferred-expressions.json'),'entries')]
        source_ids=[s['id'] for s in objects[0][1]['sources']]
        rule_ids=[r['id'] for r in objects[1][1]['rules']]
        for op,obj,key in objects:
            suffix=[] if op=='validate_sources' else [source_ids if op=='validate_rules' else rule_ids]
            for bad in [None,[],{}, {key:None},{key:[]},{key:[None]},obj]: yield op,[bad,*suffix]
            duplicate=copy.deepcopy(obj);duplicate[key].append(copy.deepcopy(duplicate[key][0]));yield op,[duplicate,*suffix]
            for field in obj[key][0]:
                for val in [None,[],{},'',17,'UNKNOWN']:
                    bad=copy.deepcopy(obj);bad[key][0][field]=val
                    yield op,[bad,*suffix]
        cases=[json.loads(x) for x in (baseline/'eval/seed-cases.jsonl').read_text().splitlines() if x.strip()]
        yield 'validate_cases',[cases,rule_ids]
        for field in cases[0]:
            for val in [None,[],{},'',17,'UNKNOWN']:
                bad=copy.deepcopy(cases);bad[0][field]=val
                yield 'validate_cases',[bad,rule_ids]
        for text in ['```md\n[bad](missing.md)\n```','> ~~~\n[bad](missing.md)\n> ~~~','`x`\n[bad](missing.md)','~~~\r\na\r\n~~~\r\nb']:
            yield 'without_fences',[text]
        skill=(baseline/'SKILL.md').read_text();cff=(baseline/'CITATION.cff').read_text();version=load('rules/rules.json')['version']
        for a,b,v in [(skill,cff,version),(skill,cff,'99'),('',cff,version),(skill.replace('author: dotoridot','author: other'),cff,version)]:
            yield 'selected_metadata_errors',[a,b,v]
        for val in [None,[],{},'', ' ', '\x1c', '\u00a0', '한글', 7, True]: yield 'nonempty',[val]


def verify_baseline(path):
    manifest=json.loads((Path(__file__).with_name('python-baseline-manifest.json')).read_text())
    mismatches=[name for name,digest in manifest.items() if not (path/name).is_file() or hashlib.sha256((path/name).read_bytes()).hexdigest()!=digest]
    if mismatches:raise ValueError('baseline integrity mismatch: '+', '.join(mismatches))
    return hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',required=True,type=Path);p.add_argument('--binary',type=Path);p.add_argument('--capture',type=Path);p.add_argument('--section',choices=['all','lint','render','package'],default='all');a=p.parse_args()
    provenance=verify_baseline(a.baseline)
    oracle=subprocess.Popen([sys.executable,'-u','-c',ORACLE,str(a.baseline.resolve())],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    rows=[];failures=[];deltas=[]
    def compare(op,args):
        item={'op':op,'args':args};oracle.stdin.write(json.dumps(item)+'\n');oracle.stdin.flush()
        expected=json.loads(oracle.stdout.readline());row={**item,'expected':expected};rows.append(row)
        if a.binary:
            run=subprocess.run([str(a.binary.resolve()),'bridge',op,'--root',str(ROOT)],input=json.dumps(args),text=True,capture_output=True)
            if 'error' in expected:
                if op=='validate_cases' and expected.get('error_type')=='TypeError' and any("unhashable type: '"+kind+"'" in expected['error'] for kind in ('list','dict')) and run.returncode==0 and json.loads(run.stdout)==['cases[1]: invalid expected_review']:
                    deltas.append({**row,'native_diagnostic':json.loads(run.stdout),'reason':'Malformed labels are now rejected with a validation diagnostic instead of a Python container exception.'})
                elif run.returncode!=2 or run.stdout or (expected.get('error_type')=='ValueError' and run.stderr.strip()!='ERROR: '+expected['error']):
                    failures.append({**row,'actual':{'code':run.returncode,'out':run.stdout,'err':run.stderr}})
            elif run.returncode or json.loads(run.stdout)!=expected['ok']:
                failures.append({**row,'actual':{'code':run.returncode,'out':run.stdout,'err':run.stderr}})
    try:
        for op,args in inputs(a.baseline,a.section): compare(op,args)
        if a.section in ('all','package'):
            with tempfile.TemporaryDirectory(prefix='stk-parity-') as tmp:
                base=Path(tmp)/'package';shutil.copytree(a.baseline,base,ignore=shutil.ignore_patterns('.git','__pycache__','target','bin'))
                compare('validate',[str(base)])
                for filename,content in [('docs/parity.md','[bad](missing.md)'),('references/external.json','{}')]:
                    path=base/filename;path.write_text(content);compare('validate',[str(base)]);path.unlink()
                original=(base/'rules/rules.json').read_bytes();(base/'rules/rules.json').unlink();compare('validate',[str(base)]);(base/'rules/rules.json').write_bytes(original)
                for target in ('README.md','../outside.md'):
                    if target.startswith('..'): (base.parent/'outside.md').write_text('outside')
                    link=base/'symlink.md';link.symlink_to(target);compare('validate',[str(base)]);link.unlink()
                for text in ['[ok](README.md#title)','[bad](../outside.md)','[bad](%2e%2e/outside.md)','[bad](missing.md)','[external](https://example.invalid/)','[bad](dir/../missing.md)']:
                    compare('local_link_errors',[str(base),str(base/'doc.md'),text])
    finally:
        oracle.stdin.close();oracle.wait()
    summary={'baseline_sha':BASELINE,'section':a.section,'comparisons':len(rows),'failures':len(failures),'intentional_deltas':len(deltas),'baseline_manifest_sha256':provenance,'python':sys.version,'binary_sha256':hashlib.sha256(a.binary.read_bytes()).hexdigest() if a.binary else None}
    if a.capture:a.capture.write_text(json.dumps({'summary':summary,'cases':rows,'failures':failures,'intentional_deltas':deltas},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))
    for index,f in enumerate(failures): print(json.dumps({'failure_index':index,'op':f['op'],'expected':f['expected'],'actual':f['actual']},ensure_ascii=False))
    return bool(failures)

if __name__=='__main__':sys.exit(main())
