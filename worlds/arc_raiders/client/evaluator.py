"""Pure check evaluation: arctracker.io rounds + slot_data + baseline -> location names reached.
No network, no AP imports, so it can be tested directly against saved fixtures."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .. import data as D

# roundEndedAt is only accurate to the half hour, so allow that much slack before the baseline.
END_SLACK = timedelta(minutes=30)


def parse_time(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


@dataclass
class Progress:
    extractions: int = 0
    per_map: dict = field(default_factory=dict)
    best_raid: int = 0
    total_value: int = 0
    arc_kills: int = 0
    deaths: list = field(default_factory=list)  # round ids with outcome == died
    locations: set = field(default_factory=set)
    goal_done: bool = False


def eligible_rounds(rounds: list, baseline_iso: str) -> list:
    """Rounds that happened after the baseline: synced after it and ended no earlier than 30 min before it.
    The second rule keeps an old backlog that gets synced late from counting."""
    base = parse_time(baseline_iso)
    out = []
    for r in rounds:
        if r.get("isLegacy"):
            continue
        try:
            synced, ended = parse_time(r["syncedAt"]), parse_time(r["roundEndedAt"])
        except (KeyError, TypeError, ValueError):
            continue
        if synced > base and ended >= base - END_SLACK:
            out.append(r)
    return out


def count_cores(slot: dict, stash_items: list, loadout: dict | None) -> dict:
    """Total of each core (damaged variants folded in) across the stash and the carried loadout.
    Freshly looted items can still be in the backpack after a raid, so the loadout counts too."""
    core_ids = {c[0] for c in slot["cores"]}
    aliases = slot.get("core_aliases", {})
    entries = list(stash_items or [])
    if loadout:
        for key in ("backpack", "safePocket", "quickItems", "augmentedSlots", "other"):
            entries += [e for e in (loadout.get(key) or []) if e]
    out: dict = {}
    for e in entries:
        iid = aliases.get(e.get("itemId"), e.get("itemId"))
        if iid in core_ids:
            out[iid] = out.get(iid, 0) + int(e.get("quantity") or 1)
    return out


def core_gain(prev: dict, now: dict) -> dict:
    """Increases only. Selling, recycling or handing cores in only lowers counts, so it never creates credit."""
    return {k: now[k] - prev.get(k, 0) for k in now if now[k] > prev.get(k, 0)}


def progress_snapshot(quests: dict | None, blueprints: dict | None, hideout: dict | None,
                      projects: dict | None) -> dict:
    """JSON-able snapshot of account progress from the /user/quests, blueprints, hideout, projects payloads."""
    snap = {}
    if quests is not None:
        snap["quest"] = sorted(q["id"] for q in quests.get("quests", []) if q.get("completed"))
    if blueprints is not None:
        snap["blueprint"] = sorted(b["id"] for b in blueprints.get("blueprints", []) if b.get("learned"))
    if hideout is not None:
        snap["hideout"] = {m["id"]: int(m.get("currentLevel") or 0) for m in hideout.get("modules", [])}
    if projects is not None:
        snap["project"] = sorted(f"{p['id']}:{ph['phase']}" for p in projects.get("projects", [])
                                 for ph in p.get("phases", []) if ph.get("completed"))
    return snap


def progress_gain(prev: dict, now: dict) -> dict:
    """How many new completions per kind between two snapshots (kinds missing from either side count 0)."""
    gain = {}
    for kind in ("quest", "blueprint", "project"):
        if kind in prev and kind in now:
            gain[kind] = len(set(now[kind]) - set(prev[kind]))
    if "hideout" in prev and "hideout" in now:
        gain["hideout"] = sum(max(0, lvl - prev["hideout"].get(m, 0)) for m, lvl in now["hideout"].items())
    return {k: v for k, v in gain.items() if v}


def backlog_in_sync(rounds: list, prev_synced: str | None, now_synced: str, baseline_iso: str) -> bool:
    """True if the stash sync we're about to credit also brought in raids that ended before the baseline.
    Then the core increase mixes pre-baseline loot with post-baseline loot and can't be split, so the caller
    should re-snapshot instead of crediting. (Happens when someone connects with an out-of-date sync.)"""
    cutoff = parse_time(baseline_iso) - END_SLACK
    lo = parse_time(prev_synced) if prev_synced else None
    hi = parse_time(now_synced)
    for r in rounds:
        try:
            synced, ended = parse_time(r["syncedAt"]), parse_time(r["roundEndedAt"])
        except (KeyError, TypeError, ValueError):
            continue
        if (lo is None or synced > lo) and synced <= hi and ended < cutoff:
            return True
    return False


def core_goal_status(slot: dict, looted: dict) -> tuple:
    """(distinct types looted, boss looted?, goal met?)"""
    distinct = sum(1 for c in slot["cores"] if looted.get(c[0], 0) > 0)
    boss = any(looted.get(c[0], 0) > 0 for c in slot["cores"] if c[2] == "boss")
    met = distinct >= slot["core_hunt_count"] and (boss or not slot["require_boss_core"])
    return distinct, boss, met


def evaluate(slot: dict, rounds: list, baseline_iso: str, cores_looted: dict | None = None,
             progress_done: dict | None = None) -> Progress:
    p = Progress()
    cores_looted = cores_looted or {}
    progress_done = progress_done or {}
    slug_to_name = slot["maps"]
    for r in eligible_rounds(rounds, baseline_iso):
        extracted = r.get("outcome") == "extracted"
        p.arc_kills += int(r.get("arcKills") or 0)
        if slot["value_metric"] == "net":
            p.total_value += int(r.get("netValue") or 0)
        elif extracted:
            p.total_value += int(r.get("valueExtracted") or 0)
        if extracted:
            p.extractions += 1
            name = slug_to_name.get(r.get("map"))
            if name:
                p.per_map[name] = p.per_map.get(name, 0) + 1
            p.best_raid = max(p.best_raid, int(r.get("valueExtracted") or 0))
        elif r.get("outcome") == "died":
            p.deaths.append(r["id"])

    locs = p.locations
    locs.update(D.extraction_name(i) for i in range(1, min(p.extractions, slot["extraction_checks"]) + 1))
    for name, n in p.per_map.items():
        locs.update(D.map_extraction_name(name, i) for i in range(1, min(n, slot["map_extraction_checks"]) + 1))
    if slot["raid_value_checks"]:
        locs.update(D.raid_value_name(label) for label, v in slot["raid_value_tiers"].items() if p.best_raid >= v)
    reached = max(0, p.total_value) // slot["milestone_step"]
    locs.update(D.milestone_name(i) for i in range(1, min(reached, slot["milestone_count"]) + 1))
    if slot["arc_kill_checks"]:
        locs.update(D.kill_name(n) for n in slot["arc_kill_tiers"] if p.arc_kills >= n)
    per_type = slot.get("core_checks_per_type", 0)
    for iid, display, _ in slot.get("cores", []):
        locs.update(D.core_name(display, i) for i in range(1, min(cores_looted.get(iid, 0), per_type) + 1))

    for kind, cap in (slot.get("progress_checks") or {}).items():
        label = slot["progress_labels"][kind]
        locs.update(D.progress_name(label, i) for i in range(1, min(progress_done.get(kind, 0), cap) + 1))

    value_met = p.total_value >= slot["value_goal"]
    core_met = core_goal_status(slot, cores_looted)[2] if slot.get("cores") else False
    goal = slot.get("goal", "extracted_value")
    p.goal_done = {"extracted_value": value_met, "core_hunt": core_met, "both": value_met and core_met}[goal]
    return p
