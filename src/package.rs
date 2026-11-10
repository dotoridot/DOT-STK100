use crate::render::render_document;
use regex::Regex;
use serde_json::{Value, json};
use std::collections::HashSet;
use std::fs;
use std::path::{Component, Path, PathBuf};
use unicode_normalization::UnicodeNormalization;

pub const REQUIRED: &[&str] = &[
    "references/preferred-expressions.json",
    "references/EXPRESSIONS.md",
    "README.md",
    "SKILL.md",
    "AGENTS.md",
    "AUTHORS.md",
    "CITATION.cff",
    "LICENSE.md",
    "NOTICE.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "LICENSES/MIT.txt",
    "rules/rules.json",
    "references/DOT-STK100-SPEC.md",
    "references/RESEARCH.md",
    "references/sources.json",
    "references/terminology.json",
    "docs/AGENT-HANDOFF.md",
    "docs/DESIGN-DECISIONS.md",
    "docs/IMPLEMENTATION-PLAN.md",
    "docs/EVALUATION.md",
    "docs/INTEGRATION.md",
    "docs/MIGRATION.md",
    "docs/RELEASE-CHECKLIST.md",
    "eval/seed-cases.jsonl",
    "eval/DATA-CARD.md",
    "eval/annotation-template.json",
    "eval/review-output.schema.json",
    "examples/BEFORE-AFTER.md",
    "scripts/render_rules.py",
    "scripts/validate_package.py",
    "tests/test_package.py",
    "reports/VALIDATION.md",
    ".github/pull_request_template.md",
    ".gitignore",
    "scripts/lint_text.py",
    "scripts/evaluate_linter.py",
    "docs/LINTER.md",
    "references/lint-terms.json",
    "references/profiles/lite.md",
    "references/profiles/core.md",
    "references/profiles/audit.md",
    "tests/test_linter.py",
    "tests/test_evaluation.py",
    "eval/lint-output.schema.json",
    "docs/HOST-COMPATIBILITY.md",
    "reports/AUDIT.md",
];

const LABELS: [&str; 3] = ["compatible", "meaning_changed", "needs_context"];

fn re(pattern: &str) -> Regex {
    Regex::new(pattern).expect("static package pattern")
}
fn py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}
fn trim(text: &str) -> &str {
    text.trim_matches(py_space)
}
pub fn nonempty(value: &Value) -> bool {
    value.as_str().is_some_and(|s| !trim(s).is_empty())
}
fn truthy(value: &Value) -> bool {
    match value {
        Value::Null => false,
        Value::Bool(v) => *v,
        Value::String(v) => !v.is_empty(),
        Value::Array(v) => !v.is_empty(),
        Value::Object(v) => !v.is_empty(),
        Value::Number(v) => v.as_f64() != Some(0.0),
    }
}
fn strings(value: &Value, require_nonempty: bool) -> Option<Vec<&str>> {
    let list = value.as_array()?;
    if require_nonempty && list.is_empty() {
        return None;
    }
    list.iter()
        .map(|v| {
            v.as_str()
                .filter(|s| !require_nonempty || !trim(s).is_empty())
        })
        .collect()
}
fn fields<'a>(data: &'a Value, key: &str) -> Option<&'a Vec<Value>> {
    data.as_object()?.get(key)?.as_array()
}
fn missing(errors: &mut Vec<String>, value: &Value, loc: &str, keys: &[&str]) {
    for key in keys {
        if !nonempty(&value[*key]) {
            errors.push(format!("{loc}: missing {key}"));
        }
    }
}

pub fn validate_sources(data: &Value) -> Vec<String> {
    let Some(sources) = fields(data, "sources") else {
        return vec!["sources: expected an object with a sources list".into()];
    };
    let mut errors = vec![];
    let mut seen = HashSet::new();
    for (index, source) in sources.iter().enumerate() {
        let loc = format!("sources[{}]", index + 1);
        if !source.is_object() {
            errors.push(format!("{loc}: expected an object"));
            continue;
        }
        if !nonempty(&source["id"]) {
            errors.push(format!("{loc}: missing id"));
        } else if !seen.insert(source["id"].as_str().unwrap()) {
            errors.push(format!(
                "{loc}: duplicate source id {}",
                source["id"].as_str().unwrap()
            ));
        }
        missing(
            &mut errors,
            source,
            &loc,
            &[
                "title",
                "authors",
                "published",
                "url",
                "reviewed_scope",
                "limits",
                "verification_status",
                "confirmed_findings",
                "applicable_principles",
                "non_applicable_principles",
            ],
        );
        if !truthy(&source["accessed"])
            && source["verification_status"] != "inherited_not_reverified"
        {
            errors.push(format!("{loc}: missing accessed for checked source"));
        }
        if strings(&source["hypotheses"], true).is_none() {
            errors.push(format!("{loc}: missing hypotheses"));
        }
        if source["url"]
            .as_str()
            .is_some_and(|v| !v.starts_with("https://"))
        {
            errors.push(format!("{loc}: expected an HTTPS source URL"));
        }
    }
    errors
}

