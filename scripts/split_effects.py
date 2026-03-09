"""Split monolithic effect files into individual card files.

Reads the existing oath/cards/effects/{suit}.py files and the canonical
oath_cards.json, then generates one .py file per card in the new folder
structure:
    oath/cards/effects/denizens/{suit}/card_name.py
    oath/cards/effects/sites/card_name.py
    oath/cards/effects/relics/card_name.py
    oath/cards/effects/edifices/card_name.py
    oath/cards/effects/visions/card_name.py

Usage:
    python scripts/split_effects.py          # Generate new files
    python scripts/split_effects.py --dry-run  # Preview without writing
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EFFECTS_DIR = PROJECT_ROOT / "oath" / "cards" / "effects"
CARD_DATA_JSON = PROJECT_ROOT / "scripts" / "card_data" / "oath_cards.json"

SUIT_FILES = {
    "order": EFFECTS_DIR / "order.py",
    "arcane": EFFECTS_DIR / "arcane.py",
    "discord": EFFECTS_DIR / "discord.py",
    "hearth": EFFECTS_DIR / "hearth.py",
    "beast": EFFECTS_DIR / "beast.py",
    "nomad": EFFECTS_DIR / "nomad.py",
}
SPECIAL_FILES = {
    "relics": EFFECTS_DIR / "relics.py",
    "edifices": EFFECTS_DIR / "edifices.py",
}


def load_card_data() -> dict:
    with open(CARD_DATA_JSON) as f:
        cards = json.load(f)
    return {c["leder_id"]: c for c in cards}


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[''']", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    if s and s[0].isdigit():
        s = "card_" + s
    return s


def extract_register_blocks(filepath: Path) -> list[dict]:
    """Parse a Python effect file and extract blocks between register_effect calls.

    Each block includes the functions + registration call for one card.
    """
    source = filepath.read_text(encoding="utf-8")
    lines = source.split("\n")

    # Find the end of the import header (first non-import, non-blank, non-comment
    # line that isn't part of an if TYPE_CHECKING block)
    header_end = 0
    in_type_checking = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "if TYPE_CHECKING:":
            in_type_checking = True
            continue
        if in_type_checking:
            if stripped and not stripped.startswith(("from ", "import ", "#")):
                in_type_checking = False
                header_end = i
                break
            continue
        if stripped == "" or stripped.startswith(("#", "from ", "import ", '"""', "'''")):
            continue
        if stripped.startswith("def ") or stripped.startswith("# ──"):
            header_end = i
            break
        header_end = i

    # Also capture the header for extracting shared imports
    header_lines = lines[:header_end]

    # Find all register_effect line positions
    reg_positions = []
    for i, line in enumerate(lines):
        if "register_effect(" in line and not line.strip().startswith("#"):
            # Find end of this call (balanced parens)
            end = _find_paren_end(lines, i)
            reg_positions.append((i, end))

    if not reg_positions:
        return []

    blocks = []
    for idx, (reg_start, reg_end) in enumerate(reg_positions):
        # Block starts right after previous register_effect end (or header end)
        if idx == 0:
            block_start = header_end
        else:
            block_start = reg_positions[idx - 1][1] + 1

        # Block ends at reg_end
        block_lines = lines[block_start:reg_end + 1]

        # Strip leading/trailing blank lines
        while block_lines and not block_lines[0].strip():
            block_lines.pop(0)
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()

        # Extract card_id from register_effect call
        reg_text = "\n".join(lines[reg_start:reg_end + 1])
        m = re.search(r"register_effect\(\s*(\d+)", reg_text)
        if not m:
            continue
        card_id = int(m.group(1))

        blocks.append({
            "card_id": card_id,
            "source_lines": "\n".join(block_lines),
            "header_lines": header_lines,
        })

    return blocks


def _find_paren_end(lines: list[str], start: int) -> int:
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0:
            return i
    return len(lines) - 1


def build_id_to_leder_map() -> dict[int, str]:
    sys.path.insert(0, str(PROJECT_ROOT))
    from oath.cards.database import OATH_ID_TO_INTERNAL
    return {v: k for k, v in OATH_ID_TO_INTERNAL.items()}


