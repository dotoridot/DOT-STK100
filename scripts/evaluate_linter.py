#!/usr/bin/env python3
"""Development-only warning triage counts against provisional synthetic labels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    from .lint_text import ROOT, review
except ImportError:
    from lint_text import ROOT, review


def evaluate(cases: list[dict]) -> dict:
    matrix = {key: 0 for key in ("tp", "fp", "tn", "fn")}
    rows = []
    needs_context = 0
    for case in cases:
        result = review(case['source'], case['candidate'])
        warned = bool(result['findings'])
        label = case['expected_review']
        if label == 'needs_context':
            outcome = 'excluded_needs_context'
            needs_context += 1
        elif label in ('meaning_changed', 'compatible'):
            positive = label == 'meaning_changed'
            outcome = ('tp' if warned else 'fn') if positive else ('fp' if warned else 'tn')
            matrix[outcome] += 1
        else:
            raise ValueError('unknown reference label')
        rows.append({'case_id': case['case_id'], 'pair_id': case['pair_id'],
                     'provisional_label': label, 'warning_count': len(result['findings']),
                     'checks': sorted({f['check'] for f in result['findings']}), 'triage_outcome': outcome})
    ratio = lambda a, b: a / b if b else None
    return {'evaluation_kind': 'development_warning_triage_against_ai_draft_labels',
            'human_validated': False, 'unit': 'one_candidate_document_any_warning',
            'case_count': len(cases), 'source_family_count': len({c['pair_id'] for c in cases}),
            'confusion_matrix_provisional': matrix, 'excluded_needs_context': needs_context,
            'provisional_precision': ratio(matrix['tp'], matrix['tp'] + matrix['fp']),
            'provisional_recall': ratio(matrix['tp'], matrix['tp'] + matrix['fn']),
            'provisional_false_positive_rate': ratio(matrix['fp'], matrix['fp'] + matrix['tn']),
            'provisional_false_negative_rate': ratio(matrix['fn'], matrix['fn'] + matrix['tp']),
            'human_precision': None, 'human_recall': None,
            'notice': 'AI 초안 라벨 기준의 경고 발생 집계다. 경고의 타당성, 의미 판정 성능, 일반 정확도와 사람 평가가 아니다. 관련 없는 경고도 any-warning으로 센다. 같은 pair_id는 독립 표본이 아니다.',
            'cases': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=ROOT/'eval/seed-cases.jsonl')
    args = parser.parse_args(argv)
    try:
        raw = args.cases.read_bytes()
        cases = [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
        if not cases or len({c['case_id'] for c in cases}) != len(cases):
            raise ValueError('empty or duplicate cases')
        if any(c.get('label_status') != 'ai_draft_not_human_adjudicated' or c.get('split') != 'development_only' for c in cases):
            raise ValueError('this evaluator accepts only provisional development data')
        result = evaluate(cases)
        result['dataset_sha256'] = hashlib.sha256(raw).hexdigest()
        result['implementation_sha256'] = hashlib.sha256((ROOT/'scripts/lint_text.py').read_bytes()).hexdigest()
        result['spec_version'] = json.loads((ROOT/'rules/rules.json').read_text())['version']
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
