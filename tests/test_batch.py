"""End-to-end batch contracts; only synthetic public fixture inputs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts._native import executable
from scripts.lint_text import review,review_many

class BatchTests(unittest.TestCase):
    def cases(self):
        return [json.loads(line) for line in (ROOT/'eval/seed-cases.jsonl').read_text().splitlines() if line.strip()]

    def test_api_batch_matches_individual_reviews_in_order(self):
        cases=self.cases()
        expected=[review(c['source'],c['candidate']) for c in cases]
        self.assertEqual(review_many(cases),expected)

    def test_source_omitted_and_empty_batch(self):
        self.assertEqual(review_many([]),[])
        self.assertEqual(review_many([{'candidate':'해당 프로세스 3회'}]),[review(None,'해당 프로세스 3회')])
        self.assertEqual(review_many([{'source':'','candidate':'😀\r\n5회'}]),[review('','😀\r\n5회')])

    def test_jsonl_keeps_unicode_separators_inside_string_values(self):
        cases=[{'source':'😀\u0085원문\u2028끝','candidate':'😀\u0085수정\u2028끝'}]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'unicode.jsonl';path.write_text(json.dumps(cases[0],ensure_ascii=False)+'\n')
            run=subprocess.run([executable(),'lint-batch','--root',str(ROOT),'--cases',str(path)],text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout),review_many(cases))

    def test_custom_terms_hash_and_warning_are_preserved(self):
        config={'groups':[{'id':'CUSTOM','canonical':'캐시','variants':['cache']}]}
        cases=[{'source':None,'candidate':'캐시 cache'}, {'source':'캐시','candidate':'cache'}]
        self.assertEqual(review_many(cases,config),[review(c['source'],c['candidate'],config) for c in cases])

    def test_invalid_batch_has_no_partial_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cases.jsonl'
            for bad in [{'source':42,'candidate':'3회'},{'candidate':None},[]]:
                path.write_text(json.dumps({'candidate':'3회'})+'\n'+json.dumps(bad)+'\n')
                run=subprocess.run([executable(),'lint-batch','--root',str(ROOT),'--cases',str(path)],text=True,capture_output=True)
                self.assertEqual(run.returncode,2,run.stdout)
                self.assertEqual(run.stdout,'')
                self.assertTrue(run.stderr.strip())

    def test_cli_batch_matches_individual_api_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases=self.cases();path=Path(tmp)/'cases.jsonl'
            raw=('\r\n'.join(json.dumps(c,ensure_ascii=False) for c in cases)+'\r\n').encode();path.write_bytes(raw)
            run=subprocess.run([executable(),'lint-batch','--root='+str(ROOT),'--cases='+str(path)],text=True,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout),[review(c['source'],c['candidate']) for c in cases])
            self.assertEqual(path.read_bytes(),raw)

if __name__=='__main__':unittest.main()
