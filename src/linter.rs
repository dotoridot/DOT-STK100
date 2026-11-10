use fancy_regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::cell::{OnceCell, RefCell};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::rc::Rc;

pub const TOOL_VERSION: &str = "0.2.0";
pub const CHECKS: [&str; 8] = [
    "protected",
    "values",
    "identifiers",
    "negation",
    "uncertainty",
    "conditions",
    "subject",
    "terminology",
];

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Token {
    pub start: usize,
    pub end: usize,
    pub text: String,
    pub kind: String,
}

thread_local! {
    static REGEXES: RefCell<HashMap<String, Rc<Regex>>> = RefCell::new(HashMap::new());
}

// Python's Unicode word class excludes combining marks; its whitespace class
// also includes the four information separators outside Unicode White_Space.
fn expression(pattern: &str) -> Result<Rc<Regex>, String> {
    REGEXES.with(|cache| {
        if let Some(found) = cache.borrow().get(pattern) {
            return Ok(Rc::clone(found));
        }
        let pattern_python = python_pattern(pattern);
        let compiled = Rc::new(Regex::new(&pattern_python).map_err(|e| e.to_string())?);
        cache
            .borrow_mut()
            .insert(pattern.to_owned(), Rc::clone(&compiled));
        Ok(compiled)
    })
}

fn python_pattern(pattern: &str) -> String {
    let mut chars = pattern.chars();
    let mut translated = String::new();
    let mut in_class = false;
    while let Some(ch) = chars.next() {
        if ch == '\\' {
            let Some(escaped) = chars.next() else {
                translated.push(ch);
                break;
            };
            let replacement = match escaped {
                's' => Some(r"[\p{White_Space}\x{001c}-\x{001f}]"),
                'S' => Some(r"[^\p{White_Space}\x{001c}-\x{001f}]"),
                'w' => Some(r"[\p{L}\p{N}_]"),
                'W' => Some(r"[^\p{L}\p{N}_]"),
                'b' if !in_class => Some(
                    r"(?:(?<=[\p{L}\p{N}_])(?=[^\p{L}\p{N}_]|$)|(?<![\p{L}\p{N}_])(?=[\p{L}\p{N}_]))",
                ),
                'b' => Some(r"\x08"),
                'Z' => Some(r"\z"),
                _ => None,
            };
            if let Some(replacement) = replacement {
                translated.push_str(replacement);
            } else {
                translated.push('\\');
                translated.push(escaped);
            }
        } else {
            if ch == '[' {
                in_class = true;
            } else if ch == ']' {
                in_class = false;
            }
            translated.push(ch);
        }
    }
    translated
}

pub fn tokens(pattern: &str, text: &str, kind: &str) -> Result<Vec<Token>, String> {
    let regex = expression(pattern)?;
    let (mut previous_byte, mut previous_codepoint) = (0, 0);
    regex
        .find_iter(text)
        .map(|m| {
            let m = m.map_err(|e| e.to_string())?;
            let start = previous_codepoint + text[previous_byte..m.start()].chars().count();
            let end = start + m.as_str().chars().count();
            previous_byte = m.end();
            previous_codepoint = end;
            Ok(Token {
                start,
                end,
                text: m.as_str().to_owned(),
                kind: kind.to_owned(),
            })
        })
        .collect()
}