pub fn validate_rules(data: &Value, source_ids: &HashSet<String>) -> Vec<String> {
    let Some(rules) = fields(data, "rules") else {
        return vec!["rules: expected an object with a rules list".into()];
    };
    let mut errors = vec![];
    if rules.is_empty() {
        errors.push("rules: list is empty".into());
    }
    if !nonempty(&data["version"]) {
        errors.push("rules: missing version".into());
    }
    let mut seen = HashSet::new();
    let pattern = re(r"^YSK-[MKEPQ]\d{2}$");
    for (index, rule) in rules.iter().enumerate() {
        let loc = format!("rules[{}]", index + 1);
        if !rule.is_object() {
            errors.push(format!("{loc}: expected an object"));
            continue;
        }
        match rule["id"].as_str() {
            Some(id) if pattern.is_match(id) => {
                if !seen.insert(id) {
                    errors.push(format!("{loc}: duplicate rule id {id}"));
                }
            }
            _ => errors.push(format!("{loc}: invalid rule id")),
        }
        missing(
            &mut errors,
            rule,
            &loc,
            &[
                "section",
                "title",
                "requirement",
                "exception",
                "verification",
                "evidence_status",
            ],
        );
        if !matches!(rule["level"].as_str(), Some("MUST" | "SHOULD")) {
            errors.push(format!("{loc}: invalid rule level"));
        }
        match strings(&rule["sources"], false) {
            None => errors.push(format!("{loc}: sources must be a string list")),
            Some(refs) => {
                for source in refs {
                    if !source_ids.contains(source) {
                        errors.push(format!("{loc}: unknown source {source}"));
                    }
                }
            }
        }
    }
    errors
}

pub fn validate_cases(data: &Value, rule_ids: &HashSet<String>) -> Vec<String> {
    let Some(cases) = data.as_array() else {
        return vec!["cases: expected a list".into()];
    };
    let mut errors = vec![];
    let mut seen = HashSet::new();
    if cases.is_empty() {
        errors.push("cases: empty dataset".into());
    }
    for (index, case) in cases.iter().enumerate() {
        let loc = format!("cases[{}]", index + 1);
        if !case.is_object() {
            errors.push(format!("{loc}: expected an object"));
            continue;
        }
        if !nonempty(&case["case_id"]) {
            errors.push(format!("{loc}: missing case_id"));
        } else if !seen.insert(case["case_id"].as_str().unwrap()) {
            errors.push(format!(
                "{loc}: duplicate case id {}",
                case["case_id"].as_str().unwrap()
            ));
        }
        missing(
            &mut errors,
            case,
            &loc,
            &["pair_id", "source", "candidate", "topic", "note"],
        );
        if !case["expected_review"]
            .as_str()
            .is_some_and(|v| LABELS.contains(&v))
        {
            errors.push(format!("{loc}: invalid expected_review"));
        }
        for (key, value) in [
            ("origin", "synthetic_original"),
            ("split", "development_only"),
            ("label_status", "ai_draft_not_human_adjudicated"),
        ] {
            if case[key] != value {
                errors.push(format!("{loc}: seed {key} must remain {value}"));
            }
        }
        match strings(&case["rule_ids"], false).filter(|v| !v.is_empty()) {
            None => errors.push(format!("{loc}: rule_ids must be a nonempty string list")),
            Some(refs) => {
                for id in refs {
                    if !rule_ids.contains(id) {
                        errors.push(format!("{loc}: unknown rule {id}"));
                    }
                }
            }
        }
    }
    errors
}

