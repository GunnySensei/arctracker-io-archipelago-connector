"""End-to-end smoke: generate the default test seed, host it on a private port, run the client headless for
~45s with a back-dated baseline, then shut everything down. Uses 2 arctracker.io calls (rounds + loadout).
Keys are read from .env into the child's environment only; nothing prints them."""
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
AP_SRC = pathlib.Path("C:/Games/APLocalTracker/ap_src")
PY = "C:/Games/APLocalTracker/venv/Scripts/python.exe"
OUT = ROOT / "test_gen" / "out"
PORT = "38999"
STUB = "import ModuleUpdate; ModuleUpdate.update = lambda *a, **k: None; import runpy, sys; "


def main() -> None:
    for f in OUT.glob("*"):
        f.unlink()
    subprocess.run([PY, str(ROOT / "tools" / "test_gen.py"), "--one", "a_default.yaml"], check=True,
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
    seed = next(OUT.glob("*.zip"))
    env = dict(os.environ)
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    env["ARC_TEST_BASELINE"] = "2026-01-01T00:00:00+00:00"

    log = open(OUT / "e2e_server.log", "w")
    server = subprocess.Popen([PY, "-c", STUB + f"sys.argv=['MultiServer.py','--host','127.0.0.1','--port','{PORT}',r'{seed}'];"
                               "runpy.run_path('MultiServer.py', run_name='__main__')"],
                              cwd=AP_SRC, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
    time.sleep(8)
    client = subprocess.Popen([PY, "-u", "-c", STUB + "sys.path.insert(0,'.'); import worlds; "
                               "from worlds.arc_raiders.client.launch import launch_arc_client; "
                               f"launch_arc_client('--nogui','--connect','localhost:{PORT}','--name','GunnyArc')"],
                              cwd=AP_SRC, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(35)
        import json
        import urllib.request
        try:
            state = json.load(urllib.request.urlopen("http://127.0.0.1:38300/state.json", timeout=5))
            page = urllib.request.urlopen("http://127.0.0.1:38300/", timeout=5).read()
            print(f"OVERLAY page {len(page)} bytes; kit={state.get('kit')} traps={len(state.get('traps', []))} "
                  f"cores={state.get('cores')} value={state.get('value')}")
            for e in state.get("events", [])[:5]:
                print(f"OVERLAY event [{e['kind']}] {e['title']} -> {e['text']}")
            first_trap = (state.get("traps") or [[None]])[0][0]
            if first_trap:
                req = urllib.request.Request("http://127.0.0.1:38300/action", method="POST",
                                             data=json.dumps({"kind": "done", "name": first_trap}).encode(),
                                             headers={"Content-Type": "application/json"})
                print("OVERLAY action done", first_trap, json.load(urllib.request.urlopen(req, timeout=5)))
                after = json.load(urllib.request.urlopen("http://127.0.0.1:38300/state.json", timeout=5))
                print("OVERLAY after action: last =", after.get("last_action"))
        except Exception as e:  # noqa: BLE001
            print("OVERLAY error:", e)
        time.sleep(2)
    finally:
        client.terminate()
        server.terminate()
    out = client.communicate(timeout=20)[0]
    server.wait(timeout=20)
    log.close()
    keep = [l for l in out.splitlines() if l.strip() and "UserWarning" not in l and "pkg_resources" not in l
            and "warnings.warn" not in l and "import pkg_resources" not in l]
    print("\n".join(keep[-60:]))


if __name__ == "__main__":
    sys.exit(main())
