"""Light generation smoke test: one single-player seed per YAML in test_gen/players, each in its own process.
Usage: python -I tools/test_gen.py            (runs every yaml)
       python -I tools/test_gen.py --one NAME (runs one yaml, used internally)"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
AP_SRC = pathlib.Path("C:/Games/APLocalTracker/ap_src")
VENV_PY = pathlib.Path("C:/Games/APLocalTracker/venv/Scripts/python.exe")
PLAYERS = ROOT / "test_gen" / "players"
OUT = ROOT / "test_gen" / "out"


def run_one(yaml_name: str) -> None:
    sys.path.insert(0, str(AP_SRC))
    os.chdir(AP_SRC)
    import ModuleUpdate
    ModuleUpdate.update = lambda *a, **k: None  # skip AP's interactive auto-installer
    import Generate
    import Main
    ydir = tempfile.mkdtemp(prefix="arc_players_")
    (pathlib.Path(ydir) / yaml_name).write_bytes((PLAYERS / yaml_name).read_bytes())
    OUT.mkdir(parents=True, exist_ok=True)
    sys.argv = ["Generate.py", "--player_files_path", ydir, "--seed", "1", "--spoiler", "2",
                "--outputpath", str(OUT), "--log_level", "warning"]
    args, seed = Generate.main()
    mw = Main.main(args, seed)
    locs = [l for l in mw.get_locations() if l.address is not None]
    spheres = list(mw.get_spheres())
    traps = sum(1 for l in locs if l.item.trap)
    print(f"OK {yaml_name}: {len(locs)} checks, {len(spheres)} spheres, {traps} traps, "
          f"start={sorted(i.name for i in mw.precollected_items[1])}")


def main() -> None:
    if "--one" in sys.argv:
        run_one(sys.argv[sys.argv.index("--one") + 1])
        return
    failed = 0
    for y in sorted(PLAYERS.glob("*.yaml")):
        r = subprocess.run([str(VENV_PY), __file__, "--one", y.name], capture_output=True, text=True,
                           timeout=180, stdin=subprocess.DEVNULL)
        line = next((l for l in r.stdout.splitlines() if l.startswith("OK ")), None)
        expect_fail = y.name.startswith("fail_")
        if expect_fail and r.returncode != 0 and "OptionError" in r.stdout + r.stderr:
            print(f"OK {y.name}: rejected as expected")
        elif not expect_fail and r.returncode == 0 and line:
            print(line)
        else:
            failed += 1
            print(f"FAIL {y.name} (exit {r.returncode})\n" + "\n".join((r.stdout + r.stderr).splitlines()[-15:]))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
