"""Validate an assessment and derive all report views from its scope ledger.

No connector calls or rendering live here. Unknown scope and incomplete checks
remain explicit; findings and actions cannot refer to unrecorded evidence.
"""

import csv
import math
import re
import runpy
from collections import Counter
from datetime import datetime
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

PROFILES = {
    "privacy": "Personal data handling",
    "hipaa": "HIPAA information handling",
    "security": "Security and governance evidence",
    "cui": "CUI handling",
    "pci": "Cardholder data handling",
    "dora": "Operational resilience documentation",
    "export": "Export-controlled content screening",
    "ai": "AI governance evidence",
    "accessibility": "Document accessibility",
    "sensitive-content": "Sensitive content review",
    "sharing": "Sharing arrangements",
    "retention": "Retention policy review",
    "storage": "Storage capacity review",
    "duplicates": "Duplicate review",
    "contracts": "Contract discovery",
    "invoices": "Invoice organization",
    "activity": "File activity digest",
    "naming": "Naming changes",
    "offboarding": "Content handover",
    "inbox": "Inbox folder filing",
    "redaction": "Redaction review",
}
CHECK_STATES = (
    "checked",
    "partial",
    "skipped",
    "failed",
    "not_attempted",
    "not_applicable",
)
ACTION_STATES = ("proposed", "approved", "completed", "skipped", "failed")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
INVENTORY_MODES = ("embedded", "compact", "companion", "omitted_by_request")
PRIORITIES = ("critical", "high", "medium", "low", "info")
CHECK_KINDS = ("content", "metadata")
DELIVERY_STATUSES = ("unverified", "size_verified", "download_verified")
TEMPLATE_VERSION_LEGACY = "1.0"
TEMPLATE_VERSION = "2.0"


def is_new_mode(data) -> bool:
    return "report_mode" in data


def inventory_mode(data) -> str:
    """Return the inventory mode without validating; legacy records embed."""
    if is_new_mode(data):
        return data["report_mode"]["inventory"]
    return "embedded"


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be non-empty text")
    return value


def _fields(value, allowed, where):
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    unknown = set(value) - set(allowed.split())
    if unknown:
        raise ValueError(f"unknown {where} fields: " + ", ".join(sorted(unknown)))


def _optional_texts(record, keys, where):
    for key in keys.split():
        if key in record:
            _text(record[key], where + "." + key)


