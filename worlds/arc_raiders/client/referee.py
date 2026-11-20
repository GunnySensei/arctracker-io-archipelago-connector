"""Compare a synced /user/loadout with what the player has unlocked. Pure; returns human-readable warnings.
Note: arctracker captures the loadout when it syncs (after a raid), so used consumables may already be gone."""
import json
import pkgutil

from .. import data as D

RARITY_NAMES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
HEAL_LIMITS = [2, 4, 6, 10, None]          # by Progressive Healing tier (None = unlimited)
HEAL_RARITY = [0, 1, 2, 4, 4]               # max heal rarity by tier
THROW_LIMITS = [0, 2, 5, None]              # by Progressive Throwables tier
AUGMENT_RARITY = [0, 1, 2, 4]               # by Progressive Augment tier

_items = None


def item_table() -> dict:
    global _items
    if _items is None:
        raw = pkgutil.get_data(D.__name__.rsplit(".", 1)[0], "assets/referee_items.json")
        _items = json.loads(raw.decode("utf-8"))
    return _items


def _carried(loadout: dict) -> list:
    """Every (itemId, quantity) in quick slots, backpack and safe pocket."""
    out = []
    for key in ("quickItems", "backpack", "safePocket", "augmentedSlots", "other"):
        for entry in loadout.get(key) or []:
            if entry and entry.get("itemId"):
                out.append((entry["itemId"], int(entry.get("quantity") or 1), entry.get("name") or entry["itemId"]))
    return out


def check(loadout: dict, tiers: dict, licenses: set) -> list:
    """tiers: progressive item name -> copies received. licenses: weapon class names unlocked."""
    t = {n: tiers.get(n, 0) for n in D.PROGRESSIVE}
    table = item_table()
    warns = []

    shield = loadout.get("shield")
    if shield and shield.get("itemId"):
        need = table["shields"].get(shield["itemId"], 3)
        if need > t[D.SHIELDS]:
            warns.append(f"{shield.get('name')} needs Shields tier {need} (you have {t[D.SHIELDS]}).")

    weapons = [w for w in (loadout.get("weapon1"), loadout.get("weapon2")) if w and w.get("itemId")]
    if len(weapons) > 1 and t[D.SLOTS] < 1:
        warns.append("Two weapons equipped, but you only have 1 weapon slot.")
    for w in weapons:
        info = table["weapons"].get(w["itemId"])
        if not info:
            continue
        if info["rarity"] > t[D.RARITY]:
            warns.append(f"{info['name']} is {RARITY_NAMES[info['rarity']]}; your rarity cap is "
                         f"{RARITY_NAMES[t[D.RARITY]]}.")
        if info["tier"] - 1 > t[D.TIER]:
            warns.append(f"{info['name']} is tier {info['tier']}; your cap is tier {t[D.TIER] + 1}.")
        if info["class"] not in licenses:
            warns.append(f"{info['name']} is a {info['class']}; you don't have that license.")

    heals = throws = 0
    for iid, qty, name in _carried(loadout):
        if iid in table["heals"]:
            heals += qty
            if table["heals"][iid] > HEAL_RARITY[t[D.HEALING]]:
                warns.append(f"{name} is above your heal rarity cap ({RARITY_NAMES[HEAL_RARITY[t[D.HEALING]]]}).")
        elif iid in table["throwables"]:
            throws += qty
    limit = HEAL_LIMITS[t[D.HEALING]]
    if limit is not None and heals > limit:
        warns.append(f"Carrying {heals} heals; your limit is {limit}.")
    limit = THROW_LIMITS[t[D.THROWABLES]]
    if limit is not None and throws > limit:
        warns.append(f"Carrying {throws} grenades/mines; your limit is {limit}.")

    aug = loadout.get("augment")
    if aug and aug.get("itemId") in table["augments"]:
        r = table["augments"][aug["itemId"]]
        if r > AUGMENT_RARITY[t[D.AUGMENT]]:
            warns.append(f"{aug.get('name')} is {RARITY_NAMES[r]}; your augment cap is "
                         f"{RARITY_NAMES[AUGMENT_RARITY[t[D.AUGMENT]]]}.")
    return warns
