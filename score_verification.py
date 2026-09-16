"""Reproduce the field-level verification scores shown in the case study."""

from __future__ import annotations

import json
from pathlib import Path


ARTIFACT = Path(__file__).parent / "data" / "verification_sample.json"
AUTH_ALIASES = {
    "oauth 2.0": "oauth2",
    "api key": "api_key",
    "bearer token": "bearer_token",
}
API_ALIASES = {
    "rest": "rest",
    "rest api": "rest",
    "graphql": "graphql",
    "webhooks": "webhook",
    "mongodb wire protocol": "database_protocol",
}


def comparable(value):
    return sorted(set(value)) if isinstance(value, list) else value


def normalize_aliases(field: str, value):
    if not isinstance(value, list):
        return value
    aliases = AUTH_ALIASES if field == "auth_methods" else API_ALIASES
    return sorted({aliases.get(str(item).lower(), str(item).lower()) for item in value})


def score(records: list[dict], fields: list[str], candidate: str, normalize: bool = False):
    matches = 0
    per_field = {}
    for field in fields:
        field_matches = 0
        for record in records:
            actual = record[candidate][field]
            expected = record["verified"][field]
            if normalize and field in {"auth_methods", "api_types"}:
                actual = normalize_aliases(field, actual)
                expected = comparable(expected)
            else:
                actual = comparable(actual)
                expected = comparable(expected)
            field_matches += actual == expected
        per_field[field] = field_matches
        matches += field_matches
    checks = len(records) * len(fields)
    return matches, checks, per_field


def main() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8-sig"))
    records = artifact["records"]
    fields = artifact["comparison_fields"]
    categories = {}
    for record in records:
        categories[record["category"]] = categories.get(record["category"], 0) + 1
    if len(records) != 20 or len(categories) != 10 or set(categories.values()) != {2}:
        raise SystemExit("Verification sample must contain two apps from each category")

    for label, candidate, normalize in (
        ("First pass exact", "first_pass", False),
        ("First pass alias-normalized", "first_pass", True),
        ("Second pass exact", "second_pass", False),
        ("Final correction completeness", "final", False),
    ):
        matches, checks, per_field = score(records, fields, candidate, normalize)
        print(f"{label}: {matches}/{checks} = {matches / checks:.1%}")
        if candidate == "second_pass":
            print("Second-pass matches by field:")
            for field in fields:
                print(f"  {field}: {per_field[field]}/{len(records)}")


if __name__ == "__main__":
    main()
