#!/usr/bin/env python3
"""Compatibility API for native structure checks, not semantic validation."""
from pathlib import Path
import re
try:
    from ._native import call, main as native_main
except ImportError:
    from _native import call, main as native_main

RULE_ID = re.compile(r"^YSK-[MKEPQ]\d{2}$")
LABELS = {'compatible', 'meaning_changed', 'needs_context'}
REQUIRED = (
    "references/preferred-expressions.json", "references/EXPRESSIONS.md",
    "README.md", "SKILL.md", "AGENTS.md", "AUTHORS.md", "CITATION.cff", "LICENSE.md",
    "NOTICE.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSES/MIT.txt",
    "rules/rules.json", "references/DOT-STK100-SPEC.md", "references/RESEARCH.md",
    "references/sources.json", "references/terminology.json", "docs/AGENT-HANDOFF.md",
    "docs/DESIGN-DECISIONS.md", "docs/IMPLEMENTATION-PLAN.md", "docs/EVALUATION.md",
    "docs/INTEGRATION.md", "docs/MIGRATION.md", "docs/RELEASE-CHECKLIST.md",
    "eval/seed-cases.jsonl", "eval/DATA-CARD.md", "eval/annotation-template.json",
    "eval/review-output.schema.json", "examples/BEFORE-AFTER.md",
    "scripts/render_rules.py", "scripts/validate_package.py", "tests/test_package.py",
    "reports/VALIDATION.md", ".github/pull_request_template.md", ".gitignore",
    "scripts/lint_text.py", "scripts/evaluate_linter.py", "docs/LINTER.md",
    "references/lint-terms.json", "references/profiles/lite.md",
    "references/profiles/core.md", "references/profiles/audit.md",
    "tests/test_linter.py", "tests/test_evaluation.py", "eval/lint-output.schema.json",
    "docs/HOST-COMPATIBILITY.md", "reports/AUDIT.md",
)

def nonempty(value):
    return call('nonempty', value)


def validate_sources(data):
    return call('validate_sources', data)


def validate_rules(data, source_ids):
    return call('validate_rules', data, sorted(source_ids))


def validate_cases(cases, rule_ids):
    return call('validate_cases', cases, sorted(rule_ids))


def validate_examples(examples, loc):
    return call('validate_examples', examples, loc)


def validate_terminology(data, rule_ids):
    return call('validate_terminology', data, sorted(rule_ids))


def validate_expressions(data, rule_ids):
    return call('validate_expressions', data, sorted(rule_ids))


def without_fences(text):
    return call('without_fences', text)


def local_link_errors(root, document, text):
    return call('local_link_errors', str(root), str(document), text)


def selected_metadata_errors(skill, cff, version):
    return call('selected_metadata_errors', skill, cff, version)


def validate(root):
    return tuple(call('validate', str(root)))


def main(argv=None):
    return native_main('validate', argv)


if __name__ == '__main__':
    raise SystemExit(main())
