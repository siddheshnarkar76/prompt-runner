"""
Seed canonical rules for multiple cities into MongoDB.
- Cities covered: Mumbai, Ahmedabad, Pune, Nashik
- Safe to run multiple times (idempotent upsert by city + clause_no)

Usage:
  python -m scripts.seed_rules --cities Mumbai Pune
  python -m scripts.seed_rules --force   # drop existing city rules before seeding
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

from mcp.db import Collections, get_database

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ----------------------------------------------------------------------------
# Seed data
# ----------------------------------------------------------------------------
SEED_RULES: Dict[str, List[Dict[str, object]]] = {
    "Mumbai": [
        {
            "clause_no": "3.1",
            "summary": "Maximum building height for mid-rise residential blocks is 24 m.",
            "full_text": "Residential mid-rise structures shall not exceed 24 meters in total height including parapet.",
            "rule_type": "height",
            "parsed_fields": {"height_m": 24.0},
            "category": "height",
        },
        {
            "clause_no": "3.2",
            "summary": "Minimum front setback for buildings up to 30 m road width is 4.0 m.",
            "full_text": "A minimum front setback of four meters is required for plots abutting roads up to thirty meters wide.",
            "rule_type": "setback",
            "parsed_fields": {"setback_m": 4.0},
            "category": "setback",
        },
        {
            "clause_no": "3.3",
            "summary": "FSI cap for standard residential use is 2.0.",
            "full_text": "For standard residential developments the Floor Space Index shall not exceed two point zero.",
            "rule_type": "fsi",
            "parsed_fields": {"fsi": 2.0},
            "category": "fsi",
        },
    ],
    "Ahmedabad": [
        {
            "clause_no": "4.1",
            "summary": "Maximum permissible building height in residential zones is 18 m.",
            "full_text": "The total height of residential buildings in designated zones shall not exceed eighteen meters.",
            "rule_type": "height",
            "parsed_fields": {"height_m": 18.0},
            "category": "height",
        },
        {
            "clause_no": "4.2",
            "summary": "Front setback requirement is minimum 3.0 m.",
            "full_text": "A minimum front setback of three meters is mandatory for all residential plots.",
            "rule_type": "setback",
            "parsed_fields": {"setback_m": 3.0},
            "category": "setback",
        },
        {
            "clause_no": "4.3",
            "summary": "FSI for plotted development shall not exceed 1.8.",
            "full_text": "For plotted residential development the Floor Space Index shall be limited to one point eight.",
            "rule_type": "fsi",
            "parsed_fields": {"fsi": 1.8},
            "category": "fsi",
        },
    ],
    "Pune": [
        {
            "clause_no": "5.1",
            "summary": "Maximum height for G+6 residential typology is 21 m.",
            "full_text": "Residential structures up to ground plus six floors shall not exceed twenty one meters in height.",
            "rule_type": "height",
            "parsed_fields": {"height_m": 21.0},
            "category": "height",
        },
        {
            "clause_no": "5.2",
            "summary": "Front setback minimum 3.5 m for collector roads.",
            "full_text": "Plots abutting collector roads shall maintain a front setback of at least three point five meters.",
            "rule_type": "setback",
            "parsed_fields": {"setback_m": 3.5},
            "category": "setback",
        },
        {
            "clause_no": "5.3",
            "summary": "FSI cap for mid-rise residential is 1.9.",
            "full_text": "Mid-rise residential developments shall adhere to a maximum Floor Space Index of one point nine.",
            "rule_type": "fsi",
            "parsed_fields": {"fsi": 1.9},
            "category": "fsi",
        },
    ],
    "Nashik": [
        {
            "clause_no": "6.1",
            "summary": "Maximum permissible building height is 16 m for standard plots.",
            "full_text": "Standard residential plots shall limit the total building height to sixteen meters.",
            "rule_type": "height",
            "parsed_fields": {"height_m": 16.0},
            "category": "height",
        },
        {
            "clause_no": "6.2",
            "summary": "Minimum setback on primary frontage is 3.0 m.",
            "full_text": "A minimum setback of three meters shall be maintained along the primary frontage of the plot.",
            "rule_type": "setback",
            "parsed_fields": {"setback_m": 3.0},
            "category": "setback",
        },
        {
            "clause_no": "6.3",
            "summary": "FSI shall not exceed 1.6 in designated residential areas.",
            "full_text": "In designated residential areas the Floor Space Index must be limited to one point six.",
            "rule_type": "fsi",
            "parsed_fields": {"fsi": 1.6},
            "category": "fsi",
        },
    ],
}


def _build_rule_doc(city: str, rule: Dict[str, object], now_iso: str) -> Dict[str, object]:
    """Normalize a seed rule into the canonical shape used across agents."""
    clause = str(rule.get("clause_no") or "seed")
    rule_id = f"{city.lower()}_{clause}".replace(" ", "_")
    parsed_fields = rule.get("parsed_fields") or {}
    return {
        "city": city,
        "rule_id": rule_id,
        "clause_no": clause,
        "summary": rule.get("summary"),
        "full_text": rule.get("full_text"),
        "rule_type": rule.get("rule_type"),
        "parsed_fields": parsed_fields,
        "parsed_data": parsed_fields,
        "category": rule.get("category"),
        "entitlements": rule.get("entitlements"),
        "conditions": rule.get("conditions") or rule.get("summary"),
        "notes": rule.get("notes"),
        "source": "seed_rules",
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def seed_rules(cities: Optional[List[str]] = None, force: bool = False) -> Dict[str, int]:
    """Insert or update seed rules for the selected cities."""
    db = get_database()
    rules_col = db[Collections.RULES]

    target_cities = cities or list(SEED_RULES.keys())
    now_iso = datetime.utcnow().isoformat() + "Z"

    if force:
        for city in target_cities:
            rules_col.delete_many({"city": city})
            logger.info("Cleared existing rules for %s", city)

    inserted = 0
    upserted = 0

    for city in target_cities:
        for rule in SEED_RULES.get(city, []):
            doc = _build_rule_doc(city, rule, now_iso)
            result = rules_col.update_one(
                {"city": city, "clause_no": doc["clause_no"]},
                {"$set": doc, "$setOnInsert": {"created_at": now_iso}},
                upsert=True,
            )
            if result.upserted_id is not None:
                inserted += 1
            else:
                upserted += 1
    logger.info("Seed complete: inserted=%d updated=%d", inserted, upserted)
    return {"inserted": inserted, "updated": upserted}


def ensure_seed_rules(city: str) -> None:
    """Ensure a city has baseline rules; seed if missing."""
    db = get_database()
    rules_col = db[Collections.RULES]
    existing = rules_col.count_documents({"city": city})
    if existing == 0:
        logger.info("No rules found for %s, seeding defaults", city)
        seed_rules([city])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed multi-city MCP rules")
    parser.add_argument("--cities", nargs="*", help="Cities to seed (default: all)")
    parser.add_argument("--force", action="store_true", help="Clear existing city rules before seeding")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    summary = seed_rules(cities=args.cities, force=args.force)
    logger.info("Seeding summary: %s", summary)