def _detect_imports(source: str) -> set[str]:
    known_helpers = {
        "always_true", "has_rule", "is_role", "has_min_favor", "has_min_secrets",
        "player_rules_site", "count_ruled_sites",
        "gain_favor", "gain_favor_from_banks", "gain_secrets",
        "spend_favor", "spend_secrets", "burn_favor", "burn_secrets",
        "gain_warbands", "place_warbands_at_site", "kill_warbands",
        "gain_supply",
    }
    return {h for h in known_helpers if h in source}


def _detect_enum_imports(source: str) -> set[str]:
    enums = set()
    if "EffectTrigger." in source:
        enums.add("EffectTrigger")
    if "ModifierType." in source:
        enums.add("ModifierType")
    if "Role." in source:
        enums.add("Role")
    if "Suit." in source:
        enums.add("Suit")
    if "MAX_SITES" in source:
        enums.add("MAX_SITES")
    if "MAX_ADVISERS" in source:
        enums.add("MAX_ADVISERS")
    return enums


def _detect_other_imports(source: str) -> list[str]:
    """Detect additional imports needed (e.g., get_card from database)."""
    extras = []
    if "get_card(" in source:
        extras.append("from oath.cards.database import get_card")
    return extras


def generate_card_file(
    card_id: int,
    card_info: dict | None,
    source_block: str,
    leder_id: str | None,
) -> str:
    name = card_info["name"] if card_info else f"Card {card_id}"
    card_type = card_info["type"] if card_info else "unknown"
    suit = card_info["suit"] if card_info else None

    docstring = f'"""{name}'
    if leder_id:
        docstring += f" ({leder_id})"
    docstring += f" — {card_type.title()}"
    if suit:
        docstring += f" ({suit.title()})"
    docstring += '."""'

    imports = _detect_imports(source_block)
    enum_imports = _detect_enum_imports(source_block)
    other_imports = _detect_other_imports(source_block)

    header = f"{docstring}\n"
    header += "from __future__ import annotations\n"
    header += "from typing import TYPE_CHECKING\n\n"
    header += "from oath.cards.effects._base import register_effect, CardEffect\n"

    if enum_imports:
        header += f"from oath.enums import {', '.join(sorted(enum_imports))}\n"

    if imports:
        header += f"from oath.cards.effects._helpers import {', '.join(sorted(imports))}\n"

    for imp in other_imports:
        header += f"{imp}\n"

    header += "\nif TYPE_CHECKING:\n"
    header += "    from oath.state.game_state import GameState\n"
    header += "\n\n"

    return header + source_block + "\n"


