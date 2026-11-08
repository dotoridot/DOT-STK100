#!/usr/bin/env python3
"""Render the rule table from JSON. This does not evaluate Korean prose."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

START = "<!-- BEGIN GENERATED RULES -->"
END = "<!-- END GENERATED RULES -->"


def cell(value: str) -> str:
    """Escape the small, documented subset used in table cells."""
    return value.replace("|", "&#124;").replace("\r\n", "\n").replace("\n", "<br>")


def render_table(rules: list[dict[str, object]]) -> str:
    rows = ["| ID | 강도 | 영역·제목 | 요구 사항 |",
            "|---|---|---|---|"]
    for rule in rules:
        keys = ("id", "level", "section", "title", "requirement")
        if not isinstance(rule, dict) or any(not isinstance(rule.get(k), str) for k in keys):
            raise ValueError("Rule table fields must be strings")
        values = (rule["id"], rule["level"], f'{rule["section"]} — {rule["title"]}', rule["requirement"])
        rows.append("| " + " | ".join(cell(str(v)) for v in values) + " |")
    return "\n".join(rows)


def render_document(text: str, rules: list[dict[str, object]]) -> str:
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("Document must contain exactly one start/end marker pair")
    start = text.index(START) + len(START)
    end = text.index(END)
    if start > end:
        raise ValueError("Generated table markers are out of order")
    return text[:start] + "\n\n" + render_table(rules) + "\n\n" + text[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Check without writing files")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        data = json.loads((root / "rules/rules.json").read_text(encoding="utf-8"))
        rules = data["rules"]
        if not isinstance(rules, list) or not rules:
            raise ValueError("rules must be a nonempty list")
        path = root / "references/YUPK-STK100-SPEC.md"
        original = path.read_text(encoding="utf-8")
        rendered = render_document(original, rules)
        if args.check:
            if rendered != original:
                print("FAIL: generated rule table is stale; run scripts/render_rules.py", file=sys.stderr)
                return 1
            print(f"PASS: generated rule table matches {len(rules)} rules (structure only)")
        else:
            path.write_text(rendered, encoding="utf-8")
            print(f"Rendered {len(rules)} rules")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
