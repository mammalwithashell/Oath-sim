#!/usr/bin/env python3
"""Build canonical data/cards_manifest.json for all 259 playable Oath cards.

Maps Leder IDs OATH-001..OATH-259 directly to canonical integer IDs 1..259:
  1..198   : Denizens
  199..210 : Edifices (odd = intact, even = ruined)
  211..231 : Relics (231 = The Grand Scepter)
  232..236 : Visions (232 = Conspiracy, 233..236 = Exiles' Visions)
  237..259 : Sites
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_JSON = ROOT / "scripts" / "card_data" / "oath_cards.json"
OUT_JSON = ROOT / "data" / "cards_manifest.json"

# Verified site metadata: (starting_relics, starting_favor, starting_secrets, recover_cost_favor, recover_cost_secrets, defense, is_coast)
# Defense values match official site silhouettes (bandits + defense dice).
SITE_META: dict[int, dict] = {
    237: {"starting_relics": 1, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 2, "recover_secrets": 0, "defense": 2, "is_coast": False},  # Ancient City
    238: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": True},   # Barren Coast
    239: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 1, "recover_secrets": 1, "defense": 2, "is_coast": False},  # Buried Giant
    240: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Charming Valley
    241: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 0, "recover_favor": 2, "recover_secrets": 0, "defense": 2, "is_coast": False},  # Deep Woods
    242: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 2, "recover_favor": 0, "recover_secrets": 1, "defense": 2, "is_coast": False},  # Drowned City
    243: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Fertile Valley
    244: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Great Slum
    245: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 2, "is_coast": False},  # The Tribunal
    246: {"starting_relics": 1, "starting_favor": 2, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": True},   # Lush Coast
    247: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 0, "recover_secrets": 1, "defense": 2, "is_coast": False},  # Marshes
    248: {"starting_relics": 1, "starting_favor": 2, "starting_secrets": 0, "recover_favor": 2, "recover_secrets": 0, "defense": 2, "is_coast": False},  # Mine
    249: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 2, "recover_secrets": 0, "defense": 3, "is_coast": False},  # Mountain
    250: {"starting_relics": 0, "starting_favor": 0, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 4, "is_coast": False},  # Narrow Pass
    251: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Plains
    252: {"starting_relics": 1, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # River
    253: {"starting_relics": 1, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 2, "is_coast": True},   # Rocky Coast
    254: {"starting_relics": 1, "starting_favor": 1, "starting_secrets": 1, "recover_favor": 1, "recover_secrets": 0, "defense": 2, "is_coast": False},  # Salt Flats
    255: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 0, "recover_secrets": 1, "defense": 3, "is_coast": False},  # Shrouded Wood
    256: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 0, "recover_secrets": 1, "defense": 2, "is_coast": False},  # Standing Stones
    257: {"starting_relics": 0, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Steppe
    258: {"starting_relics": 1, "starting_favor": 0, "starting_secrets": 1, "recover_favor": 0, "recover_secrets": 1, "defense": 2, "is_coast": False},  # The Hidden Place
    259: {"starting_relics": 1, "starting_favor": 1, "starting_secrets": 0, "recover_favor": 1, "recover_secrets": 0, "defense": 1, "is_coast": False},  # Wastes
}

# Verified placement restrictions from official Oath cards (Tree = site_only, Person = adviser_only, Chain = locked)
SITE_ONLY_IDS = {
    3, 5, 7, 13, 27, 29, 34, 42, 47, 51, 56, 61, 64, 71, 76, 82, 87, 92, 95,
    102, 108, 113, 119, 124, 131, 136, 141, 148, 154, 161, 168, 174, 181, 188, 194,
}
ADVISER_ONLY_IDS = {
    9, 19, 26, 43, 52, 58, 67, 74, 83, 91, 98, 105, 112, 121, 129, 138, 145, 152, 164, 177, 185,
}
LOCKED_IDS = {
    199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210,  # All edifices are locked
}


def infer_battle_plan_side(tags: list[str], text: str) -> str:
    if "Battle Plan" not in tags:
        return "none"
    low = text.lower()
    if "±" in text or "either" in low:
        return "either"
    if "if this site is targeted" in low or "attacker's" in low or "attacker " in low or "when defending" in low:
        return "defender"
    if "defender's" in low or "defender " in low or "when attacking" in low:
        return "attacker"
    if "+ `symbol:diceb`" in low or "+2 `symbol:diceb`" in low or "+3 `symbol:diceb`" in low:
        return "defender"
    if "+ `symbol:dicer`" in low or "+2 `symbol:dicer`" in low or "+3 `symbol:dicer`" in low:
        return "attacker"
    return "either"


def infer_costs(card_id: int, tags: list[str], text: str) -> dict:
    # Base costs inferred from card text / iconography conventions.
    # Specific overrides can be added cleanly here.
    low = text.lower()
    cost_favor = 0
    cost_secrets = 0
    cost_burn_favor = 0
    cost_burn_secrets = 0
    if "burn `symbol:secret` `symbol:secret`" in low:
        cost_burn_secrets = 2
    elif "burn `symbol:secret`" in low or "burn one `symbol:secret`" in low:
        cost_burn_secrets = 1
    if "burn `symbol:favor` `symbol:favor`" in low:
        cost_burn_favor = 2
    elif "burn `symbol:favor`" in low or "burn one `symbol:favor`" in low:
        cost_burn_favor = 1
    if "spend `symbol:secret`" in low or "pay `symbol:secret`" in low:
        cost_secrets = 1
    if "spend `symbol:favor`" in low or "pay `symbol:favor`" in low:
        cost_favor = 1
    return {
        "cost_favor": cost_favor,
        "cost_secrets": cost_secrets,
        "cost_burn_favor": cost_burn_favor,
        "cost_burn_secrets": cost_burn_secrets,
    }


def main() -> None:
    raw = json.loads(SRC_JSON.read_text())
    playable = [c for c in raw if c["type"] != "reference"]
    playable.sort(key=lambda c: int(c["leder_id"].split("-")[1]))

    manifest = []
    for c in playable:
        cid = int(c["leder_id"].split("-")[1])
        ctype = c["type"]
        text = c.get("effect_text") or ""
        tags = c.get("effect_tags") or []
        meta = c.get("meta") or {}

        restriction = "none"
        if cid in LOCKED_IDS or "locked" in text.lower():
            restriction = "locked"
        elif cid in SITE_ONLY_IDS:
            restriction = "site_only"
        elif cid in ADVISER_ONLY_IDS:
            restriction = "adviser_only"

        edifice_is_ruined = ctype == "edifice" and (cid % 2 == 0)
        edifice_flip_id = None
        if ctype == "edifice":
            edifice_flip_id = cid - 1 if edifice_is_ruined else cid + 1

        site_info = SITE_META.get(cid, {})
        defense = site_info.get("defense", meta.get("defense") or 0)
        capacity = meta.get("card_capacity") if meta.get("card_capacity") is not None else 0

        costs = infer_costs(cid, tags, text)

        entry = {
            "id": cid,
            "leder_id": c["leder_id"],
            "name": c["name"],
            "card_type": ctype,
            "suit": None if edifice_is_ruined else c.get("suit"),
            "edifice_suit": c.get("suit") if ctype == "edifice" else None,
            "restriction": restriction,
            "capacity": capacity,
            "defense": defense,
            "starting_relics": site_info.get("starting_relics", 0),
            "starting_favor": site_info.get("starting_favor", 0),
            "starting_secrets": site_info.get("starting_secrets", 0),
            "recover_favor": site_info.get("recover_favor", 0),
            "recover_secrets": site_info.get("recover_secrets", 0),
            "is_coast": site_info.get("is_coast", False),
            "edifice_is_ruined": edifice_is_ruined,
            "edifice_flip_id": edifice_flip_id,
            "battle_plan_side": infer_battle_plan_side(tags, text),
            "effect_tags": tags,
            "effect_text": text,
            **costs,
        }
        manifest.append(entry)

    assert len(manifest) == 259, f"Expected 259 cards, got {len(manifest)}"
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(manifest)} cards to {OUT_JSON}")


if __name__ == "__main__":
    main()