pub fn splitlines_keepends(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut iter = text.char_indices().peekable();
    while let Some((index, ch)) = iter.next() {
        if matches!(
            ch,
            '\n' | '\r'
                | '\u{b}'
                | '\u{c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        ) {
            let mut end = index + ch.len_utf8();
            if ch == '\r' && iter.peek().is_some_and(|(_, c)| *c == '\n') {
                end = iter.next().expect("peeked newline").0 + 1;
            }
            lines.push(&text[start..end]);
            start = end;
        }
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

fn slice(text: &str, start: usize, end: usize) -> String {
    text.chars().skip(start).take(end - start).collect()
}

fn token(text: &str, start: usize, end: usize, kind: &str) -> Token {
    Token {
        start,
        end,
        text: slice(text, start, end),
        kind: kind.to_owned(),
    }
}

pub fn protected(text: &str) -> Vec<Token> {
    protected_inner(text).expect("fixed protection patterns are valid")
}

fn protected_inner(text: &str) -> Result<Vec<Token>, String> {
    let mut out = Vec::new();
    let mut offset = 0;
    let mut fence: Option<(String, usize)> = None;
    for line in splitlines_keepends(text) {
        let opening = expression(r"^ {0,3}(`{3,}|~{3,})(.*)")?
            .captures(line)
            .map_err(|e| e.to_string())?;
        if let Some((marker, start)) = &fence {
            let close = format!(
                r"\A {{0,3}}{}{{{},}}[ \t]*(?:\r?\n)?\z",
                regex::escape(&marker[..1]),
                marker.len()
            );
            if expression(&close)?
                .is_match(line)
                .map_err(|e| e.to_string())?
            {
                out.push(token(text, *start, offset + line.chars().count(), "fence"));
                fence = None;
            }
        } else if let Some(opening) = opening {
            fence = Some((opening.get(1).expect("capture").as_str().to_owned(), offset));
        } else if expression(r"^(?: {0,3}>| {4}|\t|\s*\||\s*(?:INFO|WARN|ERROR|DEBUG)\b)")?
            .is_match(line)
            .map_err(|e| e.to_string())?
        {
            out.push(token(
                text,
                offset,
                offset + line.chars().count(),
                "opaque_line",
            ));
        }
        offset += line.chars().count();
    }
    if let Some((_, start)) = fence {
        out.push(token(text, start, text.chars().count(), "unclosed_fence"));
    }
    let masked = mask(text, &out);
    let mut cursor = 0;
    while cursor < masked.len() {
        let Some(found) = expression(r"`+")?
            .find(&masked[cursor..])
            .map_err(|e| e.to_string())?
        else {
            break;
        };
        let start = cursor + found.start();
        let run = found.as_str();
        let tail = start + run.len();
        let closer = format!(r"(?<!`){}(?!`)", regex::escape(run));
        if let Some(end_match) = expression(&closer)?
            .find(&masked[tail..])
            .map_err(|e| e.to_string())?
        {
            let end = tail + end_match.end();
            out.push(token(
                text,
                masked[..start].chars().count(),
                masked[..end].chars().count(),
                "inline_code",
            ));
            cursor = end;
        } else {
            cursor = tail;
        }
    }
    let mut masked = mask(text, &out);
    for (pattern, kind) in [
        (r#""[^"\n]*"|“[^”\n]*”|‘[^’\n]*’"#, "quotation"),
        (r"\]\((?:[^()\n]|\([^()\n]*\))*\)", "link_destination"),
        (r"https?://[^\s<>]+", "url"),
    ] {
        for item in tokens(pattern, &masked, kind)? {
            out.push(token(text, item.start, item.end, kind));
        }
        masked = mask(text, &out);
    }
    out.sort_by_key(|item| (item.start, item.end));
    Ok(out)
}

pub fn mask(text: &str, spans: &[Token]) -> String {
    let mut chars: Vec<char> = text.chars().collect();
    for span in spans {
        for ch in chars.iter_mut().take(span.end).skip(span.start) {
            if !matches!(*ch, '\r' | '\n') {
                *ch = ' ';
            }
        }
    }
    chars.into_iter().collect()
}

pub fn location(text: &str, span: Option<&Token>) -> Value {
    match span {
        None => Value::Null,
        Some(span) => {
            let prefix: Vec<char> = text.chars().take(span.start).collect();
            let line = prefix.iter().filter(|c| **c == '\n').count() + 1;
            let column = span.start
                - prefix
                    .iter()
                    .rposition(|c| *c == '\n')
                    .map(|i| i + 1)
                    .unwrap_or(0)
                + 1;
            json!({ "start": span.start, "end": span.end, "line": line, "column": column, "quote": slice(text, span.start, span.end) })
        }
    }
}

fn key_equal(a: &Token, b: &Token) -> bool {
    a.kind == b.kind && a.text == b.text
}

// Ratcliff/Obershelp matching with SequenceMatcher's earliest a/earliest b
// tie-break and no popularity filtering (autojunk=False).
fn matching_blocks(a: &[Token], b: &[Token]) -> Vec<(usize, usize, usize)> {
    let mut positions: HashMap<(&str, &str), Vec<usize>> = HashMap::new();
    for (j, token) in b.iter().enumerate() {
        positions
            .entry((&token.kind, &token.text))
            .or_default()
            .push(j);
    }
    let mut pending = vec![(0, a.len(), 0, b.len())];
    let mut blocks = Vec::new();
    while let Some((alo, ahi, blo, bhi)) = pending.pop() {
        let (mut besti, mut bestj, mut size) = (alo, blo, 0);
        let mut previous = HashMap::<usize, usize>::new();
        for (i, item) in a.iter().enumerate().take(ahi).skip(alo) {
            let mut current = HashMap::new();
            if let Some(js) = positions.get(&(item.kind.as_str(), item.text.as_str())) {
                for &j in js {
                    if j < blo {
                        continue;
                    }
                    if j >= bhi {
                        break;
                    }
                    let k = if j == 0 {
                        1
                    } else {
                        previous.get(&(j - 1)).copied().unwrap_or(0) + 1
                    };
                    current.insert(j, k);
                    if k > size {
                        (besti, bestj, size) = (i + 1 - k, j + 1 - k, k);
                    }
                }
            }
            previous = current;
        }
        while besti > alo && bestj > blo && key_equal(&a[besti - 1], &b[bestj - 1]) {
            besti -= 1;
            bestj -= 1;
            size += 1;
        }
        while besti + size < ahi
            && bestj + size < bhi
            && key_equal(&a[besti + size], &b[bestj + size])
        {
            size += 1;
        }
        if size > 0 {
            blocks.push((besti, bestj, size));
            if alo < besti && blo < bestj {
                pending.push((alo, besti, blo, bestj));
            }
            if besti + size < ahi && bestj + size < bhi {
                pending.push((besti + size, ahi, bestj + size, bhi));
            }
        }
    }
    blocks.sort_unstable();
    let mut collapsed = Vec::<(usize, usize, usize)>::new();
    for (i, j, n) in blocks {
        if let Some(last) = collapsed.last_mut()
            && last.0 + last.2 == i
            && last.1 + last.2 == j
        {
            last.2 += n;
            continue;
        }
        collapsed.push((i, j, n));
    }
    collapsed.push((a.len(), b.len(), 0));
    collapsed
}

fn add(
    findings: &mut Vec<Value>,
    source: &str,
    candidate: &str,
    check: &str,
    rule: &str,
    message: &str,
    spans: (Option<&Token>, Option<&Token>),
) {
    findings.push(json!({ "check": check, "rule_id": rule, "severity": "WARN", "certainty": "candidate", "source_span": location(source, spans.0), "candidate_span": location(candidate, spans.1), "message": message, "next_action": "원문과 문맥을 대조하고 사람이 판단하세요. 자동 치환하지 마세요." }));
}

fn compare(
    findings: &mut Vec<Value>,
    texts: (&str, &str),
    check: &str,
    rule: &str,
    a: &[Token],
    b: &[Token],
    message: &str,
) {
    let (mut i, mut j) = (0, 0);
    for (ai, bj, n) in matching_blocks(a, b) {
        if i < ai || j < bj {
            for offset in 0..(ai - i).max(bj - j) {
                add(
                    findings,
                    texts.0,
                    texts.1,
                    check,
                    rule,
                    message,
                    (
                        a.get(i + offset).filter(|_| i + offset < ai),
                        b.get(j + offset).filter(|_| j + offset < bj),
                    ),
                );
            }
        }
        i = ai + n;
        j = bj + n;
    }
}

const VALUE: &str = r"(?<![A-Za-z0-9_])(?:[<>]=?|[=!]=)?\s*v?[+-]?\d+(?:[.,]\d+)*(?:[-/]\d+)*(?:\s*(?:ms|KiB|MiB|KB|MB|GB|%|초|분|회|대|바이트|문자))?|이상|이하|초과|미만|최소|최대";
const IDENTIFIER: &str = r"[A-Za-z_][A-Za-z0-9_]*(?:[.:][A-Za-z_][A-Za-z0-9_]*)*(?:\(\))?";
const NEGATION: &str = r"않[가-힣]*|없[가-힣]*|아니[가-힣]*|못[가-힣]*|금지|미수행|미지원|불가";
const UNCERTAINTY: &str = r"수\s*있[가-힣]*|가능성[가-힣]*|추정[가-힣]*|예상[가-힣]*|미확인|확인\s*필요|가설[가-힣]*|예정[가-힣]*|계획[가-힣]*";
const CONDITION: &str = r"[가-힣A-Za-z0-9_]*(?:으면|면)\b|경우|때\b|제외[가-힣]*|한해|단,|오직";

pub fn sha256(data: &[u8]) -> String {
    format!("{:x}", Sha256::digest(data))
}

pub fn read_json(path: &Path) -> Result<Value, String> {
    let bytes = fs::read(path).map_err(|e| format!("{}: {e}", path.display()))?;
    serde_json::from_slice(&bytes).map_err(|e| format!("{}: {e}", path.display()))
}

// Keep the Python json.dumps default separators and sorted object keys used
// by config_hashes.terms. Other dictionary hashes deliberately use raw bytes.
pub fn python_json(value: &Value) -> String {
    match value {
        Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            format!(
                "{{{}}}",
                keys.into_iter()
                    .map(|key| format!(
                        "{}: {}",
                        serde_json::to_string(key).expect("JSON key"),
                        python_json(&map[key])
                    ))
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        }
        Value::Array(items) => format!(
            "[{}]",
            items.iter().map(python_json).collect::<Vec<_>>().join(", ")
        ),
        Value::Number(number) => python_number(number),
        _ => value.to_string(),
    }
}

fn python_number(number: &serde_json::Number) -> String {
    let original = number.to_string();
    if !original.contains(['.', 'e', 'E']) {
        return if original == "-0" {
            "0".to_owned()
        } else {
            original
        };
    }
    let Some(value) = number.as_f64().filter(|n| n.is_finite()) else {
        return original;
    };
    if value == 0.0 {
        return if value.is_sign_negative() {
            "-0.0".to_owned()
        } else {
            "0.0".to_owned()
        };
    }
    let repr = serde_json::Number::from_f64(value)
        .expect("finite number")
        .to_string();
    let sign = if value.is_sign_negative() { "-" } else { "" };
    let repr = repr.trim_start_matches('-');
    let (mantissa, exponent) = repr
        .split_once(['e', 'E'])
        .map(|(m, e)| (m, e.parse::<i32>().expect("JSON exponent")))
        .unwrap_or((repr, 0));
    let decimal = mantissa.find('.').unwrap_or(mantissa.len()) as i32;
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let leading = digits.bytes().take_while(|c| *c == b'0').count();
    let scientific_exponent = decimal - leading as i32 - 1 + exponent;
    let significant = digits[leading..].trim_end_matches('0');
    if !(-4..16).contains(&scientific_exponent) {
        let (first, rest) = significant.split_at(1);
        let fraction = if rest.is_empty() {
            String::new()
        } else {
            format!(".{rest}")
        };
        let exponent_sign = if scientific_exponent < 0 { '-' } else { '+' };
        format!(
            "{sign}{first}{fraction}e{exponent_sign}{:02}",
            scientific_exponent.abs()
        )
    } else {
        let point = scientific_exponent + 1;
        if point <= 0 {
            format!("{sign}0.{}{significant}", "0".repeat((-point) as usize))
        } else if point as usize >= significant.len() {
            format!(
                "{sign}{significant}{}.0",
                "0".repeat(point as usize - significant.len())
            )
        } else {
            format!(
                "{sign}{}.{}",
                &significant[..point as usize],
                &significant[point as usize..]
            )
        }
    }
}

pub fn validate_term_config(data: &Value) -> Result<(), String> {
    let groups = data
        .as_object()
        .and_then(|d| d.get("groups"))
        .and_then(Value::as_array)
        .ok_or("terms config requires a groups array")?;
    let mut seen = HashSet::new();
    for group in groups {
        let id = group
            .get("id")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty())
            .ok_or("invalid term group")?;
        let canonical = group
            .get("canonical")
            .and_then(Value::as_str)
            .filter(|s| !s.is_empty())
            .ok_or("invalid term group")?;
        if !seen.insert(id) {
            return Err("duplicate term group id".into());
        }
        let variants = group
            .get("variants")
            .and_then(Value::as_array)
            .filter(|items| !items.is_empty())
            .ok_or("term variants must be nonempty strings")?;
        let mut variants_seen = HashSet::from([canonical]);
        for variant in variants {
            let term = variant
                .as_str()
                .filter(|s| !s.is_empty())
                .ok_or("term variants must be nonempty strings")?;
            if !variants_seen.insert(term) {
                return Err("duplicate term variant".into());
            }
        }
    }
    Ok(())
}

fn string<'a>(value: &'a Value, key: &str) -> Result<&'a str, String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("missing or invalid {key}"))
}
fn array<'a>(value: &'a Value, key: &str) -> Result<&'a Vec<Value>, String> {
    value
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("missing or invalid {key}"))
}

