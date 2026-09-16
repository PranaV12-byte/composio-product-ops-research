"""Small, dependency-free research trigger for the Composio take-home."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).parent
DATASET = ROOT / "data" / "apps.json"
MATERIAL_FIELDS = {
    "auth_methods",
    "access_status",
    "api_types",
    "api_breadth",
    "read_capability",
    "write_capability",
    "event_capability",
    "mcp_status",
    "composio_status",
    "buildability",
}
ACCESS = {"self_serve_free", "self_serve_trial", "paid_plan", "admin_approval", "partner_gated", "unknown"}
AUTH = {"oauth2", "oauth2_1", "api_key", "bearer_token", "basic_auth", "personal_access_token", "service_account", "digest_auth", "database_credentials", "none", "other", "unknown"}
API_TYPES = {"rest", "graphql", "soap", "rpc", "websocket", "webhook", "sse", "cli", "sdk", "database_protocol", "other", "none", "unknown"}
API_BREADTH = {"broad", "moderate", "narrow", "none", "unknown"}
TRI_STATE = {"yes", "no", "unknown"}
EVENTS = {"webhook", "polling", "streaming", "none", "unknown"}
MCP = {"official", "third_party", "none_found", "unknown"}
COMPOSIO = {"existing_toolkit", "not_found", "unknown"}
BUILDABILITY = {"ready_now", "buildable_with_caveat", "product_ops_required", "not_viable", "unknown"}
CONFIDENCE = {"high", "medium", "low"}
CATEGORIES = {
    "CRM and Sales",
    "Support and Helpdesk",
    "Communications and Messaging",
    "Marketing, Ads, Email and Social",
    "Ecommerce",
    "Data, SEO and Scraping",
    "Developer, Infra and Data platforms",
    "Productivity and Project Management",
    "Finance and Fintech",
    "AI, Research and Media-native",
}
SOURCE_TYPES = {"official_docs", "official_help", "official_pricing", "official_github", "secondary"}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "integer"},
        "app": {"type": "string"},
        "category": {"type": "string"},
        "description": {"type": "string"},
        "auth_methods": {"type": "array", "items": {"type": "string", "enum": sorted(AUTH)}},
        "access_status": {
            "type": "string",
            "enum": [
                "self_serve_free", "self_serve_trial", "paid_plan",
                "admin_approval", "partner_gated", "unknown",
            ],
        },
        "access_details": {"type": "string"},
        "api_types": {"type": "array", "items": {"type": "string", "enum": sorted(API_TYPES)}},
        "api_breadth": {
            "type": "string",
            "enum": ["broad", "moderate", "narrow", "none", "unknown"],
        },
        "read_capability": {"type": "string", "enum": ["yes", "no", "unknown"]},
        "write_capability": {"type": "string", "enum": ["yes", "no", "unknown"]},
        "event_capability": {
            "type": "string",
            "enum": ["webhook", "polling", "streaming", "none", "unknown"],
        },
        "mcp_status": {
            "type": "string",
            "enum": ["official", "third_party", "none_found", "unknown"],
        },
        "mcp_evidence_url": {"type": ["string", "null"]},
        "composio_status": {
            "type": "string",
            "enum": ["existing_toolkit", "not_found", "unknown"],
        },
        "buildability": {
            "type": "string",
            "enum": [
                "ready_now", "buildable_with_caveat", "product_ops_required",
                "not_viable", "unknown",
            ],
        },
        "primary_blocker": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "fields": {"type": "array", "items": {"type": "string", "enum": sorted(MATERIAL_FIELDS)}},
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "source_type": {"type": "string", "enum": sorted(SOURCE_TYPES)},
                    "accessed_at": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["fields", "url", "title", "source_type", "accessed_at", "note"],
            },
        },
        "research_notes": {"type": "string"},
    },
    "required": [
        "id", "app", "category", "description", "auth_methods", "access_status", "access_details",
        "api_types", "api_breadth", "read_capability", "write_capability",
        "event_capability", "mcp_status", "mcp_evidence_url", "composio_status",
        "buildability", "primary_blocker", "confidence", "evidence", "research_notes",
    ],
}


def validate_dataset() -> int:
    records = json.loads(DATASET.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    required = set(SCHEMA["required"])
    if len(records) != 100:
        errors.append(f"Expected 100 apps, found {len(records)}")
    ids = [record.get("id") for record in records]
    if ids != list(range(1, 101)):
        errors.append("App IDs must be unique and ordered from 1 through 100")
    if {record.get("category") for record in records} != CATEGORIES:
        errors.append("Dataset categories do not match the supplied assignment")
    for record in records:
        name = record.get("app", "Unknown app")
        missing_keys = required - set(record)
        if missing_keys:
            errors.append(f"{name}: missing fields {sorted(missing_keys)}")
            continue
        enum_checks = {
            "access_status": ACCESS,
            "api_breadth": API_BREADTH,
            "read_capability": TRI_STATE,
            "write_capability": TRI_STATE,
            "event_capability": EVENTS,
            "mcp_status": MCP,
            "composio_status": COMPOSIO,
            "buildability": BUILDABILITY,
            "confidence": CONFIDENCE,
        }
        for field, allowed in enum_checks.items():
            if record[field] not in allowed:
                errors.append(f"{name}: invalid {field} value {record[field]!r}")
        if not set(record["auth_methods"]).issubset(AUTH):
            errors.append(f"{name}: non-canonical authentication value")
        if not set(record["api_types"]).issubset(API_TYPES):
            errors.append(f"{name}: non-canonical API type")
        if record["category"] not in CATEGORIES:
            errors.append(f"{name}: invalid category")
        covered = {
            field
            for evidence in record.get("evidence", [])
            for field in evidence.get("fields", [])
        }
        missing = MATERIAL_FIELDS - covered
        if missing:
            errors.append(f"{name}: missing evidence for {sorted(missing)}")
        for evidence in record.get("evidence", []):
            if not str(evidence.get("url", "")).startswith(("http://", "https://")):
                errors.append(f"{name}: malformed evidence URL")
            if not evidence.get("accessed_at"):
                errors.append(f"{name}: evidence is missing accessed_at")
            if evidence.get("source_type") not in SOURCE_TYPES:
                errors.append(f"{name}: invalid evidence source type")
        if record["mcp_status"] in {"official", "third_party"} and not record.get("mcp_evidence_url"):
            errors.append(f"{name}: reported MCP is missing an evidence URL")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    evidence_count = sum(len(record.get("evidence", [])) for record in records)
    print(f"Valid: 100 apps, 10 categories, {evidence_count} evidence entries")
    return 0


def extract_text(response: dict) -> str:
    for item in response.get("output", []):
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content["text"]
    raise RuntimeError("The model returned no structured output")


def research(app: str, model: str) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY before running live research")

    records = json.loads(DATASET.read_text(encoding="utf-8-sig"))
    seed = next((record for record in records if record["app"].casefold() == app.casefold()), None)
    if not seed:
        raise RuntimeError(f"{app!r} is not in the supplied 100-app research set")

    prompt = f"""Research this supplied app for an AI-agent integration readiness decision:
- id: {seed['id']}
- app: {seed['app']}
- category: {seed['category']}
- research date: {date.today().isoformat()}

Use current official developer documentation, official help, official pricing, and
official source repositories as primary evidence. Do not infer self-service access
from the existence of API docs. Check authentication, access gates, API breadth,
read/write/event capability, official MCP availability, current Composio toolkit
coverage, buildability, and the primary blocker. Preserve unknown when evidence is
insufficient. Keep the supplied id, app name, and category unchanged. Map every
material field to evidence and include the access date. Return only the requested JSON.
"""
    payload = {
        "model": model,
        "input": prompt,
        "tools": [{"type": "web_search"}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "integration_readiness",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(extract_text(json.load(response)))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Research request failed: HTTP {error.code}: {detail}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true", help="Validate the bundled dataset")
    group.add_argument("--app", help="Research one app using live web search")
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    if args.validate:
        return validate_dataset()

    try:
        result = research(args.app, args.model)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
