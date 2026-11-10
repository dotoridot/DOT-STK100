"""Public native/compatibility regressions found during independent review."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def copy_package(destination):
    return shutil.copytree(ROOT,destination,ignore=lambda directory,names:[name for name in names if name in ('.git','__pycache__') or (Path(directory)==ROOT and name in ('target','bin'))])
sys.path.insert(0,str(ROOT))
from scripts._native import executable
from scripts.lint_text import review
from scripts.validate_package import local_link_errors,validate


class NativeRegressionTests(unittest.TestCase):
    def run_cli(self,*args,root=ROOT):
        return subprocess.run([executable(),*args,'--root',str(root)],text=True,capture_output=True)

    def test_invalid_source_is_rejected_instead_of_skipping_comparison(self):
        for source in [42,[],{},False]:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):review(source,'3회')

    def test_argparse_equals_options_remain_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.txt';candidate.write_text('3회')
            run=self.run_cli('lint','--candidate='+str(candidate),'--format=json')
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(run.stdout)['checks_run'],['subject','terminology'])
        self.assertEqual(self.run_cli('render','--root='+str(ROOT),'--check').returncode,0)
        self.assertEqual(self.run_cli('validate','--root='+str(ROOT)).returncode,0)

    def test_urlsplit_empty_authority_and_invalid_bracket(self):
        self.assertEqual(local_link_errors(ROOT,ROOT/'README.md','[empty](//?q)'),[])
        with self.assertRaisesRegex(ValueError,'Invalid IPv6 URL'):
            local_link_errors(ROOT,ROOT/'README.md','[bad](http://[)')

    def test_urlsplit_brackets_and_normalization(self):
        for target in ['http://[127.0.0.1]','http://[v1]','http://[::1]suffix','http://ｅｘａｍｐｌｅ.com／x']:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):local_link_errors(ROOT,ROOT/'README.md',f'[bad]({target})')
        for target in ['https://example.invalid/','http://[::1]/','http://[v1.example]/']:
            self.assertEqual(local_link_errors(ROOT,ROOT/'README.md',f'[ok]({target})'),[])

    def test_nested_build_directory_names_are_still_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package';copy_package(root)
            for name in ['target','bin']:
                directory=root/'docs'/name;directory.mkdir()
                (directory/'broken.md').write_text('[broken](missing-file.md)')
                errors,_=validate(root)
                self.assertTrue(any('broken local file link' in error for error in errors),errors)
                (directory/'broken.md').unlink()
            for name in ['target','bin']:
                directory=root/name;directory.mkdir()
                (directory/'ignored.json').write_text('{invalid build output')
            self.assertEqual(validate(root)[0],[])

    def test_native_adapter_is_required_in_native_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package';copy_package(root)
            (root/'scripts/_native.py').unlink()
            errors,_=validate(root)
            self.assertIn('missing or out-of-root required file: scripts/_native.py',errors)

    def test_evaluation_identifies_the_executed_binary(self):
        run=self.run_cli('evaluate');self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['implementation_sha256'],hashlib.sha256(Path(executable()).read_bytes()).hexdigest())
        self.assertEqual(result['implementation_kind'],'rust_executable_sha256')
        self.assertEqual(result['evaluation_schema_version'],'0.2')
        self.assertIsNone(result['human_precision']);self.assertIsNone(result['human_recall'])

    def test_missing_native_never_builds_or_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package';copy_package(root)
            candidate=root/'candidate.txt';candidate.write_text('3회')
            env=os.environ.copy();env.pop('DOT_STK100_BIN',None)
            run=subprocess.run([sys.executable,str(root/'scripts/lint_text.py'),'--candidate',str(candidate)],capture_output=True,text=True,env=env)
            self.assertEqual(run.returncode,2)
            self.assertIn('Native executable missing',run.stderr)
            self.assertFalse((root/'target').exists());self.assertFalse((root/'bin').exists())


if __name__=='__main__':unittest.main()
