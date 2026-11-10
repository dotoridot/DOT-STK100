use crate::{evaluate, linter};
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
fn root() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    exe.ancestors()
        .skip(1)
        .find(|p| p.join("rules/rules.json").is_file())
        .map(Path::to_path_buf)
        .ok_or_else(|| "package root not found beside executable; pass --root".into())
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
            get(0)?.as_str(),
            string(get(1)?)?,
            a.get(2).filter(|v| !v.is_null()).cloned(),
        )?,
        "evaluate" => evaluate::evaluate(root, get(0)?)?,
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
        _ => return Err(format!("unknown bridge operation: {op}")),
    })
}

fn execute(args: &[String]) -> Result<i32, String> {
    let Some(command) = args.first().map(String::as_str) else {
        return Err("expected lint, evaluate or bridge".into());
    };
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!(
            "DOT-STK100 offline report-only tools\nUsage: dot-stk100 <lint|evaluate> [options]\n  lint --candidate PATH [--source PATH] [--terms PATH] [--format json]\n  evaluate [--cases PATH | --terminology-examples]\nAll commands accept --root PATH. Build explicitly with cargo build --release --locked."
        );
        return Ok(0);
    }
    let mut package_root = None;
    let mut source = None;
    let mut candidate = None;
    let mut terms = None;
    let mut cases = None;
    let mut terminology = false;
    let mut operation = None;
    let mut index = 1;
    while index < args.len() {
        let arg = &args[index];
        match arg.as_str() {
            "--root" | "--source" | "--candidate" | "--terms" | "--cases" | "--format" => {
                let option = arg.as_str();
                index += 1;
                let val = args
                    .get(index)
                    .ok_or_else(|| format!("{option} requires a value"))?;
                match option {
                    "--root" => package_root = Some(PathBuf::from(val)),
                    "--source" if command == "lint" => source = Some(PathBuf::from(val)),
                    "--candidate" if command == "lint" => candidate = Some(PathBuf::from(val)),
                    "--terms" if command == "lint" => terms = Some(PathBuf::from(val)),
                    "--format" if command == "lint" && val == "json" => {}
                    "--cases" if command == "evaluate" => cases = Some(PathBuf::from(val)),
                    _ => return Err(format!("unsupported option/value: {option} {val}")),
                }
            }
            "--terminology-examples" if command == "evaluate" => terminology = true,
            _ if command == "bridge" && operation.is_none() => operation = Some(arg.as_str()),
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
            let mut result = evaluate::evaluate(&root, &cases)?;
            result["dataset_sha256"] = json!(format!("{:x}", Sha256::digest(&raw)));
            result["implementation_sha256"] = json!(format!(
                "{:x}",
                Sha256::digest(
                    fs::read(std::env::current_exe().map_err(|e| e.to_string())?)
                        .map_err(|e| e.to_string())?
                )
            ));
            result["implementation_kind"] = json!("rust_executable_sha256");
            result["spec_version"] = data(&root.join("rules/rules.json"))?["version"].clone();
            println!(
                "{}",
                serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?
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
