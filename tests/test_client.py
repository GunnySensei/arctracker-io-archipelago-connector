"""Offline tests for the client's evaluator and referee against saved arctracker.io fixtures.
Runs inside the AP source tree (venv python) against the *built* apworld in ap_src/custom_worlds.
Usage: C:/Games/APLocalTracker/venv/Scripts/python.exe tests/test_client.py"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
AP_SRC = pathlib.Path("C:/Games/APLocalTracker/ap_src")
sys.path.insert(0, str(AP_SRC))
os.chdir(AP_SRC)
import ModuleUpdate  # noqa: E402
ModuleUpdate.update = lambda *a, **k: None
import worlds  # noqa: E402,F401  (loads custom_worlds/arc_raiders.apworld)
from worlds.arc_raiders import data as D  # noqa: E402
from worlds.arc_raiders.client import evaluator, referee  # noqa: E402

ROUNDS = json.loads((FIX / "rounds.json").read_text(encoding="utf-8"))["data"]["rounds"]
LOADOUT = json.loads((FIX / "loadout.json").read_text(encoding="utf-8"))["data"]["loadout"]
SLOT = {
    "value_goal": 500_000, "value_metric": "extracted", "milestone_step": 50_000, "milestone_count": 10,
    "extraction_checks": 20, "map_extraction_checks": 2, "raid_value_checks": True, "arc_kill_checks": True,
    "maps": {slug: name for slug, name in D.MAPS},
    "raid_value_tiers": {label: v for v, label, _ in D.RAID_VALUE_TIERS},
    "arc_kill_tiers": [n for n, _ in D.ARC_KILL_TIERS],
}
failures = 0


def check(cond: bool, msg: str) -> None:
    global failures
    print(("PASS " if cond else "FAIL ") + msg)
    failures += 0 if cond else 1


# --- evaluator: baseline before every fixture round -> independent recount
base = "2026-01-01T00:00:00+00:00"
p = evaluator.evaluate(SLOT, ROUNDS, base)
live = [r for r in ROUNDS if not r["isLegacy"]]
ext = [r for r in live if r["outcome"] == "extracted"]
check(p.extractions == len(ext), f"extractions {p.extractions} == {len(ext)}")
check(p.total_value == sum(r["valueExtracted"] for r in ext), f"extracted value {p.total_value:,}")
check(p.arc_kills == sum(r["arcKills"] for r in live), f"arc kills {p.arc_kills}")
check(p.best_raid == max(r["valueExtracted"] for r in ext), f"best raid {p.best_raid:,}")
check(len(p.deaths) == sum(1 for r in live if r["outcome"] == "died"), f"deaths {len(p.deaths)}")
check(all(n in D.all_location_names() for n in p.locations), f"all {len(p.locations)} location names exist")
check(D.extraction_name(min(len(ext), 20)) in p.locations, "highest extraction check present")
check(D.extraction_name(len(ext) + 1) not in p.locations, "no extraction check beyond count")
check(p.goal_done == (p.total_value >= 500_000), "goal flag matches total")

# --- net metric includes deaths as negatives
pn = evaluator.evaluate({**SLOT, "value_metric": "net"}, ROUNDS, base)
check(pn.total_value == sum(r["netValue"] for r in live), f"net value {pn.total_value:,}")

# --- baseline after everything -> nothing counts
late = evaluator.evaluate(SLOT, ROUNDS, "2026-12-01T00:00:00+00:00")
check(not late.locations and late.extractions == 0, "late baseline counts nothing")

# --- backlog rule: a round synced after the baseline but played days before must not count
old = dict(ROUNDS[0], id="backlog", roundEndedAt="2026-11-01T00:00:00.000Z", syncedAt="2026-11-15T00:00:00.000Z")
check(not evaluator.eligible_rounds([old], "2026-11-10T00:00:00+00:00"), "late-synced backlog ignored")

# --- cores
STASH = json.loads((FIX / "stash.json").read_text(encoding="utf-8"))["data"]["items"]
CSLOT = {**SLOT, "goal": "core_hunt", "core_hunt_count": 3, "require_boss_core": True, "core_checks_per_type": 2,
         "cores": [list(c) for c in D.CORES], "core_aliases": D.CORE_ALIASES}
counts = evaluator.count_cores(CSLOT, STASH, LOADOUT)
expect = {}
for e in STASH:
    iid = D.CORE_ALIASES.get(e["itemId"], e["itemId"])
    if iid in {c[0] for c in D.CORES}:
        expect[iid] = expect.get(iid, 0) + e["quantity"]
check(counts == expect and counts.get("wasp_driver") == 8, f"stash core counts {counts}")
check("fireball_burner" in counts, "fireball burner counted")
after = dict(counts, rocketeer_driver=counts.get("rocketeer_driver", 0) + 2, tick_pod=1, wasp_driver=1)
gain = evaluator.core_gain(counts, after)
check(gain == {"rocketeer_driver": 2, "tick_pod": 1}, f"gain counts only increases {gain}")
check(evaluator.count_cores(CSLOT, [{"itemId": "damaged_tick_pod", "quantity": 2}], None) == {"tick_pod": 2},
      "damaged variant folds into base core")
looted = {"rocketeer_driver": 3, "tick_pod": 1, "wasp_driver": 1}
pc = evaluator.evaluate(CSLOT, ROUNDS, base, looted)
check({"Loot a Rocketeer Driver #1", "Loot a Rocketeer Driver #2", "Loot a Tick Pod #1"} <= pc.locations
      and "Loot a Rocketeer Driver #3" not in pc.locations and "Loot a Tick Pod #2" not in pc.locations,
      "core checks capped per type")
check(not pc.goal_done, "3 types but no boss -> core goal not met")
pc2 = evaluator.evaluate(CSLOT, ROUNDS, base, {**looted, "matriarch_reactor": 1})
check(pc2.goal_done, "with Matriarch Reactor -> core goal met")
both = evaluator.evaluate({**CSLOT, "goal": "both"}, ROUNDS, base, {**looted, "matriarch_reactor": 1})
check(not both.goal_done, "goal=both still needs the value goal")

# --- stale-snapshot backlog (what actually happened 2026-11-20: stash last synced Nov 12, connected ~20:00,
#     one sync at 21:20 brought tonight's raid plus 7 older ones)
night = [
    {"syncedAt": "2026-11-20T21:20:00.000Z", "roundEndedAt": "2026-11-20T21:14:00.000Z"},
    {"syncedAt": "2026-11-20T21:20:00.000Z", "roundEndedAt": "2026-11-19T05:24:00.000Z"},
]
check(evaluator.backlog_in_sync(night, "2026-11-12T03:49:08.397Z", "2026-11-20T21:20:00.000Z",
                                "2026-11-20T20:00:00+00:00"), "backlog in first sync -> re-snapshot")
check(not evaluator.backlog_in_sync(night[:1], "2026-11-12T03:49:08.397Z", "2026-11-20T21:20:00.000Z",
                                    "2026-11-20T20:00:00+00:00"), "only post-baseline raid -> credit")
check(not evaluator.backlog_in_sync(night, "2026-11-20T21:20:00.000Z", "2026-11-20T22:00:00.000Z",
                                    "2026-11-20T20:00:00+00:00"), "rounds from an earlier sync don't count again")

# --- new-progress checks (quests / blueprints / hideout / projects)
P = {k: json.loads((FIX / f"{k}.json").read_text(encoding="utf-8"))["data"]
     for k in ("quests", "blueprints", "hideout", "projects")}
snap = evaluator.progress_snapshot(P["quests"], P["blueprints"], P["hideout"], P["projects"])
check(len(snap["quest"]) == sum(q["completed"] for q in P["quests"]["quests"]), f"{len(snap['quest'])} quests done")
check(len(snap["blueprint"]) == sum(b["learned"] for b in P["blueprints"]["blueprints"]),
      f"{len(snap['blueprint'])} blueprints learned")
check(evaluator.progress_gain(snap, snap) == {}, "same snapshot -> no gain")
later = json.loads(json.dumps(snap))
todo = next(q["id"] for q in P["quests"]["quests"] if not q["completed"])
later["quest"].append(todo)
mod = next(iter(later["hideout"]))
later["hideout"][mod] += 1
later["project"].append("expedition_project:99")
g = evaluator.progress_gain(snap, later)
check(g == {"quest": 1, "hideout": 1, "project": 1}, f"progress gain {g}")
PSLOT = {**SLOT, "progress_checks": {"quest": 5, "blueprint": 3, "hideout": 2, "project": 0},
         "progress_labels": {k: lab for k, lab, _ in D.NEW_PROGRESS}}
pp = evaluator.evaluate(PSLOT, ROUNDS, base, None, {"quest": 2, "hideout": 4, "project": 3})
check({"New Quest Completed #1", "New Quest Completed #2", "Hideout Upgrade #1", "Hideout Upgrade #2"} <= pp.locations
      and "Hideout Upgrade #3" not in pp.locations and not any("Project Phase" in n for n in pp.locations),
      "progress checks capped and disabled kinds ignored")
check(all(n in D.all_location_names() for n in pp.locations), "progress location names exist")

# --- referee
zero = referee.check(LOADOUT, {}, set())
check(len(zero) >= 5, f"empty unlocks -> {len(zero)} warnings")
for w in zero:
    print("      ", w)
full = referee.check(LOADOUT, dict(D.PROGRESSIVE), set(D.WEAPON_CLASSES))
check(full == [], f"full unlocks -> no warnings {full}")

print(f"\n{'ALL PASSED' if not failures else f'{failures} FAILED'}")
sys.exit(1 if failures else 0)
