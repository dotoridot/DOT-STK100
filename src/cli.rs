use crate::{evaluate, linter, package, render};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::HashSet,
    fs,
    io::{self, Read},
    path::{Path, PathBuf},
};

fn read(path: &Path) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))
}
fn data(path: &Path) -> Result<Value, String> {
    serde_json::from_str(&read(path)?).map_err(|e| e.to_string())
}
fn string(v: &Value) -> Result<&str, String> {
    v.as_str().ok_or_else(|| "expected a string".into())
}
fn ids(v: &Value) -> Result<HashSet<String>, String> {
    v.as_array()
        .ok_or("expected a string list")?
        .iter()
        .map(|v| Ok(string(v)?.to_owned()))
        .collect()
}
fn root() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    exe.ancestors()
        .skip(1)
        .find(|p| p.join("rules/rules.json").is_file())
        .map(Path::to_path_buf)
        .ok_or_else(|| "package root not found beside executable; pass --root".into())
}
fn normalized(text: String) -> String {
    text.replace("\r\n", "\n").replace('\r', "\n")
}

fn bridge(root: &Path, op: &str) -> Result<Value, String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|e| e.to_string())?;
    let a: Vec<Value> = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    let get = |i: usize| a.get(i).ok_or_else(|| "missing bridge argument".to_owned());
    Ok(match op {
        "review" => linter::review(
            root,
            match get(0)? {
                Value::Null => None,
                Value::String(text) => Some(text.as_str()),
                _ => return Err("source must be a string or null".into()),
            },
            string(get(1)?)?,
            a.get(2).filter(|v| !v.is_null()).cloned(),
        )?,
        "evaluate" => evaluate::evaluate(root, get(0)?)?,
        "review_many" => {
            linter::review_many(root, get(0)?, a.get(1).filter(|v| !v.is_null()).cloned())?
        }
        "protected" => {
            serde_json::to_value(linter::protected(string(get(0)?)?)).map_err(|e| e.to_string())?
        }
        "mask" => {
            let t: Vec<linter::Token> =
                serde_json::from_value(get(1)?.clone()).map_err(|e| e.to_string())?;
            json!(linter::mask(string(get(0)?)?, &t))
        }
        "tokens" => serde_json::to_value(linter::tokens(
            string(get(0)?)?,
            string(get(1)?)?,
            string(get(2)?)?,
        )?)
        .map_err(|e| e.to_string())?,
        "location" => {
            let token: Option<linter::Token> =
                serde_json::from_value(get(1)?.clone()).map_err(|e| e.to_string())?;
            linter::location(string(get(0)?)?, token.as_ref())
        }
        "validate_term_config" => {
            linter::validate_term_config(get(0)?)?;
            Value::Null
        }
        "cell" => json!(render::cell(string(get(0)?)?)),
        "render_table" => json!(render::render_table(get(0)?)?),
        "render_document" => json!(render::render_document(string(get(0)?)?, get(1)?)?),
        "validate" => {
            let (errors, counts) = package::validate(Path::new(string(get(0)?)?));
            json!([errors, counts])
        }
        "validate_sources" => json!(package::validate_sources(get(0)?)),
        "validate_rules" => json!(package::validate_rules(get(0)?, &ids(get(1)?)?)),
        "validate_cases" => json!(package::validate_cases(get(0)?, &ids(get(1)?)?)),
        "validate_examples" => json!(package::validate_examples(get(0)?, string(get(1)?)?)),
        "validate_terminology" => json!(package::validate_terminology(get(0)?, &ids(get(1)?)?)),
        "validate_expressions" => json!(package::validate_expressions(get(0)?, &ids(get(1)?)?)),
        "without_fences" => json!(package::without_fences(string(get(0)?)?)),
        "local_link_errors" => json!(package::local_link_errors(
            Path::new(string(get(0)?)?),
            Path::new(string(get(1)?)?),
            string(get(2)?)?
        )?),
        "selected_metadata_errors" => json!(package::selected_metadata_errors(
            string(get(0)?)?,
            string(get(1)?)?,
            string(get(2)?)?
        )),
        "nonempty" => json!(package::nonempty(get(0)?)),
        _ => return Err(format!("unknown bridge operation: {op}")),
    })
}

