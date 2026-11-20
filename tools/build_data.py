"""Build worlds/arc_raiders/data/referee_items.json from data_raw/items.json (public arctracker.io /api/items).
Only what the client's referee needs: weapons (rarity, class, tier), heals, throwables, shields, augments."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data_raw" / "items.json"
OUT = ROOT / "worlds" / "arc_raiders" / "assets" / "referee_items.json"

RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
NUMERALS = {"I": 1, "II": 2, "III": 3, "IV": 4}
# API weapon `type` -> our license names (data.WEAPON_CLASSES)
CLASS_MAP = {"Assault Rifle": "Assault Rifle", "Battle Rifle": "Battle Rifle", "SMG": "SMG", "Shotgun": "Shotgun",
             "Pistol": "Pistol", "Hand Cannon": "Hand Cannon", "Sniper Rifle": "Sniper Rifle", "LMG": "LMG",
             "Special": "Special"}


def en(v):
    return v.get("en") if isinstance(v, dict) else v


def main() -> None:
    items = json.loads(RAW.read_text(encoding="utf-8"))["items"]
    out = {"weapons": {}, "heals": {}, "throwables": {}, "shields": {}, "augments": {}}
    for it in items:
        iid, rarity = it["id"], RARITIES.index(it.get("rarity", "Common"))
        cat = ((it.get("mechanics") or {}).get("classification") or {}).get("category")
        name = en(it["name"]) or iid
        if it.get("isWeapon"):
            m = re.search(r"\s(I|II|III|IV)$", name)
            out["weapons"][iid] = {"name": name, "rarity": rarity, "class": CLASS_MAP.get(it.get("type"), "Special"),
                                   "tier": NUMERALS[m.group(1)] if m else 4}  # untiered (legendary) counts as IV
        elif cat == "Utility.Regenerative":
            out["heals"][iid] = rarity
        elif cat in ("Utility.Grenade", "Utility.Mine") and "light_stick" not in iid:
            out["throwables"][iid] = rarity
        elif it.get("type") == "Shield":
            out["shields"][iid] = {"light_shield": 1, "medium_shield": 2, "heavy_shield": 3}.get(iid, 3)
        elif cat == "Augment":
            out["augments"][iid] = rarity
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    print({k: len(v) for k, v in out.items()}, "->", OUT)


if __name__ == "__main__":
    main()