pub fn validate_examples(data: &Value, loc: &str) -> Vec<String> {
    let Some(examples) = data.as_array().filter(|v| !v.is_empty()) else {
        return vec![format!("{loc}: examples must be a nonempty list")];
    };
    let mut errors = vec![];
    let mut labels = HashSet::new();
    for example in examples {
        if !example.is_object() {
            errors.push(format!("{loc}: example must be an object"));
            continue;
        }
        for key in ["source", "candidate", "reason"] {
            if !nonempty(&example[key]) {
                errors.push(format!("{loc}: example missing {key}"));
            }
        }
        match example["expected_review"].as_str() {
            Some(label) if LABELS.contains(&label) => {
                labels.insert(label);
            }
            _ => errors.push(format!("{loc}: invalid example label")),
        }
        for (key, expected) in [
            ("origin", "synthetic_original"),
            ("split", "development_only"),
            ("label_status", "ai_draft_not_human_adjudicated"),
        ] {
            if example[key] != expected {
                errors.push(format!("{loc}: example {key} must remain {expected}"));
            }
        }
    }
    if labels != LABELS.into_iter().collect() {
        errors.push(format!(
            "{loc}: examples must cover compatible, meaning_changed and needs_context"
        ));
    }
    errors
}

pub fn validate_expressions(data: &Value, rule_ids: &HashSet<String>) -> Vec<String> {
    let Some(entries) = fields(data, "entries") else {
        return vec!["expressions: expected an entries list".into()];
    };
    let mut errors = vec![];
    if data["schema_version"] != "0.1" || entries.is_empty() {
        errors.push("expressions: expected schema_version 0.1 and nonempty entries".into());
    }
    let pattern = re(r"^EXPR-[0-9]{2}$");
    let mut seen = HashSet::new();
    let mut signals_seen = HashSet::new();
    for (index, entry) in entries.iter().enumerate() {
        let loc = format!("expressions[{}]", index + 1);
        if !entry.is_object() {
            errors.push(format!("{loc}: expected an object"));
            continue;
        }
        match entry["id"].as_str() {
            Some(id) if pattern.is_match(id) => {
                if !seen.insert(id) {
                    errors.push(format!("{loc}: duplicate id"));
                }
            }
            _ => errors.push(format!("{loc}: invalid id")),
        }
        missing(&mut errors, entry, &loc, &["preferred", "meaning"]);
        for key in ["signals", "conditions", "exceptions", "rule_ids"] {
            let Some(values) = strings(&entry[key], true) else {
                errors.push(format!("{loc}: invalid {key}"));
                continue;
            };
            let distinct: HashSet<&str> = values.iter().copied().collect();
            if distinct.len() != values.len() {
                errors.push(format!("{loc}: duplicate {key}"));
            }
            if key == "rule_ids" && values.iter().any(|v| !rule_ids.contains(*v)) {
                errors.push(format!("{loc}: unknown rule id"));
            }
            if key == "signals" {
                if values.iter().any(|v| signals_seen.contains(v)) {
                    errors.push(format!("{loc}: duplicate signal across entries"));
                }
                signals_seen.extend(values);
            }
        }
        if entry["replacement"] != "never_automatic" {
            errors.push(format!("{loc}: automatic replacement is not allowed"));
        }
        errors.extend(validate_examples(&entry["examples"], &loc));
    }
    errors
}

