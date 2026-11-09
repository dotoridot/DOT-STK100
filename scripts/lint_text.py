#!/usr/bin/env python3
"""Offline, report-only risk candidates. No semantic verdict or automatic edits."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = "0.2.0"
CHECKS = ("protected", "values", "identifiers", "negation", "uncertainty",
          "conditions", "subject", "terminology")


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str
    kind: str


def tokens(pattern: str, text: str, kind: str) -> list[Token]:
    return [Token(m.start(), m.end(), m.group(), kind) for m in re.finditer(pattern, text)]


def protected(text: str) -> list[Token]:
    """Conservative Markdown subset, preserving original code-point offsets.

    Not a CommonMark parser. Tables, quotes, logs and indented code are treated
    as opaque lines. Unknown HTML/reference-link structures require review.
    """
    out: list[Token] = []
    offset = 0
    fence = None
    for line in text.splitlines(keepends=True):
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)", line)
        if fence:
            marker, start = fence
            close = re.fullmatch(r" {0,3}" + re.escape(marker[0]) +
                                 "{" + str(len(marker)) + r",}[ \t]*(?:\r?\n)?", line)
            if close:
                out.append(Token(start, offset + len(line), text[start:offset + len(line)], "fence"))
                fence = None
        elif opening:
            fence = (opening[1], offset)
        elif re.match(r"^(?: {0,3}>| {4}|\t|\s*\||\s*(?:INFO|WARN|ERROR|DEBUG)\b)", line):
            out.append(Token(offset, offset + len(line), line, "opaque_line"))
        offset += len(line)
    if fence:
        out.append(Token(fence[1], len(text), text[fence[1]:], "unclosed_fence"))
    masked = mask(text, out)
    # Exact backtick run matching; unmatched runs remain prose.
    cursor = 0
    while cursor < len(masked):
        match = re.search(r"`+", masked[cursor:])
        if not match:
            break
        start = cursor + match.start()
        run = match.group()
        tail = start + len(run)
        end_match = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", masked[tail:])
        if end_match:
            end = tail + end_match.end()
            out.append(Token(start, end, text[start:end], "inline_code"))
            cursor = end
        else:
            cursor = tail
    masked = mask(text, out)
    patterns = (
        (r'"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’', "quotation"),
        (r"\]\((?:[^()\n]|\([^()\n]*\))*\)", "link_destination"),
        (r"https?://[^\s<>]+", "url"),
    )
    for pattern, kind in patterns:
        for item in tokens(pattern, masked, kind):
            out.append(Token(item.start, item.end, text[item.start:item.end], kind))
        masked = mask(text, out)
    return sorted(out, key=lambda x: (x.start, x.end))


def mask(text: str, spans: list[Token]) -> str:
    chars = list(text)
    for item in spans:
        for index in range(item.start, item.end):
            if chars[index] not in "\r\n":
                chars[index] = " "
    return "".join(chars)


def location(text: str, token: Token | None) -> dict | None:
    if token is None:
        return None
    return {"start": token.start, "end": token.end,
            "line": text.count("\n", 0, token.start) + 1,
            "column": token.start - text.rfind("\n", 0, token.start),
            "quote": text[token.start:token.end]}


VALUE = (r"(?<![A-Za-z0-9_])(?:[<>]=?|[=!]=)?\s*v?[+-]?\d+"
         r"(?:[.,]\d+)*(?:[-/]\d+)*(?:\s*(?:ms|KiB|MiB|KB|MB|GB|%|초|분|회|대|바이트|문자))?"
         r"|이상|이하|초과|미만|최소|최대")
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*(?:[.:][A-Za-z_][A-Za-z0-9_]*)*(?:\(\))?"
NEGATION = r"않[가-힣]*|없[가-힣]*|아니[가-힣]*|못[가-힣]*|금지|미수행|미지원|불가"
UNCERTAINTY = r"수\s*있[가-힣]*|가능성[가-힣]*|추정[가-힣]*|예상[가-힣]*|미확인|확인\s*필요|가설[가-힣]*|예정[가-힣]*|계획[가-힣]*"
CONDITION = r"[가-힣A-Za-z0-9_]*(?:으면|면)\b|경우|때\b|제외[가-힣]*|한해|단,|오직"


def review(source: str | None, candidate: str, term_config: dict | None = None) -> dict:
    if term_config is None:
        term_config = json.loads((ROOT / "references/lint-terms.json").read_text(encoding="utf-8"))
    validate_term_config(term_config)
    rules = json.loads((ROOT / "rules/rules.json").read_text(encoding="utf-8"))
    findings: list[dict] = []
    src = source if source is not None else ""
    sp, cp = protected(src), protected(candidate)
    sm, cm = mask(src, sp), mask(candidate, cp)

    def add(check: str, rule: str, message: str, a: Token | None = None, b: Token | None = None):
        findings.append({"check": check, "rule_id": rule, "severity": "WARN",
                         "certainty": "candidate", "source_span": location(src, a),
                         "candidate_span": location(candidate, b), "message": message,
                         "next_action": "원문과 문맥을 대조하고 사람이 판단하세요. 자동 치환하지 마세요."})

    def compare(check: str, rule: str, a: list[Token], b: list[Token], message: str):
        keys_a, keys_b = [(x.kind, x.text) for x in a], [(x.kind, x.text) for x in b]
        for op, i, j, k, l in SequenceMatcher(None, keys_a, keys_b, autojunk=False).get_opcodes():
            if op != "equal":
                # One finding per changed token; preserve multiplicity and both offsets.
                for n in range(max(j - i, l - k)):
                    add(check, rule, message, a[i+n] if i+n < j else None,
                        b[k+n] if k+n < l else None)

    if source is not None and src != candidate:
        compare("protected", "YSK-M05", sp, cp, "보호 구간의 내용, 순서 또는 개수가 달라졌습니다.")
        compare("values", "YSK-M04", tokens(VALUE, sm, "value"), tokens(VALUE, cm, "value"),
                "값, 단위, 경계 또는 등장 순서가 달라졌습니다. 같은 값의 압축도 경고할 수 있습니다.")
        def ids(text: str) -> list[Token]:
            return [t for t in tokens(IDENTIFIER, text, "identifier")
                    if any(c in t.text for c in "_.:()") or
                    (len(t.text) > 1 and (t.text.isupper() or re.search(r"[a-z][A-Z]", t.text)))]
        compare("identifiers", "YSK-M05", ids(sm), ids(cm), "API 또는 식별자 후보가 달라졌습니다.")
        compare("negation", "YSK-M03", tokens(NEGATION, sm, "negative"), tokens(NEGATION, cm, "negative"),
                "부정 표현이 달라졌습니다. 부정 대상과 부분 부정을 확인하세요.")
        compare("uncertainty", "YSK-M08", tokens(UNCERTAINTY, sm, "uncertainty"),
                tokens(UNCERTAINTY, cm, "uncertainty"), "불확실성 표현이 달라졌습니다. 동의 표현일 수 있습니다.")
        ca, cb = tokens(CONDITION, sm, "condition"), tokens(CONDITION, cm, "condition")
        compare("conditions", "YSK-M02", ca, cb, "조건 또는 예외 표현이 달라졌습니다.")
        boundaries = lambda text: len(re.findall(r"[.!?](?:\s|$)|\n", text))
        if ca and boundaries(sm) != boundaries(cm):
            add("conditions", "YSK-M02", "조건이 있는 글의 문장 또는 목록 경계가 바뀌었습니다. 뒤 문장의 조건 범위를 확인하세요.", ca[0], cb[0] if cb else None)
        # The dictionary contains distinct concepts, never synonym replacement pairs.
        distinctions = json.loads((ROOT / "references/terminology.json").read_text(encoding="utf-8"))
        for entry in distinctions["entries"]:
            a, b = entry["term_a"], entry["term_b"]
            if (sm.count(a) > cm.count(a) and cm.count(b) > sm.count(b)) or (sm.count(b) > cm.count(b) and cm.count(a) > sm.count(a)):
                old, new = (a, b) if sm.count(a) > cm.count(a) else (b, a)
                add("terminology", "YSK-K05", f"{entry['id']}: 서로 다른 개념인 {a}/{b}의 사용량이 바뀌었습니다. terminology.json의 정의와 예외를 대조하세요.",
                    Token(sm.index(old), sm.index(old)+len(old), old, "term"),
                    Token(cm.index(new), cm.index(new)+len(new), new, "term"))
    # Candidate-only hints also run for unchanged documents. These do not assert missing actors.
    for item in tokens(r"이것|그것|해당\s*(?:프로세스|모듈|대상|처리)|기록됩니다|전송됩니다|처리됩니다", cm, "subject"):
        add("subject", "YSK-K02", "지시 대상 또는 행동 주체를 문맥에서 확인하세요. 피동형 자체는 오류가 아닙니다.", b=item)
    for group in term_config["groups"]:
        variants = []
        for term in [group["canonical"], *group["variants"]]:
            # ASCII word boundaries, allowing Korean particles after Korean terms.
            pattern = r"(?<![A-Za-z0-9_가-힣])" + re.escape(term) + r"(?![A-Za-z0-9_])"
            hits = list(re.finditer(pattern, cm))
            if hits:
                variants.append((term, hits[0]))
        if len(variants) > 1:
            hit = variants[1][1]
            add("terminology", "YSK-K05", f"{group['id']}: 표기 후보가 혼용됩니다. 프로젝트 정의가 같은지 먼저 확인하세요.",
                b=Token(hit.start(), hit.end(), hit.group(), "term"))
    expressions_raw = (ROOT / "references/preferred-expressions.json").read_bytes()
    expressions = json.loads(expressions_raw)
    for entry in expressions["entries"]:
        for signal in entry["signals"]:
            pattern = r"(?<![A-Za-z0-9_가-힣])" + re.escape(signal)
            for hit in re.finditer(pattern, cm):
                add("terminology", "YSK-K07",
                    f"{entry['id']}: 권장 표현 후보는 {entry['preferred']}입니다. "
                    "적용 조건과 예외, 부정과 의무 수준을 확인하세요. 원문 유지가 적절할 수 있습니다.",
                    b=Token(hit.start(), hit.end(), hit.group(), "expression"))
    skipped = ["semantic_equivalence", "facts", "causal_and_actor_binding", "full_commonmark",
               "human_evaluation", "length_disabled_by_default"]
    if source is None:
        skipped.extend("source_comparison:" + check for check in CHECKS if check not in ("subject", "terminology"))
    return {"schema_version": "0.2", "tool_version": TOOL_VERSION, "spec_version": rules["version"],
            "input_hashes": {"source": hashlib.sha256(src.encode()).hexdigest() if source is not None else None,
                             "candidate": hashlib.sha256(candidate.encode()).hexdigest()},
            "config_hashes": {"terms": hashlib.sha256(json.dumps(term_config, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                              "distinctions": hashlib.sha256((ROOT / "references/terminology.json").read_bytes()).hexdigest(),
                              "expressions": hashlib.sha256(expressions_raw).hexdigest()},
            "span_convention": "0-based Python Unicode code points; end exclusive; line/column 1-based; no normalization",
            "checks_run": list(CHECKS) if source is not None else ["subject", "terminology"],
            "checks_skipped": skipped, "findings": findings,
            "notice": "경고는 검토 후보입니다. 경고 없음과 종료 코드 0은 의미 보존이나 사실의 정확성을 보장하지 않습니다."}


def validate_term_config(data: object) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        raise ValueError("terms config requires a groups array")
    seen = set()
    for group in data["groups"]:
        if not isinstance(group, dict) or not all(isinstance(group.get(k), str) and group[k] for k in ("id", "canonical")):
            raise ValueError("invalid term group")
        if group["id"] in seen:
            raise ValueError("duplicate term group id")
        seen.add(group["id"])
        variants = group.get("variants")
        if not isinstance(variants, list) or not variants or any(not isinstance(x, str) or not x for x in variants):
            raise ValueError("term variants must be nonempty strings")
        if len({group["canonical"], *variants}) != len(variants) + 1:
            raise ValueError("duplicate term variant")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Optional original UTF-8 text")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--terms", type=Path, help="Optional project-specific spelling groups")
    parser.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args(argv)
    try:
        # Read bytes to avoid universal newline conversion and preserve CRLF offsets.
        candidate = args.candidate.read_bytes().decode("utf-8")
        source = args.source.read_bytes().decode("utf-8") if args.source else None
        config = json.loads(args.terms.read_text(encoding="utf-8")) if args.terms else None
        print(json.dumps(review(source, candidate, config), ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