/// Reuse configuration only within one caller-owned operation. A new operation
/// creates a new context so file updates remain visible between calls.
pub struct ReviewContext {
    root: PathBuf,
    config: Value,
    rules: Value,
    terms_hash: String,
    distinctions_raw: OnceCell<Result<(Vec<u8>, String), String>>,
    distinctions: OnceCell<Result<Value, String>>,
    expressions: OnceCell<Result<(Value, String), String>>,
}

impl ReviewContext {
    pub fn new(root: &Path, term_config: Option<Value>) -> Result<Self, String> {
        let config = match term_config {
            Some(config) => config,
            None => read_json(&root.join("references/lint-terms.json"))?,
        };
        validate_term_config(&config)?;
        let rules = read_json(&root.join("rules/rules.json"))?;
        let terms_hash = sha256(python_json(&config).as_bytes());
        Ok(Self {
            root: root.to_owned(),
            config,
            rules,
            terms_hash,
            distinctions_raw: OnceCell::new(),
            distinctions: OnceCell::new(),
            expressions: OnceCell::new(),
        })
    }

    fn distinctions_raw(&self) -> Result<&(Vec<u8>, String), String> {
        self.distinctions_raw
            .get_or_init(|| {
                let raw = fs::read(self.root.join("references/terminology.json"))
                    .map_err(|e| e.to_string())?;
                let hash = sha256(&raw);
                Ok((raw, hash))
            })
            .as_ref()
            .map_err(Clone::clone)
    }

