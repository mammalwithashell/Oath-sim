"""Process Oath card data from the LederCards GitHub repo.

Downloads the official YAML card data and card images, then produces
a canonical JSON file (scripts/card_data/oath_cards.json) for use
as the source of truth when implementing card effects.

Usage:
    python scripts/process_card_data.py              # Parse YAML only
    python scripts/process_card_data.py --download   # Also download images
    python scripts/process_card_data.py --diff       # Compare against database.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
YAML_URL = (
    "https://raw.githubusercontent.com/LederCards/cards/master/"
    "content/card-data/oath/en-US/oathbasegame.yml"
)
IMAGE_BASE_URL = (
    "https://raw.githubusercontent.com/LederCards/cards/master/"
    "content/card-images/oath/en-US/"
)

SCRIPT_DIR = Path(__file__).resolve().parent
CARD_DATA_DIR = SCRIPT_DIR / "card_data"
YAML_PATH = CARD_DATA_DIR / "oathbasegame.yml"
JSON_PATH = CARD_DATA_DIR / "oath_cards.json"
IMAGE_DIR = CARD_DATA_DIR / "images"

SUITS = {"Order", "Arcane", "Beast", "Discord", "Hearth", "Nomad"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_yaml():
    """Download the YAML if not already present."""
    CARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not YAML_PATH.exists():
        print(f"Downloading {YAML_URL} ...")
        urllib.request.urlretrieve(YAML_URL, YAML_PATH)
        print(f"  -> {YAML_PATH}")
    else:
        print(f"Using cached {YAML_PATH}")


def load_yaml() -> list[dict]:
    """Load the YAML card data (requires PyYAML)."""
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required. Install with: pip install pyyaml")
        sys.exit(1)
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def classify_card(tags: set[str]) -> str:
    """Determine card type from tags."""
    if "Reference" in tags:
        return "reference"
    if "Site" in tags:
        return "site"
    if "Relic" in tags:
        return "relic"
    if "Edifice" in tags:
        return "edifice"
    if "Vision" in tags:
        return "vision"
    if tags & SUITS:
        return "denizen"
    return "unknown"


def get_suit(tags: set[str]) -> str | None:
    """Extract suit from tags."""
    found = tags & SUITS
    return found.pop().lower() if found else None


def get_effect_tags(tags: set[str]) -> list[str]:
    """Extract effect-related tags (not type/suit/deck)."""
    skip = SUITS | {"Standard Deck", "Site", "Relic", "Edifice", "Vision", "Reference"}
    return sorted(t for t in tags if t not in skip)


def parse_card(raw: dict) -> dict:
    """Convert a raw YAML card entry to our canonical format."""
    tags = set(raw.get("tags", []))
    card_type = classify_card(tags)
    meta = raw.get("meta", {})

    return {
        "leder_id": raw["id"],
        "name": raw["name"],
        "type": card_type,
        "suit": get_suit(tags),
        "effect_text": raw.get("text", ""),
        "effect_tags": get_effect_tags(tags),
        "image_name": raw.get("image", raw["name"]),
        "image_class": raw.get("imageClass"),
        "meta": {
            "card_capacity": meta.get("cardcapacity"),
            "defense": meta.get("defense"),
        },
        "in_standard_deck": "Standard Deck" in tags,
    }


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_images(cards: list[dict], force: bool = False):
    """Download card images from GitHub."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    total = len(cards)
    downloaded = 0
    skipped = 0
    failed = 0

    for i, card in enumerate(cards, 1):
        image_name = card["image_name"]
        filename = f"{image_name}.png"
        dest = IMAGE_DIR / filename

        if dest.exists() and not force:
            skipped += 1
            continue

        url = IMAGE_BASE_URL + urllib.request.quote(filename)
        try:
            urllib.request.urlretrieve(url, dest)
            downloaded += 1
            if downloaded % 20 == 0:
                print(f"  [{i}/{total}] Downloaded {downloaded} images...")
        except urllib.error.HTTPError as e:
            # Try with .webp extension
            try:
                url_webp = IMAGE_BASE_URL + urllib.request.quote(f"{image_name}.webp")
                dest_webp = IMAGE_DIR / f"{image_name}.webp"
                urllib.request.urlretrieve(url_webp, dest_webp)
                downloaded += 1
            except urllib.error.HTTPError:
                print(f"  WARN: Failed to download {filename}: {e}")
                failed += 1

    print(f"Images: {downloaded} downloaded, {skipped} cached, {failed} failed")


