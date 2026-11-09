"""Consumer and package-contract tests; not evidence of semantic effectiveness."""
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


class TerminologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terms = json.loads((ROOT / 'references/terminology.json').read_text())
        cls.rule_ids = {r['id'] for r in json.loads((ROOT / 'rules/rules.json').read_text())['rules']}

    def test_dictionary_contract(self):
        self.assertEqual(package.validate_terminology(self.terms, self.rule_ids), [])

    def test_missing_definition_example_or_exception_is_rejected(self):
        for field in ['meaning_a', 'meaning_b', 'rule_ids', 'examples', 'exceptions']:
            with self.subTest(field=field):
                data = copy.deepcopy(self.terms)
                data['entries'][0].pop(field, None)
                self.assertTrue(package.validate_terminology(data, self.rule_ids))

    def test_unknown_rule_duplicate_id_and_auto_replacement_rejected(self):
        mutations = [lambda d: d['entries'][0].update(rule_ids=['YSK-K99']),
                     lambda d: d['entries'].append(copy.deepcopy(d['entries'][0])),
                     lambda d: d['entries'][0].update(replacement='automatic')]
        for mutate in mutations:
            data = copy.deepcopy(self.terms)
            mutate(data)
            self.assertTrue(package.validate_terminology(data, self.rule_ids))

    def test_example_labels_and_evidence_boundary_required(self):
        for key, value in [('expected_review', 'guaranteed'), ('source', ''),
                           ('label_status', 'human_validated'), ('split', 'holdout')]:
            with self.subTest(key=key):
                data = copy.deepcopy(self.terms)
                data['entries'][0]['examples'][0][key] = value
                self.assertTrue(package.validate_terminology(data, self.rule_ids))

    def test_bad_container_and_nonstring_rule_fail_cleanly(self):
        for data in [None, {'entries': None}, {'entries': [None]}]:
            self.assertTrue(package.validate_terminology(data, self.rule_ids))
        data = copy.deepcopy(self.terms)
        data['entries'][0]['rule_ids'] = [{}]
        self.assertTrue(package.validate_terminology(data, self.rule_ids))

    def test_critical_changes_have_traceable_candidate_warnings(self):
        cases = [('TERM-01', '변경을 탐지합니다.', '변경을 차단합니다.'),
                 ('TERM-02', '검사는 미수행 상태입니다.', '검사는 실패 상태입니다.'),
                 ('TERM-13', '제품이 지원됩니다.', '제품이 호환됩니다.'),
                 ('TERM-14', '호환 여부를 검토합니다.', '동작 확인 여부를 검토합니다.'),
                 ('TERM-15', '온도 30 이상입니다.', '온도 30 초과입니다.'),
                 ('TERM-16', '백업은 권장입니다.', '백업은 필수입니다.')]
        for term_id, source, candidate in cases:
            with self.subTest(term_id=term_id):
                warnings = [f for f in review(source, candidate)['findings']
                            if f['check'] == 'terminology' and term_id in f['message']]
                self.assertTrue(warnings)
                for finding in warnings:
                    self.assertEqual(finding['certainty'], 'candidate')
                    self.assertEqual(finding['severity'], 'WARN')
                    self.assertEqual(finding['rule_id'], 'YSK-K05')
                    for text, key in [(source, 'source_span'), (candidate, 'candidate_span')]:
                        span = finding[key]
                        self.assertEqual(text[span['start']:span['end']], span['quote'])

    def test_unchanged_and_protected_terms_are_not_replacement_warnings(self):
        for source, candidate in [('지원과 호환은 별도입니다.', '지원과 호환은 별도입니다.'),
                                  ('`지원`', '`호환`'),
                                  ('> 백업은 권장입니다.\n', '> 백업은 필수입니다.\n')]:
            with self.subTest(source=source):
                self.assertFalse([f for f in review(source, candidate)['findings'] if f['check'] == 'terminology'])

    def test_dictionary_examples_run_as_development_triage(self):
        run = subprocess.run([sys.executable, str(ROOT/'scripts/evaluate_linter.py'),
                              '--terminology-examples'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(report['case_count'], 48)
        self.assertEqual(report['source_family_count'], 16)
        self.assertEqual(report['excluded_needs_context'], 16)
        self.assertFalse(report['human_validated'])
        self.assertIsNone(report['human_precision'])
        self.assertIsNone(report['human_recall'])

    def test_cli_critical_term_warning_does_not_modify_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, candidate = Path(tmp)/'source.md', Path(tmp)/'candidate.md'
            source.write_text('백업은 권장입니다.')
            candidate.write_text('백업은 필수입니다.')
            before = [p.read_bytes() for p in (source, candidate)]
            run = subprocess.run([sys.executable, str(ROOT/'scripts/lint_text.py'),
                                  '--source', str(source), '--candidate', str(candidate)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(any('TERM-16' in f['message'] for f in result['findings']))
            self.assertNotIn('verdict', result)
            self.assertEqual(before, [p.read_bytes() for p in (source, candidate)])


if __name__ == '__main__':
    unittest.main()