    fn distinctions(&self) -> Result<&Value, String> {
        self.distinctions
            .get_or_init(|| {
                let path = self.root.join("references/terminology.json");
                let raw = self
                    .distinctions_raw()
                    .map_err(|e| format!("{}: {e}", path.display()))?;
                serde_json::from_slice(&raw.0).map_err(|e| format!("{}: {e}", path.display()))
            })
            .as_ref()
            .map_err(Clone::clone)
    }

    fn expressions(&self) -> Result<&(Value, String), String> {
        self.expressions
            .get_or_init(|| {
                let raw = fs::read(self.root.join("references/preferred-expressions.json"))
                    .map_err(|e| e.to_string())?;
                let value = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
                Ok((value, sha256(&raw)))
            })
            .as_ref()
            .map_err(Clone::clone)
    }

    pub fn review(&self, source: Option<&str>, candidate: &str) -> Result<Value, String> {
        let config = &self.config;
        let rules = &self.rules;
        let src = source.unwrap_or("");
        let sp = protected_inner(src)?;
        let cp = protected_inner(candidate)?;
        let sm = mask(src, &sp);
        let cm = mask(candidate, &cp);
        let mut findings = Vec::new();
        if source.is_some() && src != candidate {
            compare(
                &mut findings,
                (src, candidate),
                "protected",
                "YSK-M05",
                &sp,
                &cp,
                "보호 구간의 내용, 순서 또는 개수가 달라졌습니다.",
            );
            for (check, rule, pattern, kind, message) in [
                (
                    "values",
                    "YSK-M04",
                    VALUE,
                    "value",
                    "값, 단위, 경계 또는 등장 순서가 달라졌습니다. 같은 값의 압축도 경고할 수 있습니다.",
                ),
                (
                    "identifiers",
                    "YSK-M05",
                    IDENTIFIER,
                    "identifier",
                    "API 또는 식별자 후보가 달라졌습니다.",
                ),
                (
                    "negation",
                    "YSK-M03",
                    NEGATION,
                    "negative",
                    "부정 표현이 달라졌습니다. 부정 대상과 부분 부정을 확인하세요.",
                ),
                (
                    "uncertainty",
                    "YSK-M08",
                    UNCERTAINTY,
                    "uncertainty",
                    "불확실성 표현이 달라졌습니다. 동의 표현일 수 있습니다.",
                ),
                (
                    "conditions",
                    "YSK-M02",
                    CONDITION,
                    "condition",
                    "조건 또는 예외 표현이 달라졌습니다.",
                ),
            ] {
                let mut a = tokens(pattern, &sm, kind)?;
                let mut b = tokens(pattern, &cm, kind)?;
                if check == "identifiers" {
                    let keep = |t: &Token| {
                        t.text.contains(['_', '.', ':', '(', ')'])
                            || (t.text.len() > 1
                                && (t.text.chars().any(|c| c.is_ascii_uppercase())
                                    && !t.text.chars().any(|c| c.is_ascii_lowercase())
                                    || t.text.as_bytes().windows(2).any(|w| {
                                        w[0].is_ascii_lowercase() && w[1].is_ascii_uppercase()
                                    })))
                    };
                    a.retain(keep);
                    b.retain(keep);
                }
                compare(
                    &mut findings,
                    (src, candidate),
                    check,
                    rule,
                    &a,
                    &b,
                    message,
                );
                if check == "conditions"
                    && !a.is_empty()
                    && tokens(r"[.!?](?:\s|$)|\n", &sm, "boundary")?.len()
                        != tokens(r"[.!?](?:\s|$)|\n", &cm, "boundary")?.len()
                {
                    add(
                        &mut findings,
                        src,
                        candidate,
                        "conditions",
                        "YSK-M02",
                        "조건이 있는 글의 문장 또는 목록 경계가 바뀌었습니다. 뒤 문장의 조건 범위를 확인하세요.",
                        (a.first(), b.first()),
                    );
                }
            }
            let distinctions = self.distinctions()?;
            for entry in array(distinctions, "entries")? {
                let (a, b) = (string(entry, "term_a")?, string(entry, "term_b")?);
                let (sa, ca, sb, cb) = (
                    sm.matches(a).count(),
                    cm.matches(a).count(),
                    sm.matches(b).count(),
                    cm.matches(b).count(),
                );
                if (sa > ca && cb > sb) || (sb > cb && ca > sa) {
                    let (old, new) = if sa > ca { (a, b) } else { (b, a) };
                    let old_start = sm[..sm.find(old).ok_or("term not found")?].chars().count();
                    let new_start = cm[..cm.find(new).ok_or("term not found")?].chars().count();
                    let old_token = token(&sm, old_start, old_start + old.chars().count(), "term");
                    let new_token = token(&cm, new_start, new_start + new.chars().count(), "term");
                    add(
                        &mut findings,
                        src,
                        candidate,
                        "terminology",
                        "YSK-K05",
                        &format!(
                            "{}: 서로 다른 개념인 {a}/{b}의 사용량이 바뀌었습니다. terminology.json의 정의와 예외를 대조하세요.",
                            string(entry, "id")?
                        ),
                        (Some(&old_token), Some(&new_token)),
                    );
                }
            }
        }
        for item in tokens(
            r"이것|그것|해당\s*(?:프로세스|모듈|대상|처리)|기록됩니다|전송됩니다|처리됩니다",
            &cm,
            "subject",
        )? {
            add(
                &mut findings,
                src,
                candidate,
                "subject",
                "YSK-K02",
                "지시 대상 또는 행동 주체를 문맥에서 확인하세요. 피동형 자체는 오류가 아닙니다.",
                (None, Some(&item)),
            );
        }
        for group in array(config, "groups")? {
            let mut hits = Vec::new();
            let canonical = string(group, "canonical")?;
            for term in std::iter::once(canonical)
                .chain(array(group, "variants")?.iter().filter_map(Value::as_str))
            {
                let pattern = format!(
                    r"(?<![A-Za-z0-9_가-힣]){}(?![A-Za-z0-9_])",
                    regex::escape(term)
                );
                if let Some(hit) = tokens(&pattern, &cm, "term")?.into_iter().next() {
                    hits.push(hit);
                }
            }
            if hits.len() > 1 {
                add(
                    &mut findings,
                    src,
                    candidate,
                    "terminology",
                    "YSK-K05",
                    &format!(
                        "{}: 표기 후보가 혼용됩니다. 프로젝트 정의가 같은지 먼저 확인하세요.",
                        string(group, "id")?
                    ),
                    (None, Some(&hits[1])),
                );
            }
        }
        let expressions = &self.expressions()?.0;
        for entry in array(expressions, "entries")? {
            for signal in array(entry, "signals")? {
                let signal = signal.as_str().ok_or("invalid expression signal")?;
                let pattern = format!(r"(?<![A-Za-z0-9_가-힣]){}", regex::escape(signal));
                for hit in tokens(&pattern, &cm, "expression")? {
                    add(
                        &mut findings,
                        src,
                        candidate,
                        "terminology",
                        "YSK-K07",
                        &format!(
                            "{}: 권장 표현 후보는 {}입니다. 적용 조건과 예외, 부정과 의무 수준을 확인하세요. 원문 유지가 적절할 수 있습니다.",
                            string(entry, "id")?,
                            string(entry, "preferred")?
                        ),
                        (None, Some(&hit)),
                    );
                }
            }
        }
        let mut skipped = vec![
            "semantic_equivalence".to_owned(),
            "facts".to_owned(),
            "causal_and_actor_binding".to_owned(),
            "full_commonmark".to_owned(),
            "human_evaluation".to_owned(),
            "length_disabled_by_default".to_owned(),
        ];
        if source.is_none() {
            skipped.extend(
                CHECKS
                    .iter()
                    .filter(|check| !matches!(**check, "subject" | "terminology"))
                    .map(|check| format!("source_comparison:{check}")),
            );
        }
        Ok(
            json!({ "schema_version": "0.2", "tool_version": TOOL_VERSION, "spec_version": rules.get("version").ok_or("missing version")?, "input_hashes": { "source": source.map(|s| sha256(s.as_bytes())), "candidate": sha256(candidate.as_bytes()) }, "config_hashes": { "terms": self.terms_hash, "distinctions": self.distinctions_raw()?.1, "expressions": self.expressions()?.1 }, "span_convention": "0-based Python Unicode code points; end exclusive; line/column 1-based; no normalization", "checks_run": if source.is_some() { CHECKS.to_vec() } else { vec!["subject", "terminology"] }, "checks_skipped": skipped, "findings": findings, "notice": "경고는 검토 후보입니다. 경고 없음과 종료 코드 0은 의미 보존이나 사실의 정확성을 보장하지 않습니다." }),
        )
    }
}