pub fn validate_terminology(data: &Value, rule_ids: &HashSet<String>) -> Vec<String> {
    let Some(entries) = fields(data, "entries") else {
        return vec!["terminology: expected an object with an entries list".into()];
    };
    let mut errors = vec![];
    if data["schema_version"] != "0.2" {
        errors.push("terminology: expected schema_version 0.2".into());
    }
    if entries.is_empty() {
        errors.push("terminology: entries must not be empty".into());
    }
    let pattern = re(r"^TERM-[0-9]{2}$");
    let mut seen = HashSet::new();
    for (index, term) in entries.iter().enumerate() {
        let loc = format!("terminology[{}]", index + 1);
        if !term.is_object() {
            errors.push(format!("{loc}: expected an object"));
            continue;
        }
        match term["id"].as_str() {
            Some(id) if pattern.is_match(id) => {
                if !seen.insert(id) {
                    errors.push(format!("{loc}: duplicate term id {id}"));
                }
            }
            _ => errors.push(format!("{loc}: invalid term id")),
        }
        missing(
            &mut errors,
            term,
            &loc,
            &[
                "term_a",
                "meaning_a",
                "term_b",
                "meaning_b",
                "scope",
                "status",
            ],
        );
        if term["term_a"] == term["term_b"] {
            errors.push(format!("{loc}: distinct terms required"));
        }
        if term["replacement"] != "never_automatic" {
            errors.push(format!("{loc}: automatic replacement is not allowed"));
        }
        match strings(&term["rule_ids"], false).filter(|v| !v.is_empty()) {
            None => errors.push(format!("{loc}: rule_ids must be a nonempty string list")),
            Some(refs) => {
                if refs.len() != refs.iter().copied().collect::<HashSet<_>>().len()
                    || refs.iter().any(|v| !rule_ids.contains(*v))
                {
                    errors.push(format!("{loc}: unknown or duplicate rule id"));
                }
            }
        }
        if strings(&term["exceptions"], true).is_none() {
            errors.push(format!("{loc}: exceptions must be nonempty strings"));
        }
        errors.extend(validate_examples(&term["examples"], &loc));
    }
    errors
}

fn split_lines(text: &str) -> Vec<&str> {
    let mut out = vec![];
    let mut start = 0;
    let mut chars = text.char_indices().peekable();
    while let Some((index, c)) = chars.next() {
        if matches!(
            c,
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
            out.push(&text[start..index]);
            start = index + c.len_utf8();
            if c == '\r' && chars.peek().is_some_and(|(_, c)| *c == '\n') {
                start = chars.next().unwrap().0 + 1;
            }
        }
    }
    if start < text.len() {
        out.push(&text[start..]);
    }
    out
}

pub fn without_fences(text: &str) -> String {
    let mut out = vec![];
    let mut marker = "";
    let quote = re(r"^[\s\x1c-\x1f]*>[\s\x1c-\x1f]?");
    let fence = re(r"^(`{3,}|~{3,})");
    for line in split_lines(text) {
        let candidate = quote.replace(line, "");
        let candidate = candidate.trim_start_matches(py_space);
        if marker.is_empty() {
            if let Some(m) = fence.find(candidate) {
                marker = &line[line.len() - candidate.len()..][..m.end()];
                continue;
            }
        } else {
            if candidate.starts_with(marker) && trim(&candidate[marker.len()..]).is_empty() {
                marker = "";
            }
            continue;
        }
        out.push(line);
    }
    out.join("\n")
}

// Resolve each existing prefix so a symlink followed by `..` has Path.resolve semantics.
pub fn resolve_path(path: &Path) -> PathBuf {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()
            .unwrap_or_else(|_| PathBuf::from("/"))
            .join(path)
    };
    fn visit(path: &Path, depth: usize) -> PathBuf {
        let mut resolved = PathBuf::new();
        for part in path.components() {
            match part {
                Component::ParentDir => {
                    resolved.pop();
                }
                Component::CurDir => {}
                _ => {
                    resolved.push(part.as_os_str());
                    if depth < 40
                        && let Ok(target) = fs::read_link(&resolved)
                    {
                        let destination = if target.is_absolute() {
                            target
                        } else {
                            resolved.parent().unwrap_or(Path::new("/")).join(target)
                        };
                        resolved = visit(&destination, depth + 1);
                    }
                }
            }
        }
        resolved
    }
    visit(&absolute, 0)
}

