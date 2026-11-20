"""Universal Tracker check: generate a seed from a YAML, then regenerate it the way UT does (a blank YAML plus
re_gen_passthrough = slot_data) and confirm the location set, starting items and logic agree.
Run with the APLocalTracker venv python."""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
AP_SRC = pathlib.Path("C:/Games/APLocalTracker/ap_src")
sys.path.insert(0, str(AP_SRC))
os.chdir(AP_SRC)
import ModuleUpdate  # noqa: E402
ModuleUpdate.update = lambda *a, **k: None
import Generate  # noqa: E402
import Main  # noqa: E402
from BaseClasses import CollectionState  # noqa: E402


def gen(yaml_text: str, passthrough=None):
    ydir = tempfile.mkdtemp(prefix="arc_ut_")
    (pathlib.Path(ydir) / "p.yaml").write_text(yaml_text)
    sys.argv = ["Generate.py", "--player_files_path", ydir, "--seed", "7", "--skip_output",
                "--outputpath", tempfile.mkdtemp(), "--log_level", "warning"]
    args, seed = Generate.main()
    if passthrough is not None:
        import worlds.AutoWorld as AW
        orig = AW.World.generate_early

        def patched_main(a, s):
            return Main.main(a, s)
        # UT sets multiworld.re_gen_passthrough before generation; emulate by patching MultiWorld creation.
        import BaseClasses
        orig_init = BaseClasses.MultiWorld.__init__

        def init(self, *a, **k):
            orig_init(self, *a, **k)
            self.re_gen_passthrough = {"ARC Raiders": passthrough}
        BaseClasses.MultiWorld.__init__ = init
        try:
            return Main.main(args, seed)
        finally:
            BaseClasses.MultiWorld.__init__ = orig_init
    return Main.main(args, seed)


real_yaml = ("name: Arc\ngame: ARC Raiders\nARC Raiders:\n  goal: both\n  extraction_checks: 13\n"
             "  map_extraction_checks: 3\n  core_hunt_count: 12\n  new_quest_checks: 7\n  hideout_upgrade_checks: 4\n"
             "  starting_maps: 2\n  starting_weapon_classes: 3\n  logic_difficulty: sweaty\n  value_goal: 750000\n")
blank_yaml = "name: Arc\ngame: ARC Raiders\nARC Raiders: {}\n"

real = gen(real_yaml)
slot_data = real.worlds[1].fill_slot_data()
regen = gen(blank_yaml, passthrough=slot_data)

locs = lambda mw: sorted(l.name for l in mw.get_locations(1))  # noqa: E731
start = lambda mw: sorted(i.name for i in mw.precollected_items[1])  # noqa: E731
ok = True
for label, a, b in (("locations", locs(real), locs(regen)), ("starting items", start(real), start(regen))):
    same = a == b
    ok &= same
    print(("PASS " if same else "FAIL ") + f"{label}: {len(a)} vs {len(b)}")

# logic: with the same item set, the same locations must be reachable
state_r, state_g = CollectionState(real), CollectionState(regen)
for name in ["Progressive Weapon Rarity", "Progressive Shields", "Progressive Healing"]:
    state_r.collect(real.worlds[1].create_item(name), True)
    state_g.collect(regen.worlds[1].create_item(name), True)
reach = lambda mw, st: sorted(l.name for l in mw.get_locations(1) if l.can_reach(st))  # noqa: E731
same = reach(real, state_r) == reach(regen, state_g)
ok &= same
print(("PASS " if same else "FAIL ") + f"logic: {len(reach(real, state_r))} reachable with 3 kit items")
print("ALL PASSED" if ok else "FAILED")
sys.exit(0 if ok else 1)