pub fn review(
    root: &Path,
    source: Option<&str>,
    candidate: &str,
    term_config: Option<Value>,
) -> Result<Value, String> {
    ReviewContext::new(root, term_config)?.review(source, candidate)
}

pub fn review_many(
    root: &Path,
    cases: &Value,
    term_config: Option<Value>,
) -> Result<Value, String> {
    let cases = cases.as_array().ok_or("batch cases must be an array")?;
    let inputs: Vec<(Option<&str>, &str)> = cases
        .iter()
        .map(|case| {
            let case = case.as_object().ok_or("batch case must be an object")?;
            let source = match case.get("source") {
                None | Some(Value::Null) => None,
                Some(Value::String(source)) => Some(source.as_str()),
                _ => return Err("source must be a string or null".to_owned()),
            };
            let candidate = case
                .get("candidate")
                .and_then(Value::as_str)
                .ok_or("batch candidate must be a string")?;
            Ok((source, candidate))
        })
        .collect::<Result<_, String>>()?;
    if inputs.is_empty() {
        return Ok(json!([]));
    }
    let context = ReviewContext::new(root, term_config)?;
    let results: Vec<Value> = inputs
        .into_iter()
        .map(|(source, candidate)| context.review(source, candidate))
        .collect::<Result<_, _>>()?;
    Ok(json!(results))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_lines_and_unicode_spans() {
        assert_eq!(
            splitlines_keepends("a\r\nb\rc\u{85}d\u{2028}"),
            ["a\r\n", "b\r", "c\u{85}", "d\u{2028}"]
        );
        let text = "🙂\r\n가 `x` e\u{301}";
        let spans = protected(text);
        assert_eq!((spans[0].start, spans[0].end), (5, 8));
        assert_eq!(
            location(text, Some(&spans[0])),
            json!({"start":5,"end":8,"line":2,"column":3,"quote":"`x`"})
        );
    }

    #[test]
    fn regex_python_word_and_whitespace() {
        assert_eq!(
            tokens(CONDITION, "때\u{301}", "condition").unwrap().len(),
            1
        );
        assert_eq!(
            tokens(UNCERTAINTY, "수\u{1c}있습니다", "uncertainty").unwrap()[0].text,
            "수\u{1c}있습니다"
        );
        assert_eq!(tokens(r"\\s", r"\s", "literal").unwrap()[0].text, r"\s");
        assert_eq!(tokens(r"\\b", r"\b", "literal").unwrap()[0].text, r"\b");
    }

    #[test]
    fn repeated_tokens_choose_earliest_longest_match() {
        let seq = |s: &str| {
            s.chars()
                .enumerate()
                .map(|(i, c)| Token {
                    start: i,
                    end: i + 1,
                    text: c.to_string(),
                    kind: "test".into(),
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(
            matching_blocks(&seq("ababa"), &seq("babab")),
            [(0, 1, 4), (5, 5, 0)]
        );
        assert_eq!(
            matching_blocks(&seq("AAAB"), &seq("ABAA")),
            [(0, 2, 2), (4, 4, 0)]
        );
    }

    #[test]
    fn sorted_python_json_spacing() {
        assert_eq!(
            python_json(&json!({"한글":[true,null,"é"],"a":2})),
            "{\"a\": 2, \"한글\": [true, null, \"é\"]}"
        );
    }

    #[test]
    fn python_float_formatting_in_terms_hash() {
        for (raw, expected) in [
            ("1e-7", "1e-07"),
            ("1e-4", "0.0001"),
            ("1e15", "1000000000000000.0"),
            ("1e16", "1e+16"),
            ("-0.0", "-0.0"),
            ("1.2300", "1.23"),
            (
                "123456789012345678901234567890",
                "123456789012345678901234567890",
            ),
        ] {
            assert_eq!(python_json(&serde_json::from_str(raw).unwrap()), expected);
        }
    }

    fn fixture() -> std::path::PathBuf {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let root = std::env::temp_dir().join(format!(
            "dot-stk100-context-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(root.join("rules")).unwrap();
        fs::create_dir_all(root.join("references")).unwrap();
        for relative in [
            "rules/rules.json",
            "references/lint-terms.json",
            "references/terminology.json",
            "references/preferred-expressions.json",
        ] {
            fs::copy(
                Path::new(env!("CARGO_MANIFEST_DIR")).join(relative),
                root.join(relative),
            )
            .unwrap();
        }
        root
    }

    #[test]
    fn batch_matches_independent_reviews_in_input_order() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let mut cases: Vec<Value> = fs::read_to_string(root.join("eval/seed-cases.jsonl"))
            .unwrap()
            .lines()
            .filter(|s| !s.trim().is_empty())
            .map(|s| serde_json::from_str(s).unwrap())
            .collect();
        for relative in [
            "references/terminology.json",
            "references/preferred-expressions.json",
        ] {
            let dictionary = read_json(&root.join(relative)).unwrap();
            cases.extend(
                dictionary["entries"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .flat_map(|e| e["examples"].as_array().unwrap().iter().cloned()),
            );
        }
        cases.extend([
            json!({"source":null,"candidate":"😀e\u{301}\r\n초기화를 수행합니다."}),
            json!({"candidate":"`3회` 그대로"}),
            json!({"source":"3회", "candidate":"3회"}),
        ]);
        let expected: Vec<Value> = cases
            .iter()
            .map(|case| {
                review(
                    root,
                    case["source"].as_str(),
                    case["candidate"].as_str().unwrap(),
                    None,
                )
                .unwrap()
            })
            .collect();
        assert_eq!(
            review_many(root, &json!(cases), None).unwrap(),
            json!(expected)
        );
    }

    #[test]
    fn batch_validates_all_inputs_and_empty_batch_needs_no_files() {
        let missing = Path::new("/dot-stk100-missing-context-root");
        assert_eq!(review_many(missing, &json!([]), None).unwrap(), json!([]));
        for cases in [
            json!(null),
            json!({}),
            json!([null]),
            json!([{"source":42,"candidate":"3회"}]),
            json!([{"source":[],"candidate":"3회"}]),
            json!([{"candidate":false}]),
            json!([{"candidate":"ok"},{"candidate":42}]),
        ] {
            let error = review_many(missing, &cases, None).unwrap_err();
            assert!(
                !error.contains("No such file"),
                "input error must precede package reads: {error}"
            );
        }
    }

    #[test]
    fn context_reuses_its_first_read_but_independent_calls_reload() {
        let root = fixture();
        let context = ReviewContext::new(&root, None).unwrap();
        let first = context
            .review(Some("탐지할 수 있습니다."), "차단합니다.")
            .unwrap();
        for relative in [
            "rules/rules.json",
            "references/lint-terms.json",
            "references/terminology.json",
            "references/preferred-expressions.json",
        ] {
            fs::remove_file(root.join(relative)).unwrap();
        }
        assert_eq!(
            first,
            context
                .review(Some("탐지할 수 있습니다."), "차단합니다.")
                .unwrap()
        );
        assert!(review(&root, Some("탐지할 수 있습니다."), "차단합니다.", None).is_err());
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn independent_reviews_observe_dictionary_updates() {
        let root = fixture();
        let first = review(&root, None, "초기화를 수행합니다.", None).unwrap();
        let path = root.join("references/preferred-expressions.json");
        let mut changed = read_json(&path).unwrap();
        changed["entries"] = json!([]);
        fs::write(path, serde_json::to_vec(&changed).unwrap()).unwrap();
        let second = review(&root, None, "초기화를 수행합니다.", None).unwrap();
        assert_ne!(
            first["config_hashes"]["expressions"],
            second["config_hashes"]["expressions"]
        );
        assert_ne!(first["findings"], second["findings"]);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn terminology_parse_remains_lazy_for_candidate_only_reviews() {
        let root = fixture();
        let path = root.join("references/terminology.json");
        fs::write(&path, "{invalid JSON").unwrap();
        let context = ReviewContext::new(&root, None).unwrap();
        let candidate_only = context.review(None, "문서입니다.").unwrap();
        assert_eq!(
            candidate_only["config_hashes"]["distinctions"],
            sha256(b"{invalid JSON")
        );
        assert!(context.review(Some("탐지"), "차단").is_err());
        let valid =
            fs::read(Path::new(env!("CARGO_MANIFEST_DIR")).join("references/terminology.json"))
                .unwrap();
        fs::write(path, valid).unwrap();
        assert!(
            context.review(Some("탐지"), "차단").is_err(),
            "one context must retain its first dictionary bytes"
        );
        assert!(review(&root, Some("탐지"), "차단", None).is_ok());
        fs::remove_dir_all(root).unwrap();
    }
}
