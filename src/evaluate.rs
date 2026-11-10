use crate::linter::ReviewContext;
use serde_json::{Value, json};
use std::collections::{BTreeSet, HashSet};
use std::path::Path;

pub fn evaluate(root: &Path, cases: &Value) -> Result<Value, String> {
    let cases = cases.as_array().ok_or("cases must be an array")?;
    let (mut tp, mut fp, mut tn, mut fn_count, mut needs_context) = (0, 0, 0, 0, 0);
    let mut rows = Vec::new();
    let mut config_hashes = Value::Null;
    let mut families = HashSet::new();
    let mut context: Option<Result<ReviewContext, String>> = None;
    for case in cases {
        let source = match case.get("source") {
            Some(Value::Null) => None,
            Some(Value::String(s)) => Some(s.as_str()),
            _ => return Err("missing or invalid source".into()),
        };
        let candidate = case
            .get("candidate")
            .and_then(Value::as_str)
            .ok_or("missing or invalid candidate")?;
        let context = context.get_or_insert_with(|| ReviewContext::new(root, None));
        let result = context
            .as_ref()
            .map_err(Clone::clone)?
            .review(source, candidate)?;
        config_hashes = result["config_hashes"].clone();
        let findings = result["findings"].as_array().ok_or("invalid findings")?;
        let warned = !findings.is_empty();
        let label = case
            .get("expected_review")
            .and_then(Value::as_str)
            .ok_or("missing expected_review")?;
        let outcome = match label {
            "needs_context" => {
                needs_context += 1;
                "excluded_needs_context"
            }
            "meaning_changed" if warned => {
                tp += 1;
                "tp"
            }
            "meaning_changed" => {
                fn_count += 1;
                "fn"
            }
            "compatible" if warned => {
                fp += 1;
                "fp"
            }
            "compatible" => {
                tn += 1;
                "tn"
            }
            _ => return Err("unknown reference label".into()),
        };
        let checks: BTreeSet<&str> = findings
            .iter()
            .filter_map(|f| f["check"].as_str())
            .collect();
        let case_id = case.get("case_id").ok_or("missing case_id")?;
        let pair_id = case.get("pair_id").ok_or("missing pair_id")?;
        families.insert(pair_id.to_string());
        rows.push(json!({ "case_id": case_id, "pair_id": pair_id, "provisional_label": label, "warning_count": findings.len(), "checks": checks, "triage_outcome": outcome }));
    }
    let ratio = |a: u64, b: u64| {
        if b == 0 {
            Value::Null
        } else {
            json!(a as f64 / b as f64)
        }
    };
    Ok(
        json!({ "evaluation_kind": "development_warning_triage_against_ai_draft_labels", "human_validated": false, "config_hashes": config_hashes, "unit": "one_candidate_document_any_warning", "case_count": cases.len(), "source_family_count": families.len(), "confusion_matrix_provisional": { "tp": tp, "fp": fp, "tn": tn, "fn": fn_count }, "excluded_needs_context": needs_context, "provisional_precision": ratio(tp, tp+fp), "provisional_recall": ratio(tp, tp+fn_count), "provisional_false_positive_rate": ratio(fp, fp+tn), "provisional_false_negative_rate": ratio(fn_count, fn_count+tp), "human_precision": null, "human_recall": null, "notice": "AI 초안 라벨 기준의 경고 발생 집계다. 경고의 타당성, 의미 판정 성능, 일반 정확도와 사람 평가가 아니다. 관련 없는 경고도 any-warning으로 센다. 같은 pair_id는 독립 표본이 아니다.", "cases": rows }),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn empty_evaluation_keeps_unknown_rates() {
        let result = evaluate(Path::new("."), &json!([])).unwrap();
        assert_eq!(result["provisional_precision"], Value::Null);
        assert_eq!(result["config_hashes"], Value::Null);
        assert_eq!(result["human_precision"], Value::Null);
        assert_eq!(result["case_count"], 0);
    }
}
