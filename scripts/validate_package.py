#!/usr/bin/env python3
"""Offline package checks; NOT a prose linter, fact checker or semantic validator.

Only the package's simple inline Markdown links and selected front-matter fields
are checked. This is not a full Markdown/YAML/CFF/schema compliance parser.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from .render_rules import render_document
except ImportError:
    from render_rules import render_document

RULE_ID = re.compile(r"^YSK-[MKEPQ]\d{2}$")
LABELS = {"compatible", "meaning_changed", "needs_context"}
REQUIRED = (
    "README.md", "SKILL.md", "AGENTS.md", "AUTHORS.md", "CITATION.cff", "LICENSE.md",
    "NOTICE.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSES/MIT.txt",
    "rules/rules.json", "references/YUPK-STK100-SPEC.md", "references/RESEARCH.md",
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


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_sources(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        return ["sources: expected an object with a sources list"]
    seen: set[str] = set()
    for index, source in enumerate(data["sources"], 1):
        loc = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{loc}: expected an object")
            continue
        sid = source.get("id")
        if not nonempty(sid):
            errors.append(f"{loc}: missing id")
        elif sid in seen:
            errors.append(f"{loc}: duplicate source id {sid}")
        else:
            seen.add(sid)
        for key in ("title", "authors", "published", "url", "reviewed_scope", "limits",
                    "verification_status", "confirmed_findings", "applicable_principles",
                    "non_applicable_principles"):
            if not nonempty(source.get(key)):
                errors.append(f"{loc}: missing {key}")
        if not source.get("accessed") and source.get("verification_status") != "inherited_not_reverified":
            errors.append(f"{loc}: missing accessed for checked source")
        if not isinstance(source.get("hypotheses"), list) or not source["hypotheses"] or any(not nonempty(x) for x in source["hypotheses"]):
            errors.append(f"{loc}: missing hypotheses")
        if isinstance(source.get("url"), str) and not source["url"].startswith("https://"):
            errors.append(f"{loc}: expected an HTTPS source URL")
    return errors


def validate_rules(data: object, source_ids: set[str]) -> list[str]:
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return ["rules: expected an object with a rules list"]
    errors: list[str] = []
    if not data["rules"]:
        errors.append("rules: list is empty")
    if not nonempty(data.get("version")):
        errors.append("rules: missing version")
    seen: set[str] = set()
    for index, rule in enumerate(data["rules"], 1):
        loc = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{loc}: expected an object")
            continue
        rid = rule.get("id")
        if not isinstance(rid, str) or not RULE_ID.fullmatch(rid):
            errors.append(f"{loc}: invalid rule id")
        elif rid in seen:
            errors.append(f"{loc}: duplicate rule id {rid}")
        else:
            seen.add(rid)
        for key in ("section", "title", "requirement", "exception", "verification", "evidence_status"):
            if not nonempty(rule.get(key)):
                errors.append(f"{loc}: missing {key}")
        if rule.get("level") not in ("MUST", "SHOULD"):
            errors.append(f"{loc}: invalid rule level")
        refs = rule.get("sources")
        if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
            errors.append(f"{loc}: sources must be a string list")
        else:
            for ref in refs:
                if ref not in source_ids:
                    errors.append(f"{loc}: unknown source {ref}")
    return errors


def validate_cases(cases: list[object], rule_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    if not cases:
        errors.append("cases: empty dataset")
    for index, case in enumerate(cases, 1):
        loc = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{loc}: expected an object")
            continue
        cid = case.get("case_id")
        if not nonempty(cid):
            errors.append(f"{loc}: missing case_id")
        elif cid in seen:
            errors.append(f"{loc}: duplicate case id {cid}")
        else:
            seen.add(cid)
        for key in ("pair_id", "source", "candidate", "topic", "note"):
            if not nonempty(case.get(key)):
                errors.append(f"{loc}: missing {key}")
        if case.get("expected_review") not in LABELS:
            errors.append(f"{loc}: invalid expected_review")
        # The public seed set must never silently become a human-validated holdout.
        for key, value in (("origin", "synthetic_original"), ("split", "development_only"),
                           ("label_status", "ai_draft_not_human_adjudicated")):
            if case.get(key) != value:
                errors.append(f"{loc}: seed {key} must remain {value}")
        refs = case.get("rule_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs):
            errors.append(f"{loc}: rule_ids must be a nonempty string list")
        else:
            for ref in refs:
                if ref not in rule_ids:
                    errors.append(f"{loc}: unknown rule {ref}")
    return errors


def without_fences(text: str) -> str:
    """Skip backtick/tilde fenced blocks, including the blockquote examples."""
    out: list[str] = []
    marker = ""
    for line in text.splitlines():
        candidate = re.sub(r"^\s*>\s?", "", line).lstrip()
        match = re.match(r"(`{3,}|~{3,})", candidate)
        if not marker and match:
            marker = match.group(1)
            continue
        if marker:
            if candidate.startswith(marker) and not candidate[len(marker):].strip():
                marker = ""
            continue
        out.append(line)
    return "\n".join(out)


def local_link_errors(root: Path, document: Path, text: str) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    for target in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", without_fences(text)):
        target = target.strip().strip("<>")
        # Link titles and reference-style links are not supported by this check.
        parts = urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        path = (document.parent / unquote(parts.path)).resolve()
        if not path.is_relative_to(root):
            errors.append(f"{document.name}: link escapes package: {target}")
        elif not path.is_file():
            errors.append(f"{document.name}: broken local file link: {target}")
    return errors


def selected_metadata_errors(skill: str, cff: str, version: str) -> list[str]:
    """Check selected known scalar fields, not all YAML or CFF syntax."""
    errors: list[str] = []
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", skill, re.S)
    if not match:
        return ["SKILL.md: missing front matter"]
    front = match.group(1)
    fields = dict(re.findall(r"^([a-z][a-z-]*):\s*(.*)$", front, re.M))
    if fields.get("name") != "yupk-stk100":
        errors.append("SKILL.md: name must be yupk-stk100")
    if not re.search(r'^  author:\s*dotoridot\s*$', front, re.M):
        errors.append("SKILL.md: author must be dotoridot")
    if not re.search(r'^  - name:\s*"dotoridot"\s*$', cff, re.M):
        errors.append("CITATION.cff: author name must be dotoridot")
    if not 1 <= len(fields.get("description", "")) <= 1024:
        errors.append("SKILL.md: description length outside 1..1024")
    if not re.search(r'^  version:\s*[\"\']?' + re.escape(version) + r'[\"\']?\s*$', front, re.M):
        errors.append("SKILL.md: metadata version mismatch")
    if not re.search(r'^version:\s*[\"\']?' + re.escape(version) + r'[\"\']?\s*$', cff, re.M):
        errors.append("CITATION.cff: version mismatch")
    return errors


def validate(root: Path) -> tuple[list[str], dict[str, int]]:
    root = root.resolve()
    errors: list[str] = []
    counts: dict[str, int] = {}
    for relative in REQUIRED:
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(f"missing or out-of-root required file: {relative}")
    if errors:
        return errors, counts
    try:
        rules = json.loads((root / "rules/rules.json").read_text(encoding="utf-8"))
        sources = json.loads((root / "references/sources.json").read_text(encoding="utf-8"))
        cases = [json.loads(line) for line in (root / "eval/seed-cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        errors.extend(validate_sources(sources))
        source_ids = {s["id"] for s in sources.get("sources", []) if isinstance(s, dict) and isinstance(s.get("id"), str)} if isinstance(sources, dict) else set()
        errors.extend(validate_rules(rules, source_ids))
        rule_ids = {r["id"] for r in rules.get("rules", []) if isinstance(r, dict) and isinstance(r.get("id"), str)} if isinstance(rules, dict) else set()
        errors.extend(validate_cases(cases, rule_ids))
        for path in root.rglob("*.json"):
            if not path.resolve().is_relative_to(root):
                errors.append(f"JSON symlink outside package: {path.name}")
                continue
            json.loads(path.read_text(encoding="utf-8"))
        for path in root.rglob("*.md"):
            if not path.resolve().is_relative_to(root):
                errors.append(f"Markdown symlink outside package: {path.name}")
                continue
            errors.extend(local_link_errors(root, path, path.read_text(encoding="utf-8")))
        if isinstance(rules, dict) and isinstance(rules.get("rules"), list):
            path = root / "references/YUPK-STK100-SPEC.md"
            text = path.read_text(encoding="utf-8")
            if render_document(text, rules["rules"]) != text:
                errors.append("generated rule table is stale")
            errors.extend(selected_metadata_errors(
                (root / "SKILL.md").read_text(encoding="utf-8"),
                (root / "CITATION.cff").read_text(encoding="utf-8"), str(rules.get("version", ""))))
        terms = json.loads((root / "references/terminology.json").read_text(encoding="utf-8"))
        if terms.get("version") != rules.get("version"):
            errors.append("terminology version mismatch")
        term_ids: set[str] = set()
        for term in terms.get("entries", []):
            if not isinstance(term, dict) or not nonempty(term.get("id")):
                errors.append("invalid terminology entry")
                continue
            if term["id"] in term_ids:
                errors.append(f"duplicate term id {term['id']}")
            term_ids.add(term["id"])
            if term.get("replacement") != "never_automatic":
                errors.append(f"term {term['id']}: automatic replacement is not allowed")
        counts = {"rules": len(rule_ids), "sources": len(source_ids), "seed_cases": len(cases),
                  "source_families": len({c["pair_id"] for c in cases if isinstance(c, dict) and isinstance(c.get("pair_id"), str)}),
                  "term_pairs": len(term_ids)}
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError) as exc:
        errors.append(f"package parse/check error: {exc}")
    return errors, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors, counts = validate(args.root)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: package structure and references")
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print("NOT CHECKED: semantic labels, facts, readability, host compatibility or real-world effectiveness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