pub fn local_link_errors(root: &Path, document: &Path, text: &str) -> Result<Vec<String>, String> {
    let mut errors = vec![];
    let root = resolve_path(root);
    let name = document.file_name().unwrap_or_default().to_string_lossy();
    let links = re(r"\[[^\]\n]*\]\(([^)\n]+)\)");
    let scheme = re(r"^[A-Za-z][A-Za-z0-9+.-]*:");
    let unfenced = without_fences(text);
    for capture in links.captures_iter(&unfenced) {
        let target = trim(&capture[1]).trim_matches(['<', '>']);
        let cleaned: String = target
            .chars()
            .filter(|c| !matches!(c, '\t' | '\r' | '\n'))
            .collect();
        let cleaned = cleaned.trim_start_matches(|c: char| c <= '\u{20}');
        let has_scheme = scheme.is_match(cleaned);
        let tail = if has_scheme {
            cleaned.split_once(':').map_or(cleaned, |(_, rest)| rest)
        } else {
            cleaned
        };
        let (netloc, tail) = if let Some(rest) = tail.strip_prefix("//") {
            let end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
            (&rest[..end], &rest[end..])
        } else {
            ("", tail)
        };
        if netloc.contains('[') != netloc.contains(']') {
            return Err("Invalid IPv6 URL".into());
        }
        if netloc.contains('[') {
            let host_port = netloc.rsplit('@').next().unwrap_or(netloc);
            let (before, bracket) = host_port.split_once('[').unwrap_or((host_port, ""));
            if !before.is_empty() {
                return Err("Invalid IPv6 URL".into());
            }
            let (host, port) = bracket.split_once(']').ok_or("Invalid IPv6 URL")?;
            if !port.is_empty() && !port.starts_with(':') {
                return Err("Invalid IPv6 URL".into());
            }
            if host.starts_with(['v', 'V']) {
                if !re(r"\A[vV][a-fA-F0-9]+\..+\z").is_match(host) {
                    return Err("IPvFuture address is invalid".into());
                }
            } else {
                let ip = host.split_once('%').map_or(host, |(ip, _)| ip);
                if ip.parse::<std::net::Ipv4Addr>().is_ok() {
                    return Err("An IPv4 address cannot be in brackets".into());
                }
                if ip.parse::<std::net::Ipv6Addr>().is_err() {
                    return Err(format!(
                        "'{host}' does not appear to be an IPv4 or IPv6 address"
                    ));
                }
            }
        }
        if !netloc.is_ascii() {
            let n: String = netloc
                .chars()
                .filter(|c| !matches!(c, '@' | ':' | '#' | '?'))
                .collect();
            let folded: String = n.nfkc().collect();
            if n != folded && folded.contains(['/', '?', '#', '@', ':']) {
                return Err(format!(
                    "netloc '{netloc}' contains invalid characters under NFKC normalization"
                ));
            }
        }
        let path_part = tail.split(['?', '#']).next().unwrap_or("");
        if has_scheme || !netloc.is_empty() || path_part.is_empty() {
            continue;
        }
        let decoded = percent_encoding::percent_decode_str(path_part).decode_utf8_lossy();
        let path = resolve_path(
            &document
                .parent()
                .unwrap_or(Path::new("."))
                .join(decoded.as_ref()),
        );
        if !path.starts_with(&root) {
            errors.push(format!("{name}: link escapes package: {target}"));
        } else if !path.is_file() {
            errors.push(format!("{name}: broken local file link: {target}"));
        }
    }
    Ok(errors)
}

pub fn selected_metadata_errors(skill: &str, cff: &str, version: &str) -> Vec<String> {
    let Some(captures) = re(r"(?s)\A---\n(.*?)\n---(?:\n|$)").captures(skill) else {
        return vec!["SKILL.md: missing front matter".into()];
    };
    let front = &captures[1];
    let mut fields = std::collections::HashMap::new();
    let scalar = re(r"(?m)^([a-z][a-z-]*):[\s\x1c-\x1f]*(.*)$");
    for item in scalar.captures_iter(front) {
        fields.insert(item[1].to_string(), item[2].to_string());
    }
    let mut errors = vec![];
    if fields.get("name").map(String::as_str) != Some("dot-stk100") {
        errors.push("SKILL.md: name must be dot-stk100".into());
    }
    if !re(r"(?m)^  author:[\s\x1c-\x1f]*dotoridot[\s\x1c-\x1f]*$").is_match(front) {
        errors.push("SKILL.md: author must be dotoridot".into());
    }
    if !re(r#"(?m)^  - name:[\s\x1c-\x1f]*"dotoridot"[\s\x1c-\x1f]*$"#).is_match(cff) {
        errors.push("CITATION.cff: author name must be dotoridot".into());
    }
    let count = fields.get("description").map_or(0, |v| v.chars().count());
    if !(1..=1024).contains(&count) {
        errors.push("SKILL.md: description length outside 1..1024".into());
    }
    let escaped = regex::escape(version);
    if !re(&format!(
        r#"(?m)^  version:[\s\x1c-\x1f]*["']?{escaped}["']?[\s\x1c-\x1f]*$"#
    ))
    .is_match(front)
    {
        errors.push("SKILL.md: metadata version mismatch".into());
    }
    if !re(&format!(
        r#"(?m)^version:[\s\x1c-\x1f]*["']?{escaped}["']?[\s\x1c-\x1f]*$"#
    ))
    .is_match(cff)
    {
        errors.push("CITATION.cff: version mismatch".into());
    }
    errors
}

