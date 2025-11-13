"""
Utilities for computing diffs between enriched data versions.

Helps the AI understand what changed between summary generations.
"""
import json
from typing import Dict, Any, List, Set
from datetime import datetime


def compute_enriched_data_diff(
    old_data: Dict[str, Any],
    new_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute diff between two versions of enriched data.

    Returns a structured diff highlighting what changed.

    Args:
        old_data: Previous enriched data
        new_data: Current enriched data

    Returns:
        Dictionary with diff information
    """
    diff = {
        "summary": [],
        "details": {}
    }

    # Check primary record changes
    old_primary = old_data.get("primary_record", {})
    new_primary = new_data.get("primary_record", {})

    if old_primary != new_primary:
        primary_changes = _compare_records("primary_record", old_primary, new_primary)
        if primary_changes:
            diff["details"]["primary_record"] = primary_changes
            diff["summary"].append(f"Primary record updated: {', '.join(primary_changes['changed_fields'])}")

    # Check related entities changes
    old_entities = old_data.get("related_entities", {})
    new_entities = new_data.get("related_entities", {})

    for entity_type in ["contacts", "companies", "deals"]:
        old_list = old_entities.get(entity_type, [])
        new_list = new_entities.get(entity_type, [])

        entity_diff = _compare_entity_lists(entity_type, old_list, new_list)
        if entity_diff["has_changes"]:
            diff["details"][entity_type] = entity_diff
            diff["summary"].append(f"{entity_type.title()}: {entity_diff['summary']}")

    # Check interaction history changes
    old_history = old_data.get("interaction_history", {})
    new_history = new_data.get("interaction_history", {})

    history_diff = _compare_interaction_history(old_history, new_history)
    if history_diff["has_changes"]:
        diff["details"]["interaction_history"] = history_diff
        diff["summary"].extend(history_diff["summary_items"])

    # Overall summary
    if not diff["summary"]:
        diff["summary"] = ["No significant changes detected"]

    return diff


def _compare_records(
    record_type: str,
    old_record: Dict[str, Any],
    new_record: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare two individual records."""
    changes = {
        "changed_fields": [],
        "details": {}
    }

    # Get all keys
    all_keys = set(old_record.keys()) | set(new_record.keys())

    for key in all_keys:
        old_val = old_record.get(key)
        new_val = new_record.get(key)

        if old_val != new_val:
            changes["changed_fields"].append(key)
            changes["details"][key] = {
                "old": old_val,
                "new": new_val
            }

    return changes if changes["changed_fields"] else None


def _compare_entity_lists(
    entity_type: str,
    old_list: List[Dict[str, Any]],
    new_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare lists of entities (contacts, companies, deals)."""
    diff = {
        "has_changes": False,
        "summary": "",
        "added": [],
        "removed": [],
        "modified": []
    }

    # Extract IDs
    old_ids = {_get_entity_id(item) for item in old_list}
    new_ids = {_get_entity_id(item) for item in new_list}

    # Find added and removed
    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids

    if added_ids:
        diff["added"] = list(added_ids)
        diff["has_changes"] = True

    if removed_ids:
        diff["removed"] = list(removed_ids)
        diff["has_changes"] = True

    # Check for modifications in existing entities
    common_ids = old_ids & new_ids
    for entity_id in common_ids:
        old_item = next((item for item in old_list if _get_entity_id(item) == entity_id), None)
        new_item = next((item for item in new_list if _get_entity_id(item) == entity_id), None)

        if old_item and new_item and old_item != new_item:
            diff["modified"].append(entity_id)
            diff["has_changes"] = True

    # Build summary
    parts = []
    if added_ids:
        parts.append(f"{len(added_ids)} added")
    if removed_ids:
        parts.append(f"{len(removed_ids)} removed")
    if diff["modified"]:
        parts.append(f"{len(diff['modified'])} modified")

    diff["summary"] = ", ".join(parts) if parts else "No changes"

    return diff


def _compare_interaction_history(
    old_history: Dict[str, List[Dict[str, Any]]],
    new_history: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """Compare interaction history (notes, tasks)."""
    diff = {
        "has_changes": False,
        "summary_items": []
    }

    for interaction_type in ["notes", "tasks"]:
        old_items = old_history.get(interaction_type, [])
        new_items = new_history.get(interaction_type, [])

        old_ids = {item.get("id") for item in old_items if item.get("id")}
        new_ids = {item.get("id") for item in new_items if item.get("id")}

        added = new_ids - old_ids
        removed = old_ids - new_ids

        if added:
            diff["has_changes"] = True
            diff["summary_items"].append(f"{len(added)} new {interaction_type}")

        if removed:
            diff["has_changes"] = True
            diff["summary_items"].append(f"{len(removed)} {interaction_type} removed")

    return diff


def _get_entity_id(entity: Dict[str, Any]) -> str:
    """Extract entity ID from an entity record."""
    # Try different ID fields
    if "id" in entity:
        return str(entity["id"])
    elif "email" in entity:
        return entity["email"]
    else:
        # Fallback to hash of entity
        return str(hash(json.dumps(entity, sort_keys=True)))


def format_diff_for_ai(diff: Dict[str, Any]) -> str:
    """
    Format diff into human-readable text for AI prompt.

    Args:
        diff: Diff dictionary from compute_enriched_data_diff

    Returns:
        Formatted string describing changes
    """
    lines = ["# Changes Since Last Summary\n"]

    if not diff["summary"] or diff["summary"] == ["No significant changes detected"]:
        lines.append("**No significant changes detected in the data.**\n")
        return "\n".join(lines)

    # Overall summary
    lines.append("## Summary of Changes")
    for item in diff["summary"]:
        lines.append(f"- {item}")
    lines.append("")

    # Detailed changes
    details = diff.get("details", {})

    if "primary_record" in details:
        lines.append("## Primary Record Changes")
        changed_fields = details["primary_record"]["changed_fields"]
        lines.append(f"Fields updated: {', '.join(changed_fields)}")
        lines.append("")

    # Entity changes
    for entity_type in ["contacts", "companies", "deals"]:
        if entity_type in details:
            entity_diff = details[entity_type]
            lines.append(f"## {entity_type.title()} Changes")

            if entity_diff.get("added"):
                lines.append(f"- **Added ({len(entity_diff['added'])})**: {', '.join(str(id) for id in entity_diff['added'][:5])}")
                if len(entity_diff['added']) > 5:
                    lines.append(f"  ... and {len(entity_diff['added']) - 5} more")

            if entity_diff.get("removed"):
                lines.append(f"- **Removed ({len(entity_diff['removed'])})**: {', '.join(str(id) for id in entity_diff['removed'][:5])}")
                if len(entity_diff['removed']) > 5:
                    lines.append(f"  ... and {len(entity_diff['removed']) - 5} more")

            if entity_diff.get("modified"):
                lines.append(f"- **Modified**: {len(entity_diff['modified'])} {entity_type}")

            lines.append("")

    # Interaction history
    if "interaction_history" in details:
        hist_diff = details["interaction_history"]
        if hist_diff.get("summary_items"):
            lines.append("## Interaction History Changes")
            for item in hist_diff["summary_items"]:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)
