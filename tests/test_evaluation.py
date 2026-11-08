import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_linter import evaluate


class EvaluationTests(unittest.TestCase):
    def test_provisional_matrix_and_abstentions(self):
        def case(cid, source, candidate, label):
            return dict(case_id=cid, pair_id=cid, source=source, candidate=candidate, expected_review=label)
        result = evaluate([
            case('tp', '3회', '5회', 'meaning_changed'),
            case('fp', '앱 3회, 서버 3회', '앱과 서버는 각각 3회', 'compatible'),
            case('tn', '캐시를 읽습니다.', '캐시를 읽습니다.', 'compatible'),
            case('fn', '앱은 3회, 서버는 5회', '서버는 3회, 앱은 5회', 'meaning_changed'),
            case('unknown', '해당 프로세스', '해당 프로세스', 'needs_context'),
        ])
        self.assertEqual(result['confusion_matrix_provisional'], dict(tp=1, fp=1, tn=1, fn=1))
        self.assertEqual(result['excluded_needs_context'], 1)
        self.assertFalse(result['human_validated'])
        self.assertIsNone(result['human_precision'])
        self.assertEqual(result['provisional_precision'], 0.5)

    def test_zero_denominators_are_unknown(self):
        result = evaluate([])
        self.assertIsNone(result['provisional_precision'])
        self.assertIsNone(result['provisional_recall'])


if __name__ == '__main__':
    unittest.main()
