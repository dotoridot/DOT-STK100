"""Preferred-expression hints and structure; not a semantic quality benchmark."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import validate_package as package
from scripts.lint_text import review


class ExpressionTests(unittest.TestCase):
    def dictionary(self):
        return json.loads((ROOT/'references/preferred-expressions.json').read_text())

    def rule_ids(self):
        return {r['id'] for r in json.loads((ROOT/'rules/rules.json').read_text())['rules']}

    def test_dictionary_contract(self):
        data = self.dictionary()
        self.assertEqual(package.validate_expressions(data, self.rule_ids()), [])
        self.assertEqual(len(data['entries']), 8)

    def test_missing_context_and_invalid_examples_rejected(self):
        for key in ['meaning', 'signals', 'preferred', 'conditions', 'exceptions', 'rule_ids', 'examples']:
            with self.subTest(key=key):
                data = self.dictionary()
                data['entries'][0].pop(key)
                self.assertTrue(package.validate_expressions(data, self.rule_ids()))
        data = self.dictionary()
        data['entries'][0]['examples'][0]['label_status'] = 'human_validated'
        self.assertTrue(package.validate_expressions(data, self.rule_ids()))

    def test_duplicate_signal_unknown_rule_and_bad_types_rejected(self):
        for mutate in [lambda d: d['entries'][1].update(signals=d['entries'][0]['signals']),
                       lambda d: d['entries'][0].update(rule_ids=['YSK-K99']),
                       lambda d: d['entries'][0].update(signals=[{}]),
                       lambda d: d['entries'][0].update(replacement='automatic')]:
            data = self.dictionary()
            mutate(data)
            self.assertTrue(package.validate_expressions(data, self.rule_ids()))
        for data in [None, {'entries': None}, {'entries': [None]}]:
            self.assertTrue(package.validate_expressions(data, self.rule_ids()))

    def test_preferred_phrase_is_only_a_review_hint(self):
        text = '시스템의 초기화를 수행합니다.'
        result = review(None, text)
        hints = [f for f in result['findings'] if 'EXPR-01' in f['message']]
        self.assertTrue(hints)
        for finding in hints:
            self.assertEqual(finding['check'], 'terminology')
            self.assertEqual(finding['rule_id'], 'YSK-K07')
            self.assertEqual(finding['certainty'], 'candidate')
            self.assertEqual(finding['severity'], 'WARN')
            span = finding['candidate_span']
            self.assertEqual(text[span['start']:span['end']], span['quote'])
            self.assertIsNone(finding['source_span'])
        self.assertEqual(result['schema_version'], '0.2')
        self.assertIn('expressions', result['config_hashes'])
        self.assertNotIn('verdict', result)

    def test_direct_prose_and_protected_names_do_not_trigger_hints(self):
        for text in ['시스템을 초기화합니다.', '`초기화를 수행합니다`',
                     'UI는 "점검을 실시합니다"입니다.', '> 확인을 진행합니다.\n',
                     '재초기화를 수행합니다.']:
            with self.subTest(text=text):
                self.assertFalse([f for f in review(None, text)['findings'] if 'EXPR-' in f['message']])

    def test_negation_and_ambiguous_modality_are_not_rewritten(self):
        for text in ['초기화를 수행하지 않습니다.', '기능의 이용이 가능합니다.', '설정을 변경할 필요가 있습니다.']:
            with self.subTest(text=text):
                hints = [f for f in review(None, text)['findings'] if 'EXPR-' in f['message']]
                self.assertTrue(hints)
                self.assertTrue(all(f['certainty'] == 'candidate' for f in hints))
                self.assertNotIn('replacement', hints[0])

    def test_evaluation_records_expression_configuration(self):
        from scripts.evaluate_linter import evaluate
        import hashlib
        report = evaluate([{'case_id':'EXAMPLE', 'pair_id':'EXAMPLE',
                            'source':'초기화를 수행합니다.', 'candidate':'초기화를 수행합니다.',
                            'expected_review':'compatible'}])
        expected = hashlib.sha256((ROOT/'references/preferred-expressions.json').read_bytes()).hexdigest()
        self.assertEqual(report['config_hashes']['expressions'], expected)
        self.assertFalse(report['human_validated'])

    def test_cli_preserves_source_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'candidate.md'
            path.write_bytes('초기화를 수행하지 않습니다.\r\n'.encode())
            original = path.read_bytes()
            run = subprocess.run([sys.executable, str(ROOT/'scripts/lint_text.py'),
                                  '--candidate', str(path)],capture_output=True,text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(any('EXPR-01' in f['message'] for f in result['findings']))
            self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