fn help() {
    println!(
        "DOT-STK100 offline report-only tools\nUsage: dot-stk100 <lint|lint-batch|evaluate|render|validate> [options]\n  lint --candidate PATH [--source PATH] [--terms PATH] [--format json]\n  lint-batch --cases PATH [--terms PATH]\n  evaluate [--cases PATH | --terminology-examples]\n  render [--check]\n  validate\nAll commands accept --root PATH. Build explicitly with cargo build --release --locked."
    );
}

fn execute(args: &[String]) -> Result<i32, String> {
    let Some(command) = args.first().map(String::as_str) else {
        return Err("expected lint, evaluate, render, validate or bridge".into());
    };
    if command == "--help" || command == "-h" {
        help();
        return Ok(0);
    }
    let mut package_root = None;
    let mut source = None;
    let mut candidate = None;
    let mut terms = None;
    let mut cases = None;
    let mut terminology = false;
    let mut check = false;
    let mut operation = None;
    let mut index = 1;
    while index < args.len() {
        let raw = &args[index];
        let (arg, assigned) = if raw.starts_with("--") {
            raw.split_once('=')
                .map_or((raw.as_str(), None), |(key, value)| (key, Some(value)))
        } else {
            (raw.as_str(), None)
        };
        match arg {
            "--root" | "--source" | "--candidate" | "--terms" | "--cases" | "--format" => {
                let option = arg;
                let val = if let Some(value) = assigned {
                    value
                } else {
                    index += 1;
                    let value = args
                        .get(index)
                        .ok_or_else(|| format!("{option} requires a value"))?;
                    if value.starts_with('-') {
                        return Err(format!("{option} requires a value"));
                    }
                    value.as_str()
                };
                match option {
                    "--root" => package_root = Some(PathBuf::from(val)),
                    "--source" if command == "lint" => source = Some(PathBuf::from(val)),
                    "--candidate" if command == "lint" => candidate = Some(PathBuf::from(val)),
                    "--terms" if matches!(command, "lint" | "lint-batch") => {
                        terms = Some(PathBuf::from(val))
                    }
                    "--format" if command == "lint" && val == "json" => {}
                    "--cases" if matches!(command, "evaluate" | "lint-batch") => {
                        cases = Some(PathBuf::from(val))
                    }
                    _ => return Err(format!("unsupported option/value: {option} {val}")),
                }
            }
            "--terminology-examples" if command == "evaluate" && assigned.is_none() => {
                terminology = true
            }
            "--check" if command == "render" && assigned.is_none() => check = true,
            "--help" | "-h" if assigned.is_none() => {
                help();
                return Ok(0);
            }
            _ if command == "bridge" && operation.is_none() && assigned.is_none() => {
                operation = Some(arg)
            }
            _ => return Err(format!("unrecognized argument: {arg}")),
        }
        index += 1;
    }
    let root = package_root.map(Ok).unwrap_or_else(root)?;
    match command {
        "lint" => {
            let candidate = read(&candidate.ok_or("--candidate is required")?)?;
            let source = source.map(|p| read(&p)).transpose()?;
            let terms = terms.map(|p| data(&p)).transpose()?;
            println!(
                "{}",
                serde_json::to_string_pretty(&linter::review(
                    &root,
                    source.as_deref(),
                    &candidate,
                    terms
                )?)
                .map_err(|e| e.to_string())?
            );
        }
        "lint-batch" => {
            let input = read(&cases.ok_or("--cases is required")?)?;
            let cases: Vec<Value> = input
                .lines()
                .filter(|line| !line.trim().is_empty())
                .map(|line| serde_json::from_str(line).map_err(|e| e.to_string()))
                .collect::<Result<_, _>>()?;
            let terms = terms.map(|p| data(&p)).transpose()?;
            println!(
                "{}",
                serde_json::to_string_pretty(&linter::review_many(&root, &json!(cases), terms)?)
                    .map_err(|e| e.to_string())?
            );
        }
        "evaluate" => {
            if terminology && cases.is_some() {
                return Err("--cases and --terminology-examples are mutually exclusive".into());
            }
            let raw = fs::read(if terminology {
                root.join("references/terminology.json")
            } else {
                cases.unwrap_or_else(|| root.join("eval/seed-cases.jsonl"))
            })
            .map_err(|e| e.to_string())?;
            let cases: Value = if terminology {
                let terms: Value = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
                let mut cases = vec![];
                for entry in terms["entries"]
                    .as_array()
                    .ok_or("expected terminology entries")?
                {
                    for (i, example) in entry["examples"]
                        .as_array()
                        .ok_or("expected examples")?
                        .iter()
                        .enumerate()
                    {
                        let mut example = example.clone();
                        if !example.is_object() {
                            return Err("example must be an object".into());
                        }
                        example["case_id"] = json!(format!("{}-{}", string(&entry["id"])?, i + 1));
                        example["pair_id"] = entry["id"].clone();
                        cases.push(example);
                    }
                }
                json!(cases)
            } else {
                let text = std::str::from_utf8(&raw).map_err(|e| e.to_string())?;
                // Python splitlines includes non-ASCII line boundaries.
                let rows: Result<Vec<Value>, _> = text
                    .split([
                        '\n', '\r', '\u{000b}', '\u{000c}', '\u{001c}', '\u{001d}', '\u{001e}',
                        '\u{0085}', '\u{2028}', '\u{2029}',
                    ])
                    .filter(|s| !s.trim().is_empty())
                    .map(serde_json::from_str)
                    .collect();
                json!(rows.map_err(|e| e.to_string())?)
            };
            let cases_array = cases.as_array().ok_or("expected cases array")?;
            let mut seen = HashSet::new();
            if cases_array.is_empty()
                || cases_array
                    .iter()
                    .any(|c| !c["case_id"].is_string() || !seen.insert(c["case_id"].clone()))
            {
                return Err("empty or duplicate cases".into());
            }
            if cases_array.iter().any(|c| {
                c["label_status"] != "ai_draft_not_human_adjudicated"
                    || c["split"] != "development_only"
            }) {
                return Err("this evaluator accepts only provisional development data".into());
            }
            let (mut result, spec_version) = evaluate::evaluate_for_cli(
                &root,
                &cases,
                if terminology {
                    Some(raw.as_slice())
                } else {
                    None
                },
            )?;
            result["dataset_sha256"] = json!(format!("{:x}", Sha256::digest(&raw)));
            result["implementation_sha256"] = json!(format!(
                "{:x}",
                Sha256::digest(
                    fs::read(std::env::current_exe().map_err(|e| e.to_string())?)
                        .map_err(|e| e.to_string())?
                )
            ));
            result["implementation_kind"] = json!("rust_executable_sha256");
            result["evaluation_schema_version"] = json!("0.2");
            result["spec_version"] = spec_version;
            println!(
                "{}",
                serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?
            );
        }
        "render" => {
            let rules = data(&root.join("rules/rules.json"))?;
            let list = rules["rules"]
                .as_array()
                .filter(|v| !v.is_empty())
                .ok_or("rules must be a nonempty list")?;
            let path = root.join("references/DOT-STK100-SPEC.md");
            let original = normalized(read(&path)?);
            let rendered = render::render_document(&original, &rules["rules"])?;
            if check {
                if rendered != original {
                    eprintln!("FAIL: generated rule table is stale; run scripts/render_rules.py");
                    return Ok(1);
                }
                println!(
                    "PASS: generated rule table matches {} rules (structure only)",
                    list.len()
                );
            } else {
                fs::write(path, rendered).map_err(|e| e.to_string())?;
                println!("Rendered {} rules", list.len());
            }
        }
        "validate" => {
            let (errors, counts) = package::validate(&root);
            if !errors.is_empty() {
                for error in errors {
                    eprintln!("FAIL: {error}");
                }
                return Ok(1);
            }
            println!("PASS: package structure and references");
            // Python CLI prints sorted count keys.
            let sorted: std::collections::BTreeMap<_, _> =
                counts.as_object().ok_or("invalid counts")?.iter().collect();
            println!(
                "{}",
                serde_json::to_string(&sorted).map_err(|e| e.to_string())?
            );
            println!(
                "NOT CHECKED: semantic labels, facts, readability, host compatibility or real-world effectiveness"
            );
        }
        "bridge" => println!(
            "{}",
            bridge(&root, operation.ok_or("bridge operation required")?)?
        ),
        _ => return Err(format!("unknown command: {command}")),
    }
    Ok(0)
}

pub fn run(args: Vec<String>) -> i32 {
    match execute(&args) {
        Ok(code) => code,
        Err(e) => {
            eprintln!("ERROR: {e}");
            2
        }
    }
}
