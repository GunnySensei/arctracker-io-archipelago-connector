"""One-shot API spike: calls each user endpoint once, saves raw JSON to tests/fixtures. Never prints keys."""
import json, pathlib, sys, urllib.request, urllib.error
ROOT = pathlib.Path(__file__).resolve().parent.parent
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.lstrip().startswith("#"))
app, user = env.get("ARC_APP_KEY", "").strip(), env.get("ARC_USER_KEY", "").strip()
if not app.startswith("arc_k1_") or not user.startswith("arc_u1_"):
    sys.exit(f"key format check failed: app={'ok' if app.startswith('arc_k1_') else 'bad'} user={'ok' if user.startswith('arc_u1_') else 'bad'}")
out = ROOT / "tests" / "fixtures"
calls = {
    "profile": "/api/v2/user/profile",
    "rounds": "/api/v2/user/rounds?limit=20",
    "stash": "/api/v2/user/stash?per_page=500",
    "loadout": "/api/v2/user/loadout",
    "quests": "/api/v2/user/quests",
    "blueprints": "/api/v2/user/blueprints",
    "hideout": "/api/v2/user/hideout",
    "projects": "/api/v2/user/projects",
}
for name, path in calls.items():
    req = urllib.request.Request("https://arctracker.io" + path, headers={
        "X-App-Key": app, "Authorization": "Bearer " + user, "User-Agent": "arc-ap-client/0.1", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body, code, rem = r.read(), r.status, r.headers.get("X-RateLimit-Remaining")
    except urllib.error.HTTPError as e:
        body, code, rem = e.read(), e.code, e.headers.get("X-RateLimit-Remaining")
    (out / f"{name}.json").write_bytes(body)
    print(f"{name:10} {code} {len(body):>8}B remaining={rem}")
