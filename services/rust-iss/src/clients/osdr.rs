use chrono::{DateTime, NaiveDateTime, TimeZone, Utc};
use serde_json::Value;
pub fn normalize(json: Value) -> Vec<Value> {
    if let Some(a) = json.as_array() {
        return a.clone();
    }
    for key in ["items", "results"] {
        if let Some(a) = json.get(key).and_then(Value::as_array) {
            return a.clone();
        }
    }
    if let Some(map) = json.as_object() {
        let list: Vec<_> = map
            .iter()
            .filter(|(k, v)| k.starts_with("OSD-") && v.is_object())
            .map(|(k, v)| {
                let mut v = v.clone();
                v["dataset_id"] = Value::String(k.clone());
                v
            })
            .collect();
        if !list.is_empty() {
            return list;
        }
    }
    vec![json]
}
pub fn pick(v: &Value, keys: &[&str]) -> Option<String> {
    keys.iter().find_map(|k| match &v[*k] {
        Value::String(s) if !s.is_empty() => Some(s.clone()),
        Value::Number(n) => Some(n.to_string()),
        _ => None,
    })
}
pub fn timestamp(v: &Value) -> Option<DateTime<Utc>> {
    if let Some(n) = v.as_i64() {
        return Utc.timestamp_opt(n, 0).single();
    }
    let s = v.as_str()?;
    s.parse::<DateTime<Utc>>().ok().or_else(|| {
        NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S")
            .ok()
            .map(|t| Utc.from_utc_datetime(&t))
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn dictionary_business_key() {
        let v = normalize(json!({"OSD-1":{"title":"Study"}}));
        assert_eq!(v[0]["dataset_id"], "OSD-1");
    }
    #[test]
    fn invalid_date_is_not_now() {
        assert!(timestamp(&json!(i64::MAX)).is_none());
    }
}