def _texts(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{where} must be {'a non-empty' if nonempty else 'a'} list")
    for item in value:
        _text(item, where)
    return value


def _records(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{where} must be a list of records")
    result = {}
    for record in value:
        if not isinstance(record, dict):
            raise ValueError(f"{where} must contain objects")
        identifier = _text(record.get("id"), where + ".id")
        if not _ID.fullmatch(identifier) or identifier in result:
            raise ValueError(
                f"{where} IDs must be unique simple identifiers: {identifier!r}"
            )
        result[identifier] = record
    return result


def _refs(value, allowed, where):
    _texts(value, where, nonempty=True)
    if len(set(value)) != len(value) or not set(value) <= set(allowed):
        raise ValueError(f"{where} must contain unique references to recorded IDs")


def _stamp(value, where):
    try:
        parsed = datetime.fromisoformat(_text(value, where))
    except ValueError as exc:
        raise ValueError(f"{where} must be an ISO timestamp with timezone") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{where} must include a timezone")
    return parsed


def validate_assessment(data):
    """Reject incomplete or contradictory provenance before producing any output."""
    if not isinstance(data, dict) or data.get("schema_version") != 2:
        raise ValueError("assessment.schema_version must be 2")
    allowed = {
        "schema_version",
        "profile",
        "run",
        "executive",
        "checks",
        "inventory",
        "findings",
        "actions",
        "limitations",
        "profile_details",
        "references",
        "inventory_companion",
        "document_kind",
        "report_mode",
        "cover",
    }
    if set(data) - allowed:
        raise ValueError(
            "unknown assessment fields: " + ", ".join(sorted(set(data) - allowed))
        )
    if _text(data.get("profile"), "assessment.profile") not in PROFILES:
        raise ValueError("assessment.profile must identify a supported report profile")
    if data.get("document_kind", "assessment") not in (
        "assessment",
        "proposal",
        "receipt",
    ):
        raise ValueError("document_kind must be assessment, proposal or receipt")
    new_mode = is_new_mode(data)
    if new_mode:
        _fields(data["report_mode"], "inventory", "report_mode")
        if data["report_mode"].get("inventory") not in INVENTORY_MODES:
            raise ValueError(
                "report_mode.inventory must be one of: " + ", ".join(INVENTORY_MODES)
            )
        if data["report_mode"]["inventory"] == "companion" and not data.get(
            "inventory_companion"
        ):
            raise ValueError(
                "report_mode.inventory companion requires inventory_companion"
            )
    if "cover" in data:
        if not new_mode:
            raise ValueError("cover requires report_mode")
        cover = data["cover"]
        _fields(cover, "title scope_label organization_label", "cover")
        for key, limit in (("title", 120), ("scope_label", 160)):
            if len(_text(cover.get(key), "cover." + key)) > limit:
                raise ValueError(f"cover.{key} must be at most {limit} characters")
        _optional_texts(cover, "organization_label", "cover")
    run = data.get("run")
    if not isinstance(run, dict):
        raise ValueError("assessment.run is required")
    _fields(
        run,
        "id version operator scope review_status assessed_at generated_at enumeration_complete unvisited_scope",
        "run",
    )
    for key in ("id", "version", "operator", "scope", "review_status"):
        _text(run.get(key), "run." + key)
    assessed = _stamp(run.get("assessed_at"), "run.assessed_at")
    if _stamp(run.get("generated_at"), "run.generated_at") < assessed:
        raise ValueError("generated_at cannot precede assessed_at")
    if not isinstance(run.get("enumeration_complete"), bool):
        raise ValueError("run.enumeration_complete must be true or false")
    _texts(run.get("unvisited_scope"), "run.unvisited_scope")
    if run["enumeration_complete"] == bool(run["unvisited_scope"]):
        raise ValueError("unvisited_scope must explain incomplete enumeration only")
    executive = data.get("executive")
    if not isinstance(executive, dict):
        raise ValueError("assessment.executive is required")
    _fields(executive, "purpose conclusion key_points decisions", "executive")
    for key in ("purpose", "conclusion"):
        _text(executive.get(key), "executive." + key)
    for key in ("key_points", "decisions"):
        _texts(executive.get(key), "executive." + key, nonempty=True)
    _texts(data.get("limitations"), "assessment.limitations", nonempty=True)
    details = data.get("profile_details")
    if not isinstance(details, dict) or not details:
        raise ValueError(
            "profile_details must state the profile-specific basis and unknowns"
        )
    for label, value in details.items():
        _text(label, "profile_details label")
        _text(value, "profile_details value")
    checks = _records(data.get("checks"), "checks", nonempty=True)
    fact_owner = {}
    for check in checks.values():
        _fields(check, "id label method kind fact_keys", "check")
        for key in ("label", "method"):
            _text(check.get(key), "checks." + key)
        if "kind" in check or new_mode:
            if check.get("kind") not in CHECK_KINDS:
                raise ValueError("check.kind must be content or metadata")
        if "fact_keys" in check:
            keys = _texts(check["fact_keys"], "check.fact_keys")
            if len(set(keys)) != len(keys) or not all(_ID.fullmatch(k) for k in keys):
                raise ValueError("check.fact_keys must be unique simple identifiers")
            for key in keys:
                if key in fact_owner:
                    raise ValueError(
                        f"fact key {key} is declared on more than one check"
                    )
                fact_owner[key] = check["id"]
    inventory = _records(data.get("inventory"), "inventory")
    coverage = {}
    for identifier, obj in inventory.items():
        _fields(
            obj, "id name type source url checks size_bytes facts", "inventory object"
        )
        _optional_texts(obj, "source url", "inventory")
        if "size_bytes" in obj and (
            type(obj["size_bytes"]) is not int or obj["size_bytes"] < 0
        ):
            raise ValueError("inventory.size_bytes must be a nonnegative integer")
        facts = obj.get("facts", {})
        if not isinstance(facts, dict):
            raise ValueError("inventory.facts must be a label-to-value object")
        for label, value in facts.items():
            _text(label, "inventory fact label")
            if isinstance(value, str):
                _text(value, "inventory fact value")
            elif not isinstance(value, (int, float, bool)) or (
                isinstance(value, float) and not math.isfinite(value)
            ):
                raise ValueError(
                    "inventory facts must contain text or finite scalar values"
                )
        for key in ("name", "type"):
            _text(obj.get(key), "inventory." + key)
        if obj.get("url") and (
            not isinstance(obj["url"], str)
            or urlsplit(obj["url"]).scheme not in ("https", "http")
        ):
            raise ValueError("inventory.url must be an http or https source link")
        statuses = _records(obj.get("checks"), "inventory.checks")
        if set(statuses) != set(checks):
            raise ValueError(
                f"inventory {identifier} must record every check, including not_applicable"
            )
        for check in statuses.values():
            _fields(check, "id status method reason", "inventory check")
            _optional_texts(check, "method reason", "inventory check")
            if check.get("status") not in CHECK_STATES:
                raise ValueError("inventory check status is invalid")
            if check["status"] != "checked":
                _text(check.get("reason"), "unchecked item reason")
            if check["status"] in ("checked", "partial"):
                _text(check.get("method"), "checked item method")
            if check["status"] == "checked" and "reason" in check:
                raise ValueError(
                    "a limited check needs partial status, method and reason"
                )
            if check["status"] == "checked":
                for key in checks[check["id"]].get("fact_keys", []):
                    value = facts.get(key)
                    if type(value) not in (int, float) or (
                        type(value) is float and not math.isfinite(value)
                    ):
                        raise ValueError(
                            f"fact {key} must be numeric for checked objects"
                        )
        coverage[identifier] = statuses
    findings = _records(data.get("findings"), "findings")
    for finding in findings.values():
        _fields(
            finding,
            "id title observation impact confidence priority priority_reason recommendation object_ids check_ids criterion example_object_ids",
            "finding",
        )
        _optional_texts(finding, "criterion", "finding")
        for key in (
            "title",
            "observation",
            "impact",
            "confidence",
            "priority",
            "priority_reason",
            "recommendation",
        ):
            _text(finding.get(key), "findings." + key)
        if new_mode and finding["priority"] not in PRIORITIES:
            raise ValueError(
                "finding.priority must be one of: " + ", ".join(PRIORITIES)
            )
        _refs(finding.get("object_ids"), inventory, "finding.object_ids")
        if "example_object_ids" in finding:
            if not new_mode:
                raise ValueError("example_object_ids requires report_mode")
            examples = finding["example_object_ids"]
            _texts(examples, "finding.example_object_ids", nonempty=True)
            if (
                len(examples) > 3
                or len(set(examples)) != len(examples)
                or not set(examples) <= set(finding["object_ids"])
            ):
                raise ValueError(
                    "finding.example_object_ids must be 1-3 unique IDs from the finding object_ids"
                )
        _refs(finding.get("check_ids"), checks, "finding.check_ids")
        for obj in finding["object_ids"]:
            for check in finding["check_ids"]:
                if coverage[obj][check]["status"] not in ("checked", "partial"):
                    raise ValueError(
                        "findings must reference checked evidence; report unchecked items as coverage limitations"
                    )
    actions = _records(data.get("actions"), "actions")
    for action in actions.values():
        _fields(
            action,
            "id action status finding_ids basis owner target verification completed_at",
            "action",
        )
        _optional_texts(
            action, "basis owner target verification completed_at", "action"
        )
        if "finding_ids" in action:
            _texts(action["finding_ids"], "action.finding_ids")
        _text(action.get("action"), "actions.action")
        if action.get("finding_ids"):
            _refs(action["finding_ids"], findings, "action.finding_ids")
        elif not action.get("basis"):
            raise ValueError("an action needs finding_ids or an explicit basis")
        if action.get("status") not in ACTION_STATES:
            raise ValueError("action.status is invalid")
        if data.get("document_kind") == "proposal" and action["status"] not in (
            "proposed",
            "approved",
        ):
            raise ValueError("a proposal cannot claim executed actions")
        if action["status"] == "completed":
            _text(action.get("verification"), "completed action verification")
            completed = _stamp(action.get("completed_at"), "action.completed_at")
            if completed > _stamp(run["generated_at"], "run.generated_at"):
                raise ValueError(
                    "completed action cannot be later than report generation"
                )
    references = data.get("references", [])
    _texts(references, "references")
    companion = data.get("inventory_companion")
    if (
        companion is not None
        and new_mode
        and data["report_mode"]["inventory"]
        in (
            "compact",
            "omitted_by_request",
        )
    ):
        raise ValueError("inventory_companion requires report_mode.inventory companion")
    if companion is not None:
        if not isinstance(companion, dict) or companion.get("authorized") is not True:
            raise ValueError(
                "inventory_companion requires explicit output authorization"
            )
        _fields(
            companion,
            "authorized name location report_id version url row_count byte_size delivery_status",
            "inventory_companion",
        )
        if "url" in companion and (
            not isinstance(companion["url"], str)
            or urlsplit(companion["url"]).scheme != "https"
        ):
            raise ValueError("inventory_companion.url must be an https link")
        for key in ("row_count", "byte_size"):
            if key in companion and (
                type(companion[key]) is not int or companion[key] < 0
            ):
                raise ValueError(
                    f"inventory_companion.{key} must be a nonnegative integer"
                )
        if "delivery_status" in companion and (
            companion["delivery_status"] not in DELIVERY_STATUSES
        ):
            raise ValueError("inventory_companion.delivery_status is invalid")
        if "row_count" in companion and companion["row_count"] != len(inventory):
            raise ValueError(
                "inventory_companion.row_count must equal the inventory size"
            )
        for key in ("name", "location", "report_id", "version"):
            _text(companion.get(key), "inventory_companion." + key)
        if (companion["report_id"], companion["version"]) != (
            run["id"],
            run["version"],
        ):
            raise ValueError(
                "inventory_companion must identify this report and version"
            )
    return checks, inventory, findings, actions


def _check_description(check):
    return (
        "; ".join(check[key] for key in ("method", "reason") if check.get(key))
        or "Not recorded"
    )


def _display_timestamp(value):
    return _stamp(value, "timestamp").strftime("%d %b %Y, %H:%M UTC%z")


_FORMATTING = {}
_RAW_BYTES = re.compile(r"\b\d{1,3}(?:[,.]\d{3})+\s*bytes\b|\b\d{4,}\s*(?:bytes|B)\b")
_BINARY_UNITS = re.compile(r"(?:\b\d[\d.,]*\s*)?\b(?:KiB|MiB|GiB|TiB)\b")
_INCOMPLETE_STATES = ("partial", "skipped", "failed", "not_attempted")


def _formatting():
    """Load the shared size formatter next to this file (cached)."""
    if not _FORMATTING:
        _FORMATTING.update(
            runpy.run_path(
                str(Path(__file__).resolve().with_name("report_formatting.py"))
            )
        )
    return _FORMATTING


def _plural(count, singular, plural=None):
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def _join_and(parts):
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _new_mode_derived(data, checks, inventory, findings, counts, status, run):
    """Coverage, overview, cover and metrics for new-mode records."""
    fmt = _formatting()
    objects = list(inventory.values())
    files = [obj for obj in objects if obj["type"] == "file"]
    folders = [obj for obj in objects if obj["type"] == "folder"]
    other = len(objects) - len(files) - len(folders)

    def states(obj, kind):
        return {
            c["status"] for c in obj["checks"] if checks[c["id"]].get("kind") == kind
        }

    content_checked = [f for f in files if "checked" in states(f, "content")]
    content_partial = [
        f
        for f in files
        if "checked" not in states(f, "content") and "partial" in states(f, "content")
    ]
    metadata_only = [
        f
        for f in files
        if not states(f, "content") & {"checked", "partial"}
        and states(f, "metadata") & {"checked", "partial"}
    ]
    not_inspected = len(files) - len(content_checked) - len(content_partial)
    not_inspected -= len(metadata_only)
    incomplete = []
    for check_id, check in checks.items():
        present = [s for s in _INCOMPLETE_STATES if counts[check_id][s]]
        if not present:
            continue
        hit = [
            obj
            for obj in objects
            if next(c["status"] for c in obj["checks"] if c["id"] == check_id)
            in _INCOMPLETE_STATES
        ]
        incomplete.append(
            {
                "label": check["label"],
                "count": len(hit),
                "states": "/".join(s.replace("_", " ") for s in present),
                "_all_files": all(obj["type"] == "file" for obj in hit),
            }
        )
    real = [f for f in findings.values() if f["priority"] != "info"]
    info = len(findings) - len(real)
    affected = {obj for f in real for obj in f["object_ids"]}
    has_content = any(c.get("kind") == "content" for c in checks.values())
    coverage = {
        "files": len(files),
        "folders": len(folders),
        "other": other,
        "content_checked_files": len(content_checked),
        "content_partial_files": len(content_partial),
        "metadata_only_files": len(metadata_only),
        "not_inspected_files": not_inspected,
        "has_content_checks": has_content,
        "incomplete_checks": [
            {k: v for k, v in item.items() if not k.startswith("_")}
            for item in incomplete
        ],
        "findings": len(real),
        "informational": info,
        "affected_objects": len(affected),
    }
    listed = [
        text
        for text in (
            _plural(len(files), "file") if files else "",
            _plural(len(folders), "folder") if folders else "",
            _plural(other, "other item") if other else "",
        )
        if text
    ]
    sentences = [(_join_and(listed) if listed else "No items") + " listed."]
    if has_content:
        sentence = f"Content checked: {_plural(len(content_checked), 'file')}."
        if content_partial:
            sentence += f" Partially checked: {len(content_partial)}."
        if metadata_only:
            sentence += f" Metadata only: {len(metadata_only)}."
        if not_inspected:
            sentence += f" Not inspected: {not_inspected}."
        sentences.append(sentence)
    else:
        sentences.append(
            f"{_plural(len(files), 'file')} measured from metadata; "
            "file contents were not reviewed."
        )
    note = f" (plus {_plural(info, 'informational note')})" if info else ""
    if real:
        sentences.append(f"Findings: {len(real)}{note}.")
    else:
        sentences.append(f"No findings{note}.")
    sentences.append(
        "Scope listing completed."
        if run["enumeration_complete"]
        else "Scope listing incomplete; the unobserved population is unknown."
    )
    if status == "Partial assessment":
        for item in incomplete:
            noun = "file" if item["_all_files"] else "item"
            sentences.append(
                f"{item['label']}: {item['states']} for {_plural(item['count'], noun)}."
            )
    explanation = {
        "Selected checks completed": "All selected checks completed",
        "Partial assessment": "Some assessment checks unavailable",
        "Unable to assess": "No checks completed",
    }[status]
    cover = data.get("cover", {})
    assessed = _stamp(run["assessed_at"], "run.assessed_at")
    verb = "reviewed" if has_content else "measured"
    measured = [f for f in files if "size_bytes" in f]
    sizes = [f["size_bytes"] for f in measured]
    total = sum(sizes) if measured else None
    ranked = sorted(measured, key=lambda f: (-f["size_bytes"], f["id"]))
    metrics = {
        "listed_files": len(files),
        "measured_files": len(measured),
        "total_size_bytes": total,
        "total_size": fmt["format_size"](total) if measured else "Not measured",
        "size_by_object": {
            obj["id"]: fmt["format_size"](obj.get("size_bytes")) for obj in objects
        },
        "largest_files": [
            {
                "id": f["id"],
                "name": f["name"],
                "size_bytes": f["size_bytes"],
                "size": fmt["format_size"](f["size_bytes"]),
            }
            for f in ranked[:10]
        ],
        "size_unit": fmt["common_unit"](sizes),
        "percent_of_total": (
            {f["id"]: fmt["format_percent"](f["size_bytes"], total) for f in measured}
            if total
            else {}
        ),
    }
    return {
        "coverage": coverage,
        "overview": f"{status}. " + " ".join(sentences),
        "status_explanation": explanation,
        "cover": {
            "title": cover.get("title"),
            "scope_label": cover.get("scope_label") or "Selected Kiteworks scope",
            "organization_label": cover.get("organization_label"),
            "date_label": f"{assessed.day} {assessed:%B %Y}",
            "count_line": f"{_plural(len(files), 'file')} {verb} \u00b7 {explanation}",
            "review_line": run["review_status"],
        },
        "metrics": metrics,
    }


def _storage_paragraph(metrics):
    listed = metrics["listed_files"]
    count = metrics["measured_files"]
    tail = (
        " Folder aggregates are excluded to avoid double counting. "
        "These are logical sizes in the observed scope, not physical usage, "
        "freed space or cost savings."
    )
    if not count:
        return (
            f"No file sizes were measured among {_plural(listed, 'listed file')}."
            + tail
        )
    label = "Measured file size" if count == listed else "Measured subtotal"
    return (
        f"{label}: {metrics['total_size']} across {count} of "
        f"{_plural(listed, 'listed file')}. "
        "Sizes use decimal units (1 kB = 1,000 bytes)." + tail
    )


def authoring_warnings(data) -> list[str]:
    """Flag raw byte counts and binary units in authored prose (new mode only)."""
    if not is_new_mode(data):
        return []
    fields = []
    executive = data.get("executive") or {}
    for key in ("purpose", "conclusion"):
        fields.append((f"executive.{key}", executive.get(key)))
    for key in ("key_points", "decisions"):
        for index, item in enumerate(executive.get(key) or []):
            fields.append((f"executive.{key}[{index}]", item))
    for index, finding in enumerate(data.get("findings") or []):
        for key in ("observation", "impact", "recommendation"):
            fields.append((f"findings[{index}].{key}", finding.get(key)))
    warnings = []
    for path, value in fields:
        if not isinstance(value, str):
            continue
        for pattern in (_RAW_BYTES, _BINARY_UNITS):
            for match in pattern.finditer(value):
                warnings.append(
                    f"{path}: use the formatted size from metrics (decimal units), "
                    f"not '{match.group(0)}'"
                )
    return warnings


FULL_FINDINGS = 8
REGISTER_LIMIT = 50
BASIS_ACTION_LIMIT = 20
_NAMES = {"info": "informational"}


def _natural_key(identifier):
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", str(identifier))
    ]


EXAMPLE_BUDGET = 10
EXAMPLES_FULL = 5
EXAMPLES_PARTIAL = 3
UNVISITED_LIMIT = 10


def _example_sections(finding, inventory, allowed):
    """Bounded example table for one full-block finding (new mode only)."""
    ids = finding["object_ids"]
    if len(ids) <= EXAMPLES_FULL:
        chosen, assessor = sorted(ids, key=_natural_key), False
    elif finding.get("example_object_ids"):
        chosen, assessor = list(finding["example_object_ids"]), True
    else:
        chosen, assessor = sorted(ids, key=_natural_key)[:EXAMPLES_PARTIAL], False
    chosen = chosen[:allowed]
    rows = [["Example", "Name"]]
    for oid in chosen:
        obj = inventory[oid]
        name = (
            {"text": obj["name"], "url": obj["url"]} if obj.get("url") else obj["name"]
        )
        rows.append([oid, name])
    sections = []
    if len(chosen) < len(ids):
        basis = "selected by the assessor" if assessor else "first by object ID"
        sections.append(
            {
                "paragraph": f"Examples: {len(chosen)} of {len(ids)} affected "
                f"objects. Selection: {basis}; file names are shown only as "
                "needed to act."
            }
        )
    sections.append({"table": {"data": rows}})
    return sections


def _findings_sections(data, checks, findings, view, inventory=None):
    """Full blocks, register and disclosure for new-mode assessments."""
    ordered = sorted(
        findings.values(),
        key=lambda f: (PRIORITIES.index(f["priority"]), _natural_key(f["id"])),
    )
    companion = inventory_mode(data) == "companion" and view == "pdf"
    shown = [
        f
        for index, f in enumerate(ordered)
        if not companion
        or index < REGISTER_LIMIT
        or f["priority"] in ("critical", "high")
    ]
    shown_ids = {f["id"] for f in shown}
    hidden = [f for f in ordered if f["id"] not in shown_ids]
    full = shown[:FULL_FINDINGS]
    register = shown[FULL_FINDINGS:]
    sections = []
    budget = max(EXAMPLE_BUDGET, len(full))
    for index, finding in enumerate(full):
        sections.extend(
            [
                {
                    "id": "finding-" + finding["id"],
                    "heading": finding["id"] + " — " + finding["title"],
                    "level": 2,
                    "paragraph": finding["observation"],
                },
                {
                    "heading": "Why this matters",
                    "level": 3,
                    "outline": False,
                    "paragraph": finding["impact"],
                },
                {
                    "heading": "Recommended response",
                    "level": 3,
                    "outline": False,
                    "paragraph": finding["recommendation"],
                },
                {
                    "paragraph": f"Priority: {finding['priority']}. {finding['priority_reason']} "
                    f"Evidence: {finding['confidence']}. "
                    f"Affected objects: {len(finding['object_ids'])}."
                },
            ]
        )
        if inventory is not None:
            count = len(finding["object_ids"])
            desired = (
                count
                if count <= EXAMPLES_FULL
                else len(finding.get("example_object_ids") or ()) or EXAMPLES_PARTIAL
            )
            take = min(desired, budget - (len(full) - index - 1))
            budget -= take
            sections.extend(_example_sections(finding, inventory, take))
        if finding.get("criterion"):
            sections.append({"paragraph": "Criterion: " + finding["criterion"]})
    if register:
        sections.append(
            {
                "id": "findings-register",
                "heading": "Findings register",
                "level": 2,
                "outline": False,
                "table": {
                    "data": [["ID", "Title", "Priority", "Affected", "Confidence"]]
                    + [
                        [
                            f["id"],
                            f["title"],
                            f["priority"],
                            len(f["object_ids"]),
                            f["confidence"],
                        ]
                        for f in register
                    ],
                    "col_widths_frac": [0.1, 0.45, 0.13, 0.12, 0.2],
                },
            }
        )
    if hidden:
        counts = Counter(f["priority"] for f in hidden)
        parts = [
            f"{counts[p]} more {_NAMES.get(p, p)}" for p in PRIORITIES if counts[p]
        ]
        noun = "finding" if len(hidden) == 1 else "findings"
        verb = "is" if len(hidden) == 1 else "are"
        sections.append(
            {
                "paragraph": f"{_join_and(parts)} {noun} {verb} listed in "
                f'{data["inventory_companion"]["name"]}; filter the "Record type" '
                'column for "finding".'
            }
        )
    view_ids = {
        "full": [f["id"] for f in full],
        "register": [f["id"] for f in register],
        "hidden": [f["id"] for f in hidden],
    }
    return sections, view_ids, shown_ids


def _action_sections(data, actions, shown_ids, view):
    """One compact register table for new-mode assessment actions."""
    companion = inventory_mode(data) == "companion" and view == "pdf"
    basis_only = sorted(
        (a["id"] for a in actions.values() if not a.get("finding_ids")),
        key=_natural_key,
    )
    basis_shown = set(basis_only[:BASIS_ACTION_LIMIT] if companion else basis_only)
    shown, hidden = [], []
    for action in actions.values():
        ids = action.get("finding_ids")
        keep = any(i in shown_ids for i in ids) if ids else action["id"] in basis_shown
        (shown if keep else hidden).append(action)
    completed = any(a["status"] == "completed" for a in shown)
    header = ["ID", "Action", "Status", "Owner", "Target", "Basis"]
    if completed:
        header += ["Completion evidence", "Completed at"]
    rows = []
    for action in shown:
        row = [
            action["id"],
            action["action"],
            action["status"],
            action.get("owner", "Unassigned"),
            action.get("target", "Not agreed"),
            ", ".join(action.get("finding_ids", [])) or action.get("basis", ""),
        ]
        if completed:
            row += [
                action.get("verification", "Not recorded"),
                action.get("completed_at", "Not recorded"),
            ]
        rows.append(row)
    sections = []
    if rows:
        sections.append(
            {
                "heading": "Action register",
                "level": 2,
                "outline": False,
                "table": {"data": [header, *rows]},
            }
        )
    if hidden:
        sections.append(
            {
                "paragraph": f"{_plural(len(hidden), 'more action')} "
                f"{'is' if len(hidden) == 1 else 'are'} listed in "
                f'{data["inventory_companion"]["name"]}; filter the "Record type" '
                'column for "action".'
            }
        )
    return sections, [a["id"] for a in hidden]


def _evidence_sections(data, run, overview, mode, view, delivery, object_count):
    """Level-1 Evidence and coverage section (new mode)."""
    letter = "C" if is_new_mode(data) else "B"
    companion = data.get("inventory_companion") or {}
    unvisited = list(run["unvisited_scope"])
    target = "the text export"
    if mode == "companion" and view == "pdf":
        target = companion.get("name", target)
    sections = [
        {
            "id": "evidence",
            "heading": "Evidence and coverage",
            "paragraph": f"Report {run['id']}, version {run['version']}. "
            f"Assessed {_display_timestamp(run['assessed_at'])}. {overview}",
        }
    ]
    if unvisited:
        shown = unvisited if view == "txt" else unvisited[:UNVISITED_LIMIT]
        sections.append(
            {"heading": "Unvisited scope", "level": 2, "bullets": list(shown)}
        )
        if len(shown) < len(unvisited):
            sections.append(
                {
                    "paragraph": f"{len(unvisited) - len(shown)} more unvisited "
                    f"locations are listed in {target}."
                }
            )
    if view == "txt" or mode == "compact":
        sections.append(
            {"paragraph": f"The complete inventory is in Appendix {letter}."}
        )
    elif mode == "embedded":
        sections.append(
            {
                "paragraph": "The complete inventory with per-object check details "
                f"is in Appendix {letter}."
            }
        )
    elif mode == "omitted_by_request":
        sections.append(
            {
                "paragraph": "The complete inventory is not included in this report, "
                "at the requester's request. Coverage and findings above are complete."
            }
        )
    else:
        source = {**companion, **(delivery or {})}
        status = {
            "size_verified": "saved and size-verified",
            "download_verified": "saved and download-verified",
        }.get(source.get("delivery_status"), "save not verified")
        count = source.get("row_count") or object_count
        sections.append(
            {
                "paragraph": f"Companion file: {source.get('name')}; location: "
                f"{source.get('location')}; {count} objects; {status}."
            }
        )
        if source.get("url"):
            sections.append(
                {
                    "table": {
                        "data": [
                            [{"text": "Open companion file", "url": source["url"]}]
                        ]
                    }
                }
            )
        sections.append(
            {
                "paragraph": 'To find the objects behind a finding, filter the "Finding IDs" '
                "column for the finding ID wrapped in semicolons, for example "
                '";F1;". Finding and action details are rows whose "Record type" '
                'is "finding" or "action".'
            }
        )
    return sections


def _inventory_sections(inventory, checks, findings, metrics, view, new_mode=False):
    """Inventory appendix for compact mode, and the complete TXT inventory tables."""
    by_object = {}
    for finding in findings.values():
        for oid in finding["object_ids"]:
            by_object.setdefault(oid, []).append(finding["id"])
    rows = [["ID", "Name", "Type", "Size", "Checks", "Findings"]]
    for obj in inventory.values():
        rows.append(
            [
                obj["id"],
                {"text": obj["name"], "url": obj["url"]}
                if obj.get("url")
                else obj["name"],
                obj["type"],
                metrics["size_by_object"][obj["id"]],
                "; ".join(
                    f"{checks[c['id']]['label']}: {c['status'].replace('_', ' ')}"
                    for c in obj["checks"]
                ),
                ", ".join(by_object.get(obj["id"], [])),
            ]
        )
    sections = [
        {
            "id": "inventory",
            "heading": "Appendix C — Inventory"
            if new_mode
            else "Appendix B — Inventory",
            "paragraph": f"{len(inventory)} enumerated objects. Every configured "
            "check is accounted for per object.",
            "table": {
                "data": rows,
                "col_widths_frac": (
                    [0.11, 0.30, 0.09, 0.13, 0.25, 0.12]
                    if new_mode
                    else [0.1, 0.32, 0.08, 0.1, 0.28, 0.12]
                ),
            },
        }
    ]
    if view == "txt":
        header = ["ID"]
        for check in checks.values():
            header += [check["label"] + " status", check["label"] + " method or reason"]
        detail = [header]
        for obj in inventory.values():
            row = [obj["id"]]
            states = {c["id"]: c for c in obj["checks"]}
            for cid in checks:
                row += [
                    states[cid]["status"].replace("_", " "),
                    _check_description(states[cid]),
                ]
            detail.append(row)
        sections.append(
            {"heading": "Per-check status", "level": 2, "table": {"data": detail}}
        )
    return sections


def prepare_assessment(data, *, view="pdf", delivery=None, layout="full"):
    """Return ordered sections and derived coverage for PDF, text and CSV views."""
    checks, inventory, findings, actions = validate_assessment(data)
    run = data["run"]
    counts = {}
    checked_total = 0
    partial_total = 0
    for check_id, check in checks.items():
        states = Counter(
            next(c["status"] for c in obj["checks"] if c["id"] == check_id)
            for obj in inventory.values()
        )
        counts[check_id] = {state: states[state] for state in CHECK_STATES}
        checked_total += states["checked"]
        partial_total += states["partial"]
    incomplete = not run["enumeration_complete"] or any(
        counts[c][s]
        for c in counts
        for s in ("partial", "skipped", "failed", "not_attempted")
    )
    status = (
        "Unable to assess"
        if not (checked_total or partial_total)
        else ("Partial assessment" if incomplete else "Selected checks completed")
    )
    affected = {obj for f in findings.values() for obj in f["object_ids"]}
    checked_objects = sum(
        any(c["status"] == "checked" for c in obj["checks"])
        for obj in inventory.values()
    )
    partial_objects = sum(
        any(c["status"] == "partial" for c in obj["checks"])
        for obj in inventory.values()
    )
    derived = (
        _new_mode_derived(data, checks, inventory, findings, counts, status, run)
        if is_new_mode(data)
        else None
    )
    overview = (
        derived["overview"]
        if derived
        else (
            f"{status}. Scope listing: {len(inventory)} items. "
            f"Items with at least one completed check: {checked_objects}. "
            f"Items with partial checks: {partial_objects}. "
            f"Items with findings: {len(affected)}. Findings: {len(findings)}. "
            + (
                "Scope listing completed."
                if run["enumeration_complete"]
                else "Scope listing incomplete; the unobserved population is unknown."
            )
        )
    )
    executive = data["executive"]
    summary = [
        {
            "id": "executive-summary",
            "heading": "Executive summary",
            "paragraph": executive["purpose"],
        },
        {"heading": "Conclusion", "level": 2, "paragraph": executive["conclusion"]},
        {"heading": "Coverage at a glance", "level": 2, "paragraph": overview},
        {"heading": "Key findings", "level": 2, "bullets": executive["key_points"]},
        {
            "heading": "Decisions requested",
            "level": 2,
            "bullets": executive["decisions"],
        },
    ]
    if data["profile"] == "storage":
        files = [obj for obj in inventory.values() if obj["type"] == "file"]
        measured = [obj for obj in files if "size_bytes" in obj]
        measurement = (
            _storage_paragraph(derived["metrics"])
            if derived
            else (
                f"Measured file bytes: {sum(obj['size_bytes'] for obj in measured)}. "
                f"Measured files: {len(measured)} of {len(files)} listed files. "
                "Folder aggregates are excluded to avoid double counting. "
                "These are logical sizes in the observed scope, not physical usage, freed space or cost savings."
            )
        )
        summary.insert(
            3, {"heading": "Storage measurements", "level": 2, "paragraph": measurement}
        )
        if derived:
            metrics = derived["metrics"]
            largest = [["File", "Size", "Share"]]
            for item in metrics["largest_files"][:10]:
                url = inventory[item["id"]].get("url")
                largest.append(
                    [
                        {"text": item["name"], "url": url} if url else item["name"],
                        item["size"],
                        metrics["percent_of_total"].get(item["id"], ""),
                    ]
                )
            if len(largest) > 1:
                summary.insert(
                    4,
                    {
                        "heading": "Largest files",
                        "level": 2,
                        "table": {
                            "data": largest,
                            "col_widths_frac": [0.6, 0.2, 0.2],
                        },
                    },
                )
    body = [
        {
            "id": "report-details",
            "heading": "Report details",
            "table": {
                "data": [
                    ["Context", "Value"],
                    ["Report", run["id"] + " / " + run["version"]],
                    [
                        "Report format",
                        f"Assessment schema 2; template {TEMPLATE_VERSION if is_new_mode(data) else TEMPLATE_VERSION_LEGACY}",
                    ],
                    ["Profile", PROFILES[data["profile"]]],
                    ["Document kind", data.get("document_kind", "assessment")],
                    ["Scope", run["scope"]],
                    ["Scanned by", run["operator"]],
                    ["Assessed", _display_timestamp(run["assessed_at"])],
                    ["Generated", _display_timestamp(run["generated_at"])],
                    ["Review status", run["review_status"]],
                    *[[k, v] for k, v in data["profile_details"].items()],
                ],
                "col_widths_frac": [0.25, 0.75],
            },
        },
        {
            "id": "coverage",
            "heading": "Assessment coverage",
            "paragraph": overview,
            "table": {
                "data": [
                    [
                        "Check",
                        "Checked",
                        "Partial",
                        "Skipped",
                        "Failed",
                        "Not attempted",
                        "Not applicable",
                    ]
                ]
                + [
                    [check["label"], *[counts[key][s] for s in CHECK_STATES]]
                    for key, check in checks.items()
                ],
                "col_widths_frac": [0.27, 0.11, 0.10, 0.11, 0.09, 0.16, 0.16],
            },
        },
    ]
    appendix_details = []
    if derived:
        # New mode: provenance and check-state detail live in the appendix.
        details, coverage_table = body
        body = []
        appendix_details = [
            {**details, "heading": "Appendix A — Report details and coverage"},
            {**coverage_table, "level": 2},
        ]
    if run["unvisited_scope"] and not derived:
        body.append({"heading": "Unvisited scope", "bullets": run["unvisited_scope"]})
    body.append({"id": "findings", "heading": "Findings"})
    if not findings:
        body.append(
            {
                "paragraph": (
                    "No issue was detected in the inspected portions. This is not evidence of compliance."
                    if checked_total or partial_total
                    else "No conclusion can be drawn: no checks completed."
                )
            }
        )
    compact_register = (
        is_new_mode(data) and data.get("document_kind", "assessment") == "assessment"
    )
    findings_view = None
    shown_ids = set(findings)
    mode = inventory_mode(data)
    if compact_register:
        sections, findings_view, shown_ids = _findings_sections(
            data, checks, findings, view, inventory
        )
        body.extend(sections)
    for finding in () if compact_register else findings.values():
        body.extend(
            [
                {
                    "id": "finding-" + finding["id"],
                    "heading": finding["id"] + " — " + finding["title"],
                    "level": 2,
                    "paragraph": finding["observation"],
                },
                {
                    "heading": "Why this matters",
                    "level": 3,
                    "paragraph": finding["impact"],
                },
                {
                    "heading": "Recommended response",
                    "level": 3,
                    "paragraph": finding["recommendation"],
                },
                {
                    "paragraph": f"Priority: {finding['priority']}. {finding['priority_reason']} Evidence: {finding['confidence']}."
                },
                {
                    "table": {
                        "data": [["Evidence objects", "Checks", "Criterion"]]
                        + [
                            [
                                {"text": obj, "url": "#object-" + obj}
                                if mode == "embedded"
                                else obj,
                                ", ".join(
                                    checks[c]["label"] for c in finding["check_ids"]
                                ),
                                finding.get(
                                    "criterion",
                                    "No legal conclusion; criterion not supplied",
                                ),
                            ]
                            for obj in finding["object_ids"]
                        ]
                    }
                },
            ]
        )
    body.append(
        {
            "id": "action-plan",
            "heading": "Action plan",
            "paragraph": "Owners and target dates are proposals unless explicitly confirmed. Unassigned means no commitment has been recorded.",
        }
    )
    if compact_register:
        sections, findings_view["hidden_actions"] = _action_sections(
            data, actions, shown_ids, view
        )
        body.extend(sections)
    for action in () if compact_register else actions.values():
        body.append(
            {
                "heading": action["id"] + " — " + action["action"],
                "level": 2,
                "bullets": [
                    "Status: " + action["status"],
                    "Owner: " + action.get("owner", "Unassigned"),
                    "Target: " + action.get("target", "Not agreed"),
                    "Basis: "
                    + (
                        ", ".join(action.get("finding_ids", []))
                        or action.get("basis", "")
                    ),
                    "Completion evidence: "
                    + action.get("verification", "Not recorded"),
                    "Completed at: " + action.get("completed_at", "Not recorded"),
                ],
            }
        )
    if not actions:
        body.append(
            {
                "paragraph": "No action commitments recorded. See the decisions requested above."
            }
        )
    body.append(
        {"id": "limitations", "heading": "Limitations", "bullets": data["limitations"]}
    )
    if derived:
        body.extend(
            _evidence_sections(
                data, run, overview, mode, view, delivery, len(inventory)
            )
        )
    appendix = [
        *appendix_details,
        {
            "id": "methodology",
            "heading": (
                "Appendix B — Methodology" if derived else "Appendix A — Methodology"
            ),
            "table": {
                "data": [["Check", "Method"]]
                + [[c["label"], c["method"]] for c in checks.values()]
                + (
                    [["Size units", "Decimal: 1 kB = 1,000 bytes"]]
                    if derived and any("size_bytes" in o for o in inventory.values())
                    else []
                )
            },
        },
    ]
    if data.get("references"):
        appendix.append({"heading": "References", "bullets": data["references"]})
    if derived and (view == "txt" or mode == "compact"):
        appendix.extend(
            _inventory_sections(
                inventory, checks, findings, derived["metrics"], view, new_mode=True
            )
        )
    elif not derived or mode == "embedded":
        appendix.append(
            {
                "id": "inventory",
                "heading": "Appendix C — Complete inventory"
                if derived
                else "Appendix B — Complete inventory",
                "paragraph": f"{len(inventory)} enumerated objects. Every configured check is accounted for per object. "
                "Unvisited scope is described separately and cannot be listed as scanned files.",
            }
        )
    companion = None if derived else data.get("inventory_companion")
    if companion:
        appendix.append(
            {
                "paragraph": f"Complete companion: {companion['name']}; location: {companion['location']}; "
                f"report {run['id']}, version {run['version']}; {len(inventory)} objects. "
                "This PDF references the inventory companion; it does not contain the full inventory."
            }
        )
    # Even companion mode retains evidence-object destinations; filenames and
    # complete statuses stay in the separately authorized inventory.
    per_object = not derived or mode == "embedded"
    for obj in inventory.values() if per_object else ():
        if companion:
            if obj["id"] in affected:
                appendix.append(
                    {
                        "id": "object-" + obj["id"],
                        "heading": obj["id"],
                        "level": 2,
                        "paragraph": "See this object ID in the complete companion inventory.",
                    }
                )
            continue
        appendix.append(
            {
                "id": "object-" + obj["id"],
                "heading": obj["id"] + " — " + obj["name"],
                "level": 2,
                **({"outline": False} if derived else {}),
                "paragraph": "Type: "
                + obj["type"]
                + ". Location/version: "
                + obj.get("source", "Not available"),
                "table": {
                    "data": [["Check", "Status", "Method or reason"]]
                    + [
                        [
                            checks[c["id"]]["label"],
                            c["status"].replace("_", " "),
                            _check_description(c),
                        ]
                        for c in obj["checks"]
                    ],
                    "col_widths_frac": [0.3, 0.2, 0.5],
                },
            }
        )
        if "size_bytes" in obj or obj.get("facts"):
            size = obj.get("size_bytes")
            values = (
                [
                    [
                        "Size" if derived else "Size (bytes)",
                        _formatting()["format_size"](size) if derived else size,
                    ]
                ]
                if "size_bytes" in obj
                else []
            )
            values.extend([[k, v] for k, v in obj.get("facts", {}).items()])
            appendix.append({"table": {"data": [["Observed fact", "Value"], *values]}})
        if obj.get("url"):
            appendix.append(
                {
                    "table": {
                        "data": [
                            ["Source"],
                            [{"text": "Open source object", "url": obj["url"]}],
                        ]
                    }
                }
            )
    appendix.append(
        {
            "id": "glossary",
            "heading": (
                "Appendix D — Terms used" if derived else "Appendix C — Terms used"
            ),
            "bullets": [
                "Enumerated: the object appeared in the completed portion of the scope listing.",
                "Checked: the specified method completed; this does not mean compliant.",
                "Partial: only the stated portion was inspected; the remainder was not assessed.",
                "Finding: an evidence-backed observation that needs the stated response or validation.",
                "Priority: the recommended order of response and its rationale, not a regulatory rating.",
                "Confidence: how well the available evidence supports the observation.",
                "Partial assessment: enumeration or one or more applicable checks remain incomplete.",
            ],
        }
    )
    if derived and layout == "brief":
        appendix.pop()
    prepared = {
        "summary": summary,
        "body": body,
        "appendix": appendix,
        "status": status,
        "counts": counts,
        "object_count": len(inventory),
        "affected_count": len(affected),
        "assessed_label": _display_timestamp(run["assessed_at"]),
        "generated_label": _display_timestamp(run["generated_at"]),
    }
    if derived:
        for key in ("coverage", "status_explanation", "cover", "metrics"):
            prepared[key] = derived[key]
    if findings_view is not None:
        prepared["findings_view"] = findings_view
    return prepared


def export_assessment(data, output_format, legal_footer, scope_caveat):
    """Render a full inventory CSV or narrative text from the validated record."""
    prepared = prepare_assessment(data, view="txt" if output_format == "txt" else "pdf")
    if output_format == "csv":
        output = StringIO(newline="")
        output.write("# " + " ".join(legal_footer.splitlines()) + "\n")
        run = data["run"]
        provenance = (
            f"{scope_caveat} | Report: {run['id']}; version: {run['version']}; "
            f"scope: {run['scope']}; assessed: {run['assessed_at']}; "
            f"generated: {run['generated_at']}; {prepared['status']}; "
            f"enumeration complete: {run['enumeration_complete']}; "
            "unvisited scope: " + ("; ".join(run["unvisited_scope"]) or "None recorded")
        )
        output.write("# " + " ".join(provenance.splitlines()) + "\n\n")
        writer = csv.writer(output)

        def safe(value):
            text = str(value)
            return (
                "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
            )

        findings = data.get("findings") or []
        actions = data.get("actions") or []
        checks = data["checks"]
        per_finding = len(findings) <= 50
        declared = []
        for check in checks:
            for key in check.get("fact_keys", []):
                if key not in declared:
                    declared.append(key)
        free_labels = sorted(
            {
                label
                for obj in data["inventory"]
                for label in obj.get("facts", {})
                if label not in declared
            }
        )
        headers = [
            "Report ID",
            "Version",
            "Record type",
            "Record ID",
            "Name",
            "Type",
            "Source",
            "Source URL",
            "Size (bytes)",
            "Size status",
            "Finding IDs",
        ]
        if per_finding:
            headers.extend("Finding " + f["id"] for f in findings)
        headers.extend("Fact: " + key for key in declared)
        headers.extend("Fact: " + label for label in free_labels)
        for check in checks:
            headers.extend([check["id"] + " status", check["id"] + " method or reason"])
        headers.extend(
            [
                "Priority",
                "Priority rationale",
                "Observation",
                "Impact",
                "Recommendation",
                "Confidence",
                "Criterion",
                "Affected objects",
                "Object IDs",
                "Action status",
                "Owner",
                "Target",
                "Basis",
                "Verification",
                "Completed at",
            ]
        )
        seen_headers = set()
        for name in headers:
            if name in seen_headers:
                raise ValueError("CSV header collision: " + name)
            seen_headers.add(name)
        index = {name: i for i, name in enumerate(headers)}

        def new_row(rtype, rid, name, linked):
            row = [""] * len(headers)
            row[0] = data["run"]["id"]
            row[1] = data["run"]["version"]
            row[2] = rtype
            row[3] = rid
            row[4] = name
            row[index["Finding IDs"]] = ";" + ";".join(linked) + ";" if linked else ""
            if per_finding:
                for fid in linked:
                    row[index["Finding " + fid]] = "yes"
            return row

        by_object = {}
        for finding in findings:
            for oid in finding["object_ids"]:
                by_object.setdefault(oid, []).append(finding["id"])
        writer.writerow(headers)
        rows = []
        for obj in data["inventory"]:
            row = new_row(
                "object", obj["id"], obj["name"], by_object.get(obj["id"], [])
            )
            row[5] = obj["type"]
            row[6] = obj.get("source", "Not available")
            row[7] = obj.get("url", "Not available")
            row[8] = obj["size_bytes"] if "size_bytes" in obj else ""
            row[9] = "measured" if "size_bytes" in obj else "not measured"
            facts = obj.get("facts", {})
            for label in declared + free_labels:
                row[index["Fact: " + label]] = facts.get(label, "Not available")
            states = {c["id"]: c for c in obj["checks"]}
            for check in checks:
                state = states[check["id"]]
                row[index[check["id"] + " status"]] = state["status"]
                row[index[check["id"] + " method or reason"]] = _check_description(
                    state
                )
            rows.append(row)
        for finding in findings:
            row = new_row("finding", finding["id"], finding["title"], [finding["id"]])
            for column, key in (
                ("Priority", "priority"),
                ("Priority rationale", "priority_reason"),
                ("Observation", "observation"),
                ("Impact", "impact"),
                ("Recommendation", "recommendation"),
                ("Confidence", "confidence"),
                ("Criterion", "criterion"),
            ):
                row[index[column]] = finding.get(key, "")
            row[index["Affected objects"]] = len(finding["object_ids"])
            row[index["Object IDs"]] = ";" + ";".join(finding["object_ids"]) + ";"
            rows.append(row)
        for action in actions:
            row = new_row(
                "action",
                action["id"],
                action["action"],
                action.get("finding_ids") or [],
            )
            row[index["Action status"]] = action["status"]
            for column, key in (
                ("Owner", "owner"),
                ("Target", "target"),
                ("Basis", "basis"),
                ("Verification", "verification"),
                ("Completed at", "completed_at"),
            ):
                row[index[column]] = action.get(key, "")
            rows.append(row)
        for row in rows:
            writer.writerow([safe(value) for value in row])
        return output.getvalue()
    if output_format != "txt":
        raise ValueError("export format must be csv or txt")
    lines = []
    for section in prepared["summary"] + prepared["body"] + prepared["appendix"]:
        if section.get("heading"):
            lines.extend(["", section["heading"]])
        if section.get("paragraph"):
            lines.append(section["paragraph"])
        lines.extend("- " + text for text in section.get("bullets", []))
        for row in section.get("table", {}).get("data", []):
            lines.append(
                " | ".join(
                    (str(cell.get("text", "")) + " (" + str(cell.get("url", "")) + ")")
                    if isinstance(cell, dict)
                    else str(cell)
                    for cell in row
                )
            )
    lines.extend(["", scope_caveat, legal_footer])
    return "\n".join(lines).strip() + "\n"