def main():
    parser = argparse.ArgumentParser(description="Split effect files into per-card modules")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    card_data = load_card_data()
    id_to_leder = build_id_to_leder_map()

    all_blocks: dict[int, tuple[str, str]] = {}

    for suit, filepath in {**SUIT_FILES, **SPECIAL_FILES}.items():
        if not filepath.exists():
            print(f"WARN: {filepath} not found, skipping")
            continue
        blocks = extract_register_blocks(filepath)
        print(f"  {filepath.name}: {len(blocks)} effects extracted")
        for block in blocks:
            all_blocks[block["card_id"]] = (block["source_lines"], suit)

    print(f"\nTotal effects extracted: {len(all_blocks)}")

    dirs_to_create = [
        EFFECTS_DIR / "denizens",
        EFFECTS_DIR / "denizens" / "order",
        EFFECTS_DIR / "denizens" / "arcane",
        EFFECTS_DIR / "denizens" / "discord",
        EFFECTS_DIR / "denizens" / "hearth",
        EFFECTS_DIR / "denizens" / "beast",
        EFFECTS_DIR / "denizens" / "nomad",
        EFFECTS_DIR / "sites",
        EFFECTS_DIR / "relics",
        EFFECTS_DIR / "edifices",
        EFFECTS_DIR / "visions",
    ]

    if not args.dry_run:
        for d in dirs_to_create:
            d.mkdir(parents=True, exist_ok=True)

    files_created = 0
    dir_modules: dict[str, list[str]] = {}

    for card_id, (source_block, source_file) in sorted(all_blocks.items()):
        leder_id = id_to_leder.get(card_id)
        card_info = card_data.get(leder_id) if leder_id else None

        if card_info:
            card_type = card_info["type"]
            suit = card_info["suit"]
            name = card_info["name"]
        else:
            if source_file in SUIT_FILES:
                card_type = "denizen"
                suit = source_file
            elif source_file == "relics":
                card_type = "relic"
                suit = None
            elif source_file == "edifices":
                card_type = "edifice"
                suit = None
            else:
                card_type = "unknown"
                suit = None
            name = f"card_{card_id}"

        filename = slugify(name) + ".py"

        if card_type == "denizen" and suit:
            dest_dir = EFFECTS_DIR / "denizens" / suit
        elif card_type == "site":
            dest_dir = EFFECTS_DIR / "sites"
        elif card_type == "relic":
            dest_dir = EFFECTS_DIR / "relics"
        elif card_type == "edifice":
            dest_dir = EFFECTS_DIR / "edifices"
        elif card_type == "vision":
            dest_dir = EFFECTS_DIR / "visions"
        else:
            dest_dir = EFFECTS_DIR / "denizens" / (suit or "unknown")

        dest_file = dest_dir / filename
        content = generate_card_file(card_id, card_info, source_block, leder_id)

        dir_key = str(dest_dir)
        if dir_key not in dir_modules:
            dir_modules[dir_key] = []
        dir_modules[dir_key].append(filename)

        if args.dry_run:
            print(f"  Would create: {dest_file.relative_to(PROJECT_ROOT)}")
        else:
            dest_file.write_text(content, encoding="utf-8")
            files_created += 1

    # Generate __init__.py for each leaf directory
    for dir_str, modules in dir_modules.items():
        dir_path = Path(dir_str)
        init_path = dir_path / "__init__.py"
        lines = ['"""Auto-generated: imports all card effect modules to trigger registration."""\n']
        for mod in sorted(modules):
            mod_name = mod.removesuffix(".py")
            lines.append(f"from . import {mod_name}  # noqa: F401")
        init_content = "\n".join(lines) + "\n"

        if not args.dry_run:
            init_path.write_text(init_content, encoding="utf-8")

    # Generate denizens/__init__.py
    if not args.dry_run:
        denizens_init = EFFECTS_DIR / "denizens" / "__init__.py"
        content = '"""Auto-generated: imports all suit packages."""\n'
        for suit in ["order", "arcane", "discord", "hearth", "beast", "nomad"]:
            content += f"from . import {suit}  # noqa: F401\n"
        denizens_init.write_text(content, encoding="utf-8")

    # Generate new top-level __init__.py
    new_init = '''"""Card effects package for Oath simulator."""

from oath.cards.effects._base import (
    CardEffect,
    CARD_EFFECTS,
    register_effect,
    get_effects,
    get_action_effects,
    get_modifier_effects,
    get_battle_plan_effects,
    get_when_played_effects,
    get_wake_effects,
    get_rest_effects,
    get_persistent_effects,
)

# Import all effect modules to trigger registration
from oath.cards.effects import denizens  # noqa: F401
from oath.cards.effects import sites  # noqa: F401
from oath.cards.effects import relics  # noqa: F401
from oath.cards.effects import edifices  # noqa: F401
from oath.cards.effects import visions  # noqa: F401

__all__ = [
    'CardEffect',
    'CARD_EFFECTS',
    'register_effect',
    'get_effects',
    'get_action_effects',
    'get_modifier_effects',
    'get_battle_plan_effects',
    'get_when_played_effects',
    'get_wake_effects',
    'get_rest_effects',
    'get_persistent_effects',
]
'''

    if args.dry_run:
        print(f"\nDry run complete. {len(all_blocks)} card files would be created.")
    else:
        new_init_path = EFFECTS_DIR / "__init__.py.new"
        new_init_path.write_text(new_init, encoding="utf-8")
        print(f"\nCreated {files_created} card files")
        print(f"New __init__.py written to {new_init_path}")
        print(f"\nTo switch over:")
        print(f"  1. Review generated files")
        print(f"  2. Rename __init__.py.new -> __init__.py")
        print(f"  3. Delete old flat files (order.py, discord.py, etc.)")
        print(f"  4. Run pytest to verify")


if __name__ == "__main__":
    main()