fn read_text(path: &Path) -> Result<String, String> {
    fs::read_to_string(path)
        .map(|s| s.replace("\r\n", "\n").replace('\r', "\n"))
        .map_err(|e| format!("{}: {e}", path.display()))
}
fn read_json(path: &Path) -> Result<Value, String> {
    serde_json::from_str(&read_text(path)?).map_err(|e| e.to_string())
}
fn collect_files(root: &Path, extension: &str) -> Vec<PathBuf> {
    walkdir::WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|entry| {
            entry.depth() != 1
                || ![".git", "target", "bin"]
                    .iter()
                    .any(|name| entry.file_name() == *name)
        })
        .filter_map(Result::ok)
        .map(|entry| entry.into_path())
        .filter(|path| path.extension().is_some_and(|ext| ext == extension))
        .collect()
}
fn ids(data: &Value, field: &str) -> HashSet<String> {
    fields(data, field)
        .into_iter()
        .flatten()
        .filter_map(|v| v["id"].as_str().map(str::to_string))
        .collect()
}

pub fn validate(root: &Path) -> (Vec<String>, Value) {
    let root = resolve_path(root);
    let mut errors = vec![];
    let native_package = root.join("Cargo.toml").is_file()
        || (resolve_path(&root.join("scripts/lint_text.py")).starts_with(&root)
            && fs::read_to_string(root.join("scripts/lint_text.py"))
                .is_ok_and(|s| s.contains("from ._native import")));
    let native_required: &[&str] = if native_package {
        &[
            "scripts/_native.py",
            "Cargo.toml",
            "Cargo.lock",
            "src/main.rs",
            "src/lib.rs",
            "src/cli.rs",
            "src/linter.rs",
            "src/evaluate.rs",
            "src/render.rs",
            "src/package.rs",
            "src/bin/lint-text.rs",
            "src/bin/evaluate-linter.rs",
            "src/bin/render-rules.rs",
            "src/bin/validate-package.rs",
        ]
    } else {
        &[]
    };
    for relative in REQUIRED.iter().chain(native_required.iter()) {
        let path = resolve_path(&root.join(relative));
        if !path.starts_with(&root) || !path.is_file() {
            errors.push(format!("missing or out-of-root required file: {relative}"));
        }
    }
    if !errors.is_empty() {
        return (errors, json!({}));
    }
    let mut counts = json!({});
    let checked: Result<(), String> = (|| {
        let rules = read_json(&root.join("rules/rules.json"))?;
        let sources = read_json(&root.join("references/sources.json"))?;
        let cases: Vec<Value> = split_lines(&read_text(&root.join("eval/seed-cases.jsonl"))?)
            .into_iter()
            .filter(|line| !trim(line).is_empty())
            .map(serde_json::from_str)
            .collect::<Result<_, _>>()
            .map_err(|e| e.to_string())?;
        errors.extend(validate_sources(&sources));
        let source_ids = ids(&sources, "sources");
        errors.extend(validate_rules(&rules, &source_ids));
        let rule_ids = ids(&rules, "rules");
        errors.extend(validate_cases(&json!(cases), &rule_ids));
        for path in collect_files(&root, "json") {
            if !resolve_path(&path).starts_with(&root) {
                errors.push(format!(
                    "JSON symlink outside package: {}",
                    path.file_name().unwrap_or_default().to_string_lossy()
                ));
                continue;
            }
            read_json(&path)?;
        }
        for path in collect_files(&root, "md") {
            if !resolve_path(&path).starts_with(&root) {
                errors.push(format!(
                    "Markdown symlink outside package: {}",
                    path.file_name().unwrap_or_default().to_string_lossy()
                ));
                continue;
            }
            errors.extend(local_link_errors(&root, &path, &read_text(&path)?)?);
        }
        if let Some(rule_list) = fields(&rules, "rules") {
            let text = read_text(&root.join("references/DOT-STK100-SPEC.md"))?;
            if render_document(&text, &json!(rule_list))? != text {
                errors.push("generated rule table is stale".into());
            }
            let version = match &rules["version"] {
                Value::String(v) => v.clone(),
                Value::Null => "".into(),
                v => v.to_string(),
            };
            errors.extend(selected_metadata_errors(
                &read_text(&root.join("SKILL.md"))?,
                &read_text(&root.join("CITATION.cff"))?,
                &version,
            ));
        }
        let terms = read_json(&root.join("references/terminology.json"))?;
        if terms["version"] != rules["version"] {
            errors.push("terminology version mismatch".into());
        }
        errors.extend(validate_terminology(&terms, &rule_ids));
        let term_ids = ids(&terms, "entries");
        let expressions = read_json(&root.join("references/preferred-expressions.json"))?;
        if expressions["version"] != rules["version"] {
            errors.push("expressions version mismatch".into());
        }
        errors.extend(validate_expressions(&expressions, &rule_ids));
        let expression_count = fields(&expressions, "entries").ok_or("'entries'")?.len();
        let families: HashSet<_> = cases.iter().filter_map(|c| c["pair_id"].as_str()).collect();
        counts = json!({"rules": rule_ids.len(), "sources": source_ids.len(), "seed_cases": cases.len(),
            "source_families": families.len(), "term_pairs": term_ids.len(), "preferred_expressions": expression_count});
        Ok(())
    })();
    if let Err(error) = checked {
        errors.push(format!("package parse/check error: {error}"));
    }
    (errors, counts)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_dictionary_types_have_diagnostics() {
        for data in [
            Value::Null,
            json!({"entries":null}),
            json!({"entries":[null]}),
        ] {
            assert!(!validate_terminology(&data, &HashSet::new()).is_empty());
            assert!(!validate_expressions(&data, &HashSet::new()).is_empty());
        }
    }

    #[test]
    fn missing_package_counts_are_empty() {
        let (errors, counts) = validate(&std::env::temp_dir().join("dot-stk100-does-not-exist"));
        assert_eq!(errors.len(), REQUIRED.len());
        assert_eq!(counts, json!({}));
    }

    #[test]
    fn fences_follow_python_splitlines_and_quote_rules() {
        assert_eq!(
            without_fences("a\r\n> ```md\r[bad](missing)\u{2028}> ```\nb\u{85}"),
            "a\nb"
        );
        assert_eq!(without_fences("~~~\nx\n~~~~\n[still fenced](bad)"), "");
        assert_eq!(
            without_fences("before\n\u{1f}> ```md\n[example](missing)\n\u{1f}> ```\nafter"),
            "before\nafter"
        );
    }

    #[test]
    fn metadata_uses_codepoints_for_description_length() {
        let skill = format!(
            "---\nname: dot-stk100\ndescription: {}\nmetadata:\n  author: dotoridot\n  version: '0.0.2'\n---\n",
            "한".repeat(1024)
        );
        assert_eq!(
            selected_metadata_errors(
                &skill,
                "version: 0.0.2\nauthors:\n  - name: \"dotoridot\"\n",
                "0.0.2"
            ),
            Vec::<String>::new()
        );
        let controls = skill.replace(": ", ":\u{1f}");
        assert_eq!(
            selected_metadata_errors(
                &controls,
                "version:\u{1f}0.0.2\nauthors:\n  - name:\u{1f}\"dotoridot\"\n",
                "0.0.2"
            ),
            Vec::<String>::new()
        );
    }

    #[cfg(unix)]
    #[test]
    fn links_resolve_symlinks_before_parent_components() {
        use std::os::unix::fs::symlink;
        let tmp = std::env::temp_dir().join(format!("dot-stk100-links-{}", std::process::id()));
        fs::create_dir_all(tmp.join("inside")).unwrap();
        fs::write(tmp.join("inside/target.md"), "ok").unwrap();
        symlink(tmp.join("inside"), tmp.join("link")).unwrap();
        assert!(
            local_link_errors(&tmp, &tmp.join("doc.md"), "[ok](link/target.md)")
                .unwrap()
                .is_empty()
        );
        assert!(
            local_link_errors(&tmp, &tmp.join("doc.md"), "[bad](../outside.md)").unwrap()[0]
                .contains("link escapes package")
        );
        assert!(
            local_link_errors(&tmp, &tmp.join("doc.md"), "[missing](%6dissing.md)").unwrap()[0]
                .contains("broken local file link")
        );
        fs::remove_dir_all(tmp).unwrap();
    }
}
