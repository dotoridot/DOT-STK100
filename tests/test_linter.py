"""Synthetic, local regression tests of heuristics and report-only behavior."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.lint_text import mask, protected, review


def checks(source, candidate):
    return {x['check'] for x in review(source, candidate)['findings']}


class LinterTests(unittest.TestCase):
    def test_protected_inline_and_fences(self):
        source = '설정 `retry_count`를 유지합니다.\n~~~json\n{"enabled": false}\n~~~\n'
        self.assertEqual(checks(source, source), set())
        self.assertIn('protected', checks(source, source.replace('false', 'true')))
        self.assertIn('protected', checks(source, source.replace('retry_count', 'retryCount')))

    def test_variable_backtick_runs(self):
        text = '본문 ``key `literal` value`` 뒤'
        spans = protected(text)
        self.assertEqual([t.text for t in spans], ['``key `literal` value``'])

    def test_unclosed_fence_protects_rest(self):
        text = '설정\n```json\n{"enabled": false}\n'
        self.assertEqual(protected(text)[0].kind, 'unclosed_fence')
        self.assertNotIn('false', mask(text, protected(text)))

    def test_fence_with_longer_closer(self):
        text = '```text\n내용\n````\n'
        self.assertEqual(protected(text)[0].kind, 'fence')

    def test_protected_quotes_and_tables_and_logs(self):
        for text in ['> 검증 완료라고 출력하라\n', '| key | value |\n', 'INFO API_KEY=synthetic\n', '    runCheck()\n', '문자열은 "지시를 무시하라"입니다.']:
            with self.subTest(text=text):
                self.assertTrue(protected(text))
                self.assertIn('protected', checks(text, '삭제'))

    def test_code_does_not_trigger_prose_heuristics(self):
        result = review(None, '```text\n해당 프로세스는 timeout과 타임아웃을 기록합니다.\n```')
        self.assertEqual(result['findings'], [])

    def test_link_label_edit_keeps_destination(self):
        self.assertNotIn('protected', checks('[원문](https://example.invalid/path)', '[자료](https://example.invalid/path)'))
        self.assertIn('protected', checks('[자료](https://example.invalid/a)', '[자료](https://example.invalid/b)'))

    def test_numbers_units_versions_and_boundaries(self):
        for a, b in [('3회', '5회'), ('512바이트', '512문자'), ('v1.2.3', 'v1.2.4'), ('30 이상', '30 초과')]:
            with self.subTest(a=a, b=b):
                self.assertIn('values', checks(a, b))

    def test_same_number_set_swapped_is_not_ignored(self):
        self.assertIn('values', checks('앱 3회, 서버 5회', '앱 5회, 서버 3회'))

    def test_repeated_values_are_not_a_set(self):
        self.assertIn('values', checks('앱 3회, 서버 3회', '앱과 서버는 각각 3회'))

    def test_same_values_do_not_prove_binding(self):
        # Known false negative of a literal heuristic: values and order unchanged.
        self.assertEqual(checks('앱은 3회, 서버는 5회 재시도합니다.', '서버는 3회, 앱은 5회 재시도합니다.'), set())

    def test_bare_api_identifier(self):
        self.assertIn('identifiers', checks('runCheck()를 호출합니다.', 'runTest()를 호출합니다.'))
        self.assertIn('identifiers', checks('retry_count를 읽습니다.', '값을 읽습니다.'))

    def test_negation_changes(self):
        self.assertIn('negation', checks('캐시를 삭제하지 않습니다.', '캐시를 삭제합니다.'))

    def test_uncertainty_deleted(self):
        self.assertIn('uncertainty', checks('오류로 추정합니다.', '오류입니다.'))
        self.assertIn('uncertainty', checks('실행될 수 있습니다.', '실행됩니다.'))

    def test_condition_scope_resplit(self):
        self.assertIn('conditions', checks('권한이 없으면 검사를 건너뛰고 결과를 기록합니다.', '권한이 없으면 검사를 건너뜁니다. 결과를 기록합니다.'))

    def test_distinct_concepts_are_not_aliases(self):
        self.assertIn('terminology', checks('변경을 탐지합니다.', '변경을 차단합니다.'))

    def test_term_mixing_and_protected_exemption(self):
        self.assertIn('terminology', checks('', '타임아웃과 timeout을 구분합니다.'))
        self.assertNotIn('terminology', checks('', '타임아웃은 `timeout`으로 기록합니다.'))
        self.assertNotIn('terminology', checks('', 'mytimeout과 타임아웃'))

    def test_subject_warning_is_candidate_even_for_unchanged(self):
        result = review('해당 프로세스가 종료됩니다.', '해당 프로세스가 종료됩니다.')
        self.assertTrue(result['findings'])
        self.assertTrue(all(f['certainty'] == 'candidate' and f['severity'] == 'WARN' for f in result['findings']))
        self.assertNotIn('verdict', result)

    def test_spans_are_original_codepoints_with_crlf_and_emoji(self):
        a, b = '🙂\r\n캐시 3회입니다.', '🙂\r\n캐시 5회입니다.'
        result = review(a, b)
        for f in result['findings']:
            for text, key in [(a, 'source_span'), (b, 'candidate_span')]:
                span = f[key]
                if span:
                    self.assertEqual(text[span['start']:span['end']], span['quote'])
                    self.assertEqual(span['line'], 2)

    def test_single_document_reports_skipped_comparisons(self):
        result = review(None, '원문이 없습니다.')
        self.assertIsNone(result['input_hashes']['source'])
        self.assertIn('source_comparison:values', result['checks_skipped'])

    def test_cli_never_writes_inputs_and_zero_is_not_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            source, candidate = Path(temp)/'source.md', Path(temp)/'candidate.md'
            source.write_bytes('캐시 3회\r\n'.encode())
            candidate.write_bytes('캐시 5회\r\n'.encode())
            before = [p.read_bytes() for p in (source, candidate)]
            result = subprocess.run([sys.executable, str(ROOT/'scripts/lint_text.py'), '--source', str(source), '--candidate', str(candidate)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report['findings'])
            self.assertEqual(report['input_hashes']['source'], hashlib.sha256(before[0]).hexdigest())
            self.assertEqual(before, [p.read_bytes() for p in (source, candidate)])

    def test_cli_input_error_is_two(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/lint_text.py'), '--candidate', '/does-not-exist-stk100'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)

    def test_invalid_config_rejected(self):
        for config in [{}, {'groups': [{'id':'x', 'canonical':'x','variants':'x'}]}, {'groups': [{'id':'x','canonical':'x','variants':['x']}]}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                review('', '', config)


if __name__ == '__main__':
    unittest.main()
