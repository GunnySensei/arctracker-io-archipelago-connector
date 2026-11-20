"""Minimal arctracker.io REST client (stdlib only). Blocking; call through asyncio.to_thread."""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://arctracker.io"


class ArcApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class ArcTrackerAPI:
    def __init__(self, app_key: str, user_key: str):
        self.app_key, self.user_key = app_key.strip(), user_key.strip()
        self.remaining = None   # X-RateLimit-Remaining from the last response
        self.reset_at = None    # X-RateLimit-Reset (unix seconds)
        self.calls = 0

    def _get(self, path: str, **params) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(f"{BASE}{path}{'?' + query if query else ''}", headers={
            "X-App-Key": self.app_key, "Authorization": "Bearer " + self.user_key,
            "Accept": "application/json", "User-Agent": "arc-raiders-archipelago/0.4"})
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                self._note_limits(r.headers)
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            self._note_limits(e.headers)
            try:
                msg = json.loads(e.read()).get("error", {}).get("message", e.reason)
            except Exception:
                msg = str(e.reason)
            raise ArcApiError(e.code, msg) from None

    def _note_limits(self, headers) -> None:
        if headers is None:
            return
        if headers.get("X-RateLimit-Remaining") is not None:
            self.remaining = int(headers["X-RateLimit-Remaining"])
        if headers.get("X-RateLimit-Reset") is not None:
            self.reset_at = int(float(headers["X-RateLimit-Reset"]))

    def rounds(self, limit: int = 50, offset: int = 0) -> tuple:
        """Returns (rounds newest first, total)."""
        d = self._get("/api/v2/user/rounds", limit=limit, offset=offset, sort="newest")["data"]
        return d.get("rounds") or [], (d.get("pagination") or {}).get("total", 0)

    def stash(self) -> tuple:
        """Returns (all stash items, syncedAt). One call unless the stash has more than 500 stacks."""
        items, synced = [], None
        for page in range(1, 4):
            d = self._get("/api/v2/user/stash", per_page=500, page=page)["data"]
            items += d.get("items") or []
            synced = synced or d.get("syncedAt")
            if page >= ((d.get("pagination") or {}).get("totalPages") or 1):
                break
        return items, synced

    def progress(self, kind: str) -> dict:
        """kind: quests | blueprints | hideout | projects"""
        return self._get(f"/api/v2/user/{kind}")["data"]

    def loadout(self) -> dict:
        return self._get("/api/v2/user/loadout")["data"]
