"""Structural regression tests. None of these tests prove semantic preservation."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.render_rules import END, START, render_document, render_table
from scripts.validate_package import (
    local_link_errors, selected_metadata_errors, validate, validate_cases,
    validate_rules, validate_sources,
)


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = json.loads((ROOT / "rules/rules.json").read_text(encoding="utf-8"))
        cls.sources = json.loads((ROOT / "references/sources.json").read_text(encoding="utf-8"))
        cls.cases = [json.loads(line) for line in (ROOT / "eval/seed-cases.jsonl").read_text(encoding="utf-8").splitlines()]
        cls.rule_ids = {r["id"] for r in cls.rules["rules"]}
        cls.source_ids = {s["id"] for s in cls.sources["sources"]}

    def test_valid_package(self) -> None:
        errors, counts = validate(ROOT)
        self.assertEqual(errors, [])
        self.assertGreater(counts["rules"], 0)
        self.assertEqual(counts["seed_cases"], len(self.cases))

    def test_render_is_idempotent(self) -> None:
        original = f"prefix\n{START}\nold table\n{END}\nsuffix"
        once = render_document(original, self.rules["rules"])
        self.assertEqual(once, render_document(once, self.rules["rules"]))
        self.assertTrue(once.startswith("prefix\n"))
        self.assertTrue(once.endswith("\nsuffix"))

    def test_render_escapes_table_delimiters(self) -> None:
        rule = copy.deepcopy(self.rules["rules"][0])
        rule["requirement"] = "A | B\nC"
        self.assertIn("A &#124; B<br>C", render_table([rule]))

    def test_render_rejects_missing_marker(self) -> None:
        with self.assertRaises(ValueError):
            render_document("no markers", self.rules["rules"])

    def test_render_rejects_duplicate_marker(self) -> None:
        with self.assertRaises(ValueError):
            render_document(START + START + END, self.rules["rules"])

    def test_render_rejects_reversed_markers(self) -> None:
        with self.assertRaises(ValueError):
            render_document(END + START, self.rules["rules"])

    def test_duplicate_rule_is_rejected(self) -> None:
        data = copy.deepcopy(self.rules)
        data["rules"].append(copy.deepcopy(data["rules"][0]))
        self.assertTrue(any("duplicate rule" in x for x in validate_rules(data, self.source_ids)))

    def test_unknown_rule_source_is_rejected(self) -> None:
        data = copy.deepcopy(self.rules)
        data["rules"][0]["sources"] = ["UNLISTED"]
        self.assertTrue(any("unknown source" in x for x in validate_rules(data, self.source_ids)))

    def test_invalid_rule_level_is_rejected(self) -> None:
        data = copy.deepcopy(self.rules)
        data["rules"][0]["level"] = "GUARANTEED"
        self.assertTrue(any("invalid rule level" in x for x in validate_rules(data, self.source_ids)))

    def test_missing_rule_requirement_is_rejected(self) -> None:
        data = copy.deepcopy(self.rules)
        del data["rules"][0]["requirement"]
        self.assertTrue(any("missing requirement" in x for x in validate_rules(data, self.source_ids)))

    def test_duplicate_source_is_rejected(self) -> None:
        data = copy.deepcopy(self.sources)
        data["sources"].append(copy.deepcopy(data["sources"][0]))
        self.assertTrue(any("duplicate source" in x for x in validate_sources(data)))

    def test_missing_source_scope_is_rejected(self) -> None:
        data = copy.deepcopy(self.sources)
        del data["sources"][0]["reviewed_scope"]
        self.assertTrue(any("missing reviewed_scope" in x for x in validate_sources(data)))

    def test_duplicate_case_is_rejected(self) -> None:
        cases = copy.deepcopy(self.cases)
        cases.append(copy.deepcopy(cases[0]))
        self.assertTrue(any("duplicate case" in x for x in validate_cases(cases, self.rule_ids)))

    def test_unknown_case_label_is_rejected(self) -> None:
        cases = copy.deepcopy(self.cases)
        cases[0]["expected_review"] = "100_percent_correct"
        self.assertTrue(any("invalid expected_review" in x for x in validate_cases(cases, self.rule_ids)))

    def test_unknown_case_rule_is_rejected(self) -> None:
        cases = copy.deepcopy(self.cases)
        cases[0]["rule_ids"] = ["YSK-M99"]
        self.assertTrue(any("unknown rule" in x for x in validate_cases(cases, self.rule_ids)))

    def test_seed_cannot_become_holdout_silently(self) -> None:
        cases = copy.deepcopy(self.cases)
        cases[0]["split"] = "holdout"
        self.assertTrue(any("seed split" in x for x in validate_cases(cases, self.rule_ids)))

    def test_seed_cannot_claim_human_validation_silently(self) -> None:
        cases = copy.deepcopy(self.cases)
        cases[0]["label_status"] = "human_validated"
        self.assertTrue(any("seed label_status" in x for x in validate_cases(cases, self.rule_ids)))

    def test_local_links_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("target", encoding="utf-8")
            text = "[ok](target.md#heading) [external](https://example.invalid/) [anchor](#title)"
            self.assertEqual(local_link_errors(root, root / "doc.md", text), [])

    def test_broken_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            errors = local_link_errors(root, root / "doc.md", "[bad](missing.md)")
            self.assertTrue(any("broken local file link" in x for x in errors))

    def test_link_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            errors = local_link_errors(root, root / "doc.md", "[escape](../outside.md)")
            self.assertTrue(any("escapes package" in x for x in errors))

    def test_links_inside_fences_are_not_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = "```md\n[example](missing.md)\n```\n"
            self.assertEqual(local_link_errors(root, root / "doc.md", text), [])

    def test_metadata_version_mismatch_is_rejected(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        errors = selected_metadata_errors(skill, cff, "99.0.0")
        self.assertTrue(any("SKILL.md" in x and "mismatch" in x for x in errors))
        self.assertTrue(any("CITATION.cff" in x and "mismatch" in x for x in errors))

    def test_metadata_requires_description(self) -> None:
        skill = '---\nname: yupk-stk100\nmetadata:\n  version: "0.2"\n---\n'
        errors = selected_metadata_errors(skill, 'version: "0.2"\n', "0.2")
        self.assertTrue(any("description" in x for x in errors))

    def test_missing_package_fails_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors, counts = validate(Path(tmp))
            self.assertTrue(errors)
            self.assertEqual(counts, {})


if __name__ == "__main__":
    unittest.main()