# ---------------------------------------------------------------------------
# Diff against database.py
# ---------------------------------------------------------------------------

def diff_database(cards: list[dict]):
    """Compare scraped cards against the existing database.py."""
    # Import the database
    project_root = SCRIPT_DIR.parent
    sys.path.insert(0, str(project_root))
    from oath.cards.database import CARD_DB, OATH_ID_TO_INTERNAL

    # Build lookup from scraped data
    scraped = {c["leder_id"]: c for c in cards if c["type"] != "reference"}

    print("\n" + "=" * 60)
    print("DATABASE DIFF REPORT")
    print("=" * 60)

    # Cards in scraped but not in database
    missing_from_db = []
    for leder_id, card in scraped.items():
        if leder_id not in OATH_ID_TO_INTERNAL:
            missing_from_db.append(card)

    if missing_from_db:
        print(f"\n--- Cards in YAML but NOT in database ({len(missing_from_db)}) ---")
        for c in sorted(missing_from_db, key=lambda x: x["leder_id"]):
            print(f"  {c['leder_id']}: {c['name']} ({c['type']}, {c['suit'] or 'no suit'})")

    # Cards in database but not in scraped
    db_leder_ids = set(OATH_ID_TO_INTERNAL.keys())
    scraped_ids = set(scraped.keys())
    extra_in_db = db_leder_ids - scraped_ids
    if extra_in_db:
        print(f"\n--- Cards in database but NOT in YAML ({len(extra_in_db)}) ---")
        for lid in sorted(extra_in_db):
            internal_id = OATH_ID_TO_INTERNAL[lid]
            db_card = CARD_DB[internal_id]
            print(f"  {lid} (internal {internal_id}): {db_card.name}")

    # Name mismatches
    mismatches = []
    for leder_id, card in scraped.items():
        if leder_id in OATH_ID_TO_INTERNAL:
            internal_id = OATH_ID_TO_INTERNAL[leder_id]
            db_card = CARD_DB[internal_id]
            if db_card.name.lower() != card["name"].lower():
                mismatches.append((leder_id, db_card.name, card["name"]))

    if mismatches:
        print(f"\n--- Name mismatches ({len(mismatches)}) ---")
        for lid, db_name, yaml_name in mismatches:
            print(f"  {lid}: DB='{db_name}' vs YAML='{yaml_name}'")

    # Summary
    print(f"\nYAML cards (excl. reference): {len(scraped)}")
    print(f"Database cards: {len(CARD_DB)}")
    print(f"Mapped (OATH_ID_TO_INTERNAL): {len(OATH_ID_TO_INTERNAL)}")

    if not missing_from_db and not extra_in_db and not mismatches:
        print("\nAll cards match!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Process Oath card data")
    parser.add_argument("--download", action="store_true", help="Download card images")
    parser.add_argument("--force-download", action="store_true", help="Re-download all images")
    parser.add_argument("--diff", action="store_true", help="Compare against database.py")
    parser.add_argument("--refresh", action="store_true", help="Re-download YAML from GitHub")
    args = parser.parse_args()

    if args.refresh and YAML_PATH.exists():
        YAML_PATH.unlink()

    ensure_yaml()
    raw_cards = load_yaml()
    print(f"Loaded {len(raw_cards)} cards from YAML")

    cards = [parse_card(c) for c in raw_cards]

    # Summary
    from collections import Counter
    type_counts = Counter(c["type"] for c in cards)
    print(f"\nCard types:")
    for t, count in type_counts.most_common():
        print(f"  {t}: {count}")

    suit_counts = Counter(c["suit"] for c in cards if c["suit"])
    print(f"\nSuits:")
    for s, count in suit_counts.most_common():
        print(f"  {s}: {count}")

    # Write JSON
    CARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {JSON_PATH}")

    if args.download or args.force_download:
        print("\nDownloading card images...")
        download_images(cards, force=args.force_download)

    if args.diff:
        diff_database(cards)


if __name__ == "__main__":
    main()
