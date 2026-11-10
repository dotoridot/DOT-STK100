use serde_json::Value;

pub const START: &str = "<!-- BEGIN GENERATED RULES -->";
pub const END: &str = "<!-- END GENERATED RULES -->";

pub fn cell(value: &str) -> String {
    value
        .replace('|', "&#124;")
        .replace("\r\n", "\n")
        .replace('\n', "<br>")
}

pub fn render_table(rules: &Value) -> Result<String, String> {
    let rules = rules.as_array().ok_or("rules must be a list")?;
    let mut rows = vec![
        "| ID | 강도 | 영역·제목 | 요구 사항 |".to_string(),
        "|---|---|---|---|".to_string(),
    ];
    for rule in rules {
        let fields = ["id", "level", "section", "title", "requirement"];
        if !rule.is_object() || fields.iter().any(|key| !rule[*key].is_string()) {
            return Err("Rule table fields must be strings".into());
        }
        let values = [
            rule["id"].as_str().unwrap().to_string(),
            rule["level"].as_str().unwrap().to_string(),
            format!(
                "{} — {}",
                rule["section"].as_str().unwrap(),
                rule["title"].as_str().unwrap()
            ),
            rule["requirement"].as_str().unwrap().to_string(),
        ];
        rows.push(format!(
            "| {} |",
            values
                .iter()
                .map(|v| cell(v))
                .collect::<Vec<_>>()
                .join(" | ")
        ));
    }
    Ok(rows.join("\n"))
}

pub fn render_document(text: &str, rules: &Value) -> Result<String, String> {
    if text.matches(START).count() != 1 || text.matches(END).count() != 1 {
        return Err("Document must contain exactly one start/end marker pair".into());
    }
    let start = text.find(START).unwrap() + START.len();
    let end = text.find(END).unwrap();
    if start > end {
        return Err("Generated table markers are out of order".into());
    }
    Ok(format!(
        "{}\n\n{}\n\n{}",
        &text[..start],
        render_table(rules)?,
        &text[end..]
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn render_preserves_outside_bytes_and_escapes_cells() {
        let rules = json!([{"id":"A", "level":"MUST", "section":"s", "title":"t", "requirement":"A|B\r\nC\rD"}]);
        let original = format!("한글\r\n{START}\nold\n{END}\r\nsuffix");
        let rendered = render_document(&original, &rules).unwrap();
        assert!(rendered.starts_with("한글\r\n"));
        assert!(rendered.ends_with("\r\nsuffix"));
        assert!(rendered.contains("A&#124;B<br>C\rD"));
        assert_eq!(render_document(&rendered, &rules).unwrap(), rendered);
    }

    #[test]
    fn reject_malformed_markers_and_fields() {
        for text in [
            "missing".to_string(),
            format!("{START}{START}{END}"),
            format!("{END}{START}"),
        ] {
            assert!(render_document(&text, &json!([])).is_err());
        }
        assert_eq!(
            render_table(&json!([{}])).unwrap_err(),
            "Rule table fields must be strings"
        );
    }
}
