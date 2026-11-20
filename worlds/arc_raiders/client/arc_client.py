"""ARC Raiders Archipelago client: polls arctracker.io, sends checks, tracks honor-system permissions."""
import asyncio
import json
import os
import time
import webbrowser
from datetime import datetime, timedelta, timezone

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, gui_enabled, logger, server_loop
from NetUtils import ClientStatus

from .. import data as D
from . import evaluator, referee
from .api import ArcApiError, ArcTrackerAPI

POLL_SECONDS = 120          # normal cadence: ~30 rounds calls/hour
SLOW_POLL_SECONDS = 600     # when the shared app key is running low
LOW_REMAINING = 60
MIN_MANUAL_GAP = 20
MAX_PAGES = 4
KEYS_FILE = "arc_raiders_keys.json"
STALE_SYNC = timedelta(hours=1)
SYNC_URL = "https://arctracker.io"
ITEM_NAMES = {D.ITEM_BASE + i: n for i, n in enumerate(D.all_item_names())}
LOCATION_IDS = {n: D.LOCATION_BASE + i for i, n in enumerate(D.all_location_names())}


def load_keys() -> tuple:
    app, user = os.environ.get("ARC_APP_KEY", ""), os.environ.get("ARC_USER_KEY", "")
    if app and user:
        return app, user
    try:
        with open(Utils.user_path(KEYS_FILE), encoding="utf-8") as f:
            d = json.load(f)
        return d.get("app_key", ""), d.get("user_key", "")
    except (OSError, ValueError):
        return "", ""


def save_keys(app: str, user: str) -> None:
    with open(Utils.user_path(KEYS_FILE), "w", encoding="utf-8") as f:
        json.dump({"app_key": app.strip(), "user_key": user.strip()}, f)


SETTINGS_FILE = "arc_raiders_client.json"
DEFAULT_SETTINGS = {"toasts": False, "voice": False, "overlay": True, "overlay_port": 38300, "overlay_lan": False}


def load_settings() -> dict:
    try:
        with open(Utils.user_path(SETTINGS_FILE), encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    with open(Utils.user_path(SETTINGS_FILE), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=1)


SHORT_CLASS = {"Assault Rifle": "AR", "Battle Rifle": "BR", "SMG": "SMG", "Shotgun": "SG", "Pistol": "Pst",
               "Hand Cannon": "HC", "Sniper Rifle": "SR", "LMG": "LMG", "Special": "Spec"}


def describe_item(name: str, tiers: dict) -> tuple:
    """(kind, short text) for a received item, used for toasts/voice/overlay events."""
    if name in D.TRAPS:
        return "trap", "Trap: " + name.replace(" Trap", "")
    if name in D.PROGRESSIVE:
        return "kit", f"{name.replace('Progressive ', '')}: {D.TIER_RULES[name][tiers.get(name, 0)]}"
    if name.startswith("Map Access: "):
        return "map", "Map unlocked: " + name.split(": ", 1)[1]
    if name.startswith("Weapon License: "):
        return "license", "License: " + name.split(": ", 1)[1]
    return "token", name


class ArcCommandProcessor(ClientCommandProcessor):
    ctx: "ArcContext"

    def _cmd_arc_status(self) -> bool:
        """Show ARC Raiders progress, permissions and pending traps."""
        for line in self.ctx.status_lines():
            logger.info(line)
        return True

    def _cmd_arc_poll(self) -> bool:
        """Check arctracker.io for new raids now."""
        self.ctx.request_poll()
        return True

    def _cmd_arc_sync(self) -> bool:
        """Open arctracker.io so you can sync your latest raids."""
        webbrowser.open("https://arctracker.io")
        return True

    def _cmd_arc_spend(self, *name: str) -> bool:
        """Spend a filler token, e.g. /arc_spend heal"""
        return self.ctx.use_queued(" ".join(name), D.FILLER_TOKENS, "tokens_spent", "Spent")

    def _cmd_arc_done(self, *name: str) -> bool:
        """Mark a trap as done after the raid, e.g. /arc_done pistol"""
        return self.ctx.use_queued(" ".join(name), D.TRAPS + ["DeathLink: No Heals"], "traps_cleared", "Cleared")

    def _cmd_arc_undo(self) -> bool:
        """Undo your last token spend or trap clear."""
        return self.ctx.undo_last()

    def _cmd_arc_overlay(self) -> bool:
        """Open the in-game overlay page (pin it in the Steam overlay browser with Shift+Tab)."""
        self.ctx.start_overlay()
        logger.info(f"Overlay: {self.ctx.overlay_url()}")
        webbrowser.open(self.ctx.overlay_url())
        return True

    def _cmd_arc_hud(self) -> bool:
        """Open the desktop HUD: a transparent always-on-top panel (needs borderless-windowed mode)."""
        self.ctx.open_hud()
        return True

    def _cmd_arc_toasts(self, on: str = "") -> bool:
        """Windows notifications for items, traps and checks: /arc_toasts on|off"""
        self.ctx.set_setting("toasts", on.lower() != "off")
        logger.info(f"Toasts {'on' if self.ctx.settings['toasts'] else 'off'}.")
        return True

    def _cmd_arc_voice(self, on: str = "") -> bool:
        """Spoken callouts for items and traps: /arc_voice on|off"""
        self.ctx.set_setting("voice", on.lower() != "off")
        logger.info(f"Voice {'on' if self.ctx.settings['voice'] else 'off'}.")
        return True


class ArcContext(CommonContext):
    game = D.GAME
    state_version = 0  # bumps on every visible change; the overlay long-polls on it

    @property
    def ui_dirty(self) -> bool:
        return self._ui_dirty

    @ui_dirty.setter
    def ui_dirty(self, value: bool) -> None:
        self._ui_dirty = value
        if value:
            self.state_version += 1
    items_handling = 0b111
    command_processor = ArcCommandProcessor

    def __init__(self, server_address=None, password=None):
        super().__init__(server_address, password)
        self.slot_data: dict = {}
        self.state: dict | None = None
        self.api: ArcTrackerAPI | None = None
        self.rounds: list = []
        self.progress: evaluator.Progress | None = None
        self.loadout: dict | None = None
        self.warnings: list = []
        self.last_poll = 0.0
        self.last_error = ""
        self.newest_round_id = None
        self.poll_wake = asyncio.Event()
        self.ui_dirty = True
        self.settings = load_settings()
        self.events: list = []          # [unix time, kind, text], newest last
        self.overlay_server = None
        self.stash_synced = None
        app, user = load_keys()
        if app and user:
            self.api = ArcTrackerAPI(app, user)

    # ------------------------------------------------------------------ AP plumbing
    @property
    def state_key(self) -> str:
        return f"arc_raiders_{self.team}_{self.slot}"

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.slot_data = args.get("slot_data") or {}
            asyncio.create_task(self.send_msgs([{"cmd": "Get", "keys": [self.state_key]}]))
            if self.slot_data.get("death_link"):
                asyncio.create_task(self.update_death_link(True))
        elif cmd == "Retrieved" and self.state_key in args.get("keys", {}):
            stored = args["keys"][self.state_key]
            if stored is None:
                now = datetime.now(timezone.utc).isoformat(timespec="seconds")
                now = os.environ.get("ARC_TEST_BASELINE") or now  # dev/testing only
                self.state = {"baseline": now, "deaths_sent": [], "tokens_spent": {}, "traps_cleared": {}}
                self.save_state()
                logger.info(f"ARC Raiders: baseline set to {now}. Only raids after this count. "
                            f"Sync your raids on arctracker.io as you play.")
            else:
                self.state = stored
                logger.info(f"ARC Raiders: resuming, baseline {stored['baseline']}.")
            self.request_poll()
        elif cmd == "ReceivedItems":
            self.refresh_warnings()
        if cmd in ("Connected", "Retrieved", "ReceivedItems", "RoomUpdate"):
            self.ui_dirty = True

    def on_print_json(self, args: dict) -> None:
        """Item movement messages from the server -> overlay pop-ups, toasts and voice.
        found:    one of *your* checks sent an item (to you or someone else)
        received: someone else's check sent *you* an item"""
        super().on_print_json(args)
        if args.get("type") not in ("ItemSend", "ItemCheat") or not self.slot:
            return
        try:
            item = args["item"]
            receiver = int(args.get("receiving", 0))
            finder = int(item.player)
            if self.slot not in (receiver, finder):
                return
            item_name = self.item_names.lookup_in_slot(item.item, receiver)
            loc_name = self.location_names.lookup_in_slot(item.location, finder)
            flags = int(item.flags)
        except (KeyError, AttributeError, TypeError, ValueError):
            return
        names = self.player_names
        if finder == self.slot and receiver == self.slot:
            kind, title = "found", f"Check: {loc_name}"
            kind_, detail = describe_item(item_name, self.tiers())
            text = detail if kind_ != "token" else item_name
        elif finder == self.slot:
            kind, title = "found", f"Check: {loc_name}"
            text = f"{item_name} for {names.get(receiver, '?')}"
        else:
            kind, title = "received", f"{names.get(finder, '?')} sent you"
            kind_, detail = describe_item(item_name, self.tiers())
            text = detail if kind_ != "token" else item_name
        if flags & 0b100 and receiver == self.slot:
            kind = "trap"
        self.notify(kind, text, title=title, flags=flags)

    # ------------------------------------------------------------------ notifications & overlay
    def notify(self, kind: str, text: str, title: str = "", flags: int = 0, announce: bool = True) -> None:
        self.event_seq = getattr(self, "event_seq", 0) + 1
        self.events.append({"t": time.time(), "kind": kind, "title": title, "text": text, "flags": flags,
                            "seq": self.event_seq})
        del self.events[:-30]
        if announce:
            self.announce(f"ARC Raiders: {title}" if title else "ARC Raiders", text,
                          speak=(f"{title}. {text}" if kind in ("received", "trap") else text))
        self.ui_dirty = True

    def announce(self, title: str, body: str, speak: str | None = None) -> None:
        """Queue a toast/voice line. Bursts within ~1.2s (a release, several checks from one raid) become one
        summary toast, so we never spawn dozens of notifications at once."""
        self._pending_announce = getattr(self, "_pending_announce", [])
        self._pending_announce.append((title, body, speak))
        if len(self._pending_announce) == 1:
            asyncio.get_event_loop().call_later(1.2, self._flush_announce)

    def _flush_announce(self) -> None:
        from . import notify as N
        pending, self._pending_announce = self._pending_announce, []
        if not pending:
            return
        traps = [p for p in pending if "TRAP" in p[0].upper() or p[1].startswith("Trap:")]
        if len(pending) == 1:
            title, body, speak = pending[0]
        else:
            lead = traps[0] if traps else pending[0]
            title = f"ARC Raiders: {len(pending)} updates"
            body = lead[1] + f"  (+{len(pending) - 1} more)"
            speak = (lead[2] or lead[1]) + f", and {len(pending) - 1} more"
        if self.settings.get("toasts"):
            N.toast(title, body)
        if self.settings.get("voice") and speak:
            N.speak(speak)

    def set_setting(self, key: str, value) -> None:
        self.settings[key] = value
        save_settings(self.settings)
        self.ui_dirty = True

    def open_hud(self) -> None:
        """Desktop HUD runs as a Tk thread inside this client (a separate AP process would cost ~190 MB more)."""
        self.start_overlay()
        if getattr(self, "hud_thread", None) and self.hud_thread.is_alive():
            logger.info("ARC Raiders: the desktop HUD is already open.")
            return
        import threading
        from .hud import run
        self.hud_thread = threading.Thread(
            target=run, args=(f"http://127.0.0.1:{self.settings['overlay_port']}", True),
            name="arc desktop hud", daemon=True)
        self.hud_thread.start()
        logger.info("ARC Raiders: desktop HUD opened. Drag the dotted corner to move it; right-click for options.")

    def overlay_url(self) -> str:
        return f"http://127.0.0.1:{self.settings['overlay_port']}/"

    def start_overlay(self) -> None:
        if self.overlay_server or not self.settings.get("overlay"):
            return
        from . import overlay_server
        try:
            self.overlay_server = overlay_server.start(self, asyncio.get_running_loop(),
                                                       int(self.settings["overlay_port"]),
                                                       bool(self.settings.get("overlay_lan")))
            logger.info(f"ARC Raiders: overlay at {self.overlay_url()} (open it in the Steam overlay browser "
                        f"with Shift+Tab and pin it).")
        except OSError as e:
            logger.warning(f"ARC Raiders: overlay couldn't start on port {self.settings['overlay_port']}: {e}")

    def overlay_state(self) -> dict:
        s = self.slot_data
        if not s:
            return {"connected": False}
        p, st = self.progress, self.state or {}
        tiers = self.tiers()
        short = {D.HEALING: "healing", D.SHIELDS: "shields", D.RARITY: "rarity", D.TIER: "tier",
                 D.THROWABLES: "throwables", D.AUGMENT: "augment", D.SLOTS: "slots"}
        now = time.time()
        recent_core = next((e["text"] for e in reversed(self.events) if e["kind"] == "core" and now - e["t"] < 180),
                           None)
        state = {
            "connected": True,
            "synced": max((r["syncedAt"] for r in self.rounds if r.get("syncedAt")), default=None),
            "stale": self.sync_is_stale(),
            "kit": {short[n]: tiers[n] for n in D.PROGRESSIVE},
            "licenses": [SHORT_CLASS[c] for c in D.WEAPON_CLASSES if c in self.licenses()],
            "maps": self.maps(),
            "traps": [[n, c] for n, c in self.queued(D.TRAPS + ["DeathLink: No Heals"], "traps_cleared").items()],
            "tokens": [[n, c] for n, c in self.queued(D.FILLER_TOKENS, "tokens_spent").items()],
            "goal": s.get("goal"),
            "goal_done": bool(p and p.goal_done),
            "value": {"total": p.total_value if p else 0, "goal": s.get("value_goal", 0)},
            "warnings": len(self.warnings),
            "events": [{"age": round(now - e["t"], 1), "kind": e["kind"], "title": e["title"], "text": e["text"],
                        "flags": e["flags"], "id": str(e["seq"])} for e in self.events[-12:]][::-1],
            "last_action": self.last_action(),
            "version": self.state_version,
            "checking": bool(getattr(self, "checking", False)),
        }
        if self.tracks_cores():
            distinct, boss, met = evaluator.core_goal_status(s, st.get("cores_looted", {}))
            state["cores"] = {"distinct": distinct, "target": s["core_hunt_count"], "boss": boss,
                              "boss_required": s.get("require_boss_core", False), "met": met,
                              "recent": recent_core}
        return state

    def overlay_action(self, kind: str, name: str) -> bool:
        if kind == "done":
            return self.use_queued(name, D.TRAPS + ["DeathLink: No Heals"], "traps_cleared", "Cleared")
        if kind == "spend":
            return self.use_queued(name, D.FILLER_TOKENS, "tokens_spent", "Spent")
        if kind == "undo":
            return self.undo_last()
        if kind == "check":
            self.request_poll()
            return True
        if kind == "sync":
            webbrowser.open(SYNC_URL)
            loop = asyncio.get_event_loop()
            for delay in (30, 90):  # give arctracker time to pull the raid, then look again
                loop.call_later(delay, self.request_poll)
            logger.info("ARC Raiders: opened arctracker.io to sync; checking again in 30s and 90s.")
            return True
        return False

    def save_state(self) -> None:
        asyncio.create_task(self.send_msgs([{"cmd": "Set", "key": self.state_key, "default": None,
                                             "want_reply": False,
                                             "operations": [{"operation": "replace", "value": self.state}]}]))

    def on_deathlink(self, data: dict) -> None:
        super().on_deathlink(data)
        if self.state is not None:
            self.state.setdefault("deathlink_penalties", 0)
            self.state["deathlink_penalties"] += 1
            self.save_state()
        logger.info("ARC Raiders: DeathLink received. Your next raid is a No Heals raid (/arc_done no heals).")
        self.ui_dirty = True

    async def disconnect(self, allow_autoreconnect: bool = False):
        self.state = None
        self.slot_data = {}
        await super().disconnect(allow_autoreconnect)

    # ------------------------------------------------------------------ received items
    def received_counts(self) -> dict:
        counts: dict = {}
        for it in self.items_received:
            name = ITEM_NAMES.get(it.item)
            if name:
                counts[name] = counts.get(name, 0) + 1
        return counts

    def tiers(self) -> dict:
        c = self.received_counts()
        return {n: min(c.get(n, 0), copies) for n, copies in D.PROGRESSIVE.items()}

    def licenses(self) -> set:
        c = self.received_counts()
        return {cls for cls in D.WEAPON_CLASSES if c.get(D.license_name(cls))}

    def maps(self) -> list:
        c = self.received_counts()
        return [m for m in D.MAP_NAMES if c.get(D.map_access_name(m))]

    def queued(self, names: list, state_field: str) -> dict:
        """name -> how many are still pending (received minus used)."""
        c = self.received_counts()
        if state_field == "traps_cleared" and self.state:
            c["DeathLink: No Heals"] = self.state.get("deathlink_penalties", 0)
        used = (self.state or {}).get(state_field, {})
        return {n: c.get(n, 0) - used.get(n, 0) for n in names if c.get(n, 0) - used.get(n, 0) > 0}

    def use_queued(self, query: str, names: list, state_field: str, verb: str) -> bool:
        if self.state is None:
            logger.info("Not connected yet.")
            return False
        pending = self.queued(names, state_field)
        match = next((n for n in pending if query.lower() in n.lower()), None)
        if not match:
            logger.info(f"Nothing pending matches '{query}'. Pending: {', '.join(pending) or 'none'}")
            return False
        used = self.state.setdefault(state_field, {})
        used[match] = used.get(match, 0) + 1
        history = self.state.setdefault("history", [])
        history.append([state_field, match, verb])
        del history[:-20]
        self.save_state()
        logger.info(f"{verb}: {match}")
        self.ui_dirty = True
        return True

    def last_action(self) -> str | None:
        h = (self.state or {}).get("history") or []
        return f"{h[-1][2]} {h[-1][1]}" if h else None

    def undo_last(self) -> bool:
        h = (self.state or {}).get("history") or []
        if not h:
            logger.info("Nothing to undo.")
            return False
        state_field, name, verb = h.pop()
        used = self.state.setdefault(state_field, {})
        used[name] = max(0, used.get(name, 0) - 1)
        self.save_state()
        logger.info(f"Undid: {verb} {name}")
        self.ui_dirty = True
        return True

    # ------------------------------------------------------------------ polling
    def request_poll(self) -> None:
        self.checking = True
        self.ui_dirty = True
        self.poll_wake.set()

    def set_keys(self, app: str, user: str) -> None:
        save_keys(app, user)
        self.api = ArcTrackerAPI(app, user)
        logger.info("ARC Raiders: keys saved.")
        self.request_poll()

    async def poll_loop(self) -> None:
        while not self.exit_event.is_set():
            interval = POLL_SECONDS
            if self.api and self.api.remaining is not None and self.api.remaining < LOW_REMAINING:
                interval = SLOW_POLL_SECONDS
            try:
                await asyncio.wait_for(self.poll_wake.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            self.poll_wake.clear()
            wait = MIN_MANUAL_GAP - (time.monotonic() - self.last_poll)
            if wait > 0:  # too soon after the last poll: wait it out instead of dropping the request
                await asyncio.sleep(wait)
            if self.api and self.state and self.slot_data and self.slot:
                try:
                    await self.poll_once()
                    self.last_error = ""
                except ArcApiError as e:
                    self.last_error = str(e)
                    logger.warning(f"ARC Raiders: arctracker.io error {e}")
                except OSError as e:
                    self.last_error = f"network: {e}"
                    logger.warning(f"ARC Raiders: network error {e}")
            if getattr(self, "checking", False) or self.api:
                self.checking = False
                self.ui_dirty = True

    async def fetch_new_rounds(self) -> list:
        """Rounds newest first, paging back only until we pass the baseline."""
        base = evaluator.parse_time(self.state["baseline"]) - evaluator.END_SLACK
        out, offset = [], 0
        for _ in range(MAX_PAGES):
            page, total = await asyncio.to_thread(self.api.rounds, 50, offset)
            out += page
            offset += len(page)
            if not page or offset >= total or evaluator.parse_time(page[-1]["roundEndedAt"]) < base:
                break
        return out

    def tracks_cores(self) -> bool:
        s = self.slot_data
        return bool(s.get("cores")) and (s.get("core_checks_per_type", 0) > 0 or s.get("goal") != "extracted_value")

    def progress_kinds(self) -> list:
        return [k for k, n in (self.slot_data.get("progress_checks") or {}).items() if n > 0]

    def tracks_snapshot(self) -> bool:
        return self.tracks_cores() or bool(self.progress_kinds())

    async def update_snapshot(self, newest: dict | None) -> None:
        """Cores + account progress. First call: snapshot with no credit. Then, once per new raid, credit increases.
        Waits until the stash sync is at least as new as the raid, so a raid isn't credited from an old stash.
        If the sync also carried raids from before the baseline, re-snapshot instead of crediting."""
        st = self.state
        first = st.get("core_prev") is None and st.get("progress_prev") is None
        if not first and (newest is None or newest["id"] == st.get("core_round")):
            return
        stash_synced = newest["syncedAt"] if newest else None
        now_cores = None
        if self.tracks_cores():
            items, stash_synced = await asyncio.to_thread(self.api.stash)
            self.loadout = (await asyncio.to_thread(self.api.loadout)).get("loadout")
            if not first and stash_synced and stash_synced < newest["syncedAt"]:
                return  # stash not synced for this raid yet; try again next poll
            now_cores = evaluator.count_cores(self.slot_data, items, self.loadout)
            self.stash_synced = stash_synced
        payloads = {}
        for kind in self.progress_kinds():
            endpoint = {"quest": "quests", "blueprint": "blueprints", "hideout": "hideout", "project": "projects"}[kind]
            payloads[endpoint] = await asyncio.to_thread(self.api.progress, endpoint)
        now_prog = evaluator.progress_snapshot(payloads.get("quests"), payloads.get("blueprints"),
                                               payloads.get("hideout"), payloads.get("projects"))

        def take_snapshot():
            st["core_prev"] = now_cores
            st["progress_prev"] = now_prog
            st["core_prev_synced"] = stash_synced
            st["core_round"] = newest["id"] if newest else None

        if first:
            take_snapshot()
            logger.info("ARC Raiders: starting snapshot taken. Cores and progress from now on count.")
        elif stash_synced and evaluator.backlog_in_sync(self.rounds, st.get("core_prev_synced"), stash_synced,
                                                        st["baseline"]):
            take_snapshot()
            logger.warning("ARC Raiders: this arctracker sync also included raids from before you connected, so "
                           "its cores and progress couldn't be told apart and weren't counted. Snapshot re-taken; "
                           "your next raid counts normally.")
        else:
            if now_cores is not None:
                gain = evaluator.core_gain(st.get("core_prev") or {}, now_cores)
                looted = st.setdefault("cores_looted", {})
                for iid, n in gain.items():
                    looted[iid] = looted.get(iid, 0) + n
                if gain:
                    names = {c[0]: c[1] for c in self.slot_data["cores"]}
                    msg = ", ".join(f"{names[i]} x{n}" for i, n in gain.items())
                    logger.info("ARC Raiders: looted " + msg)
                    self.notify("core", msg, title="Cores looted")
            pgain = evaluator.progress_gain(st.get("progress_prev") or {}, now_prog)
            done = st.setdefault("progress_done", {})
            for kind, n in pgain.items():
                done[kind] = done.get(kind, 0) + n
            if pgain:
                logger.info("ARC Raiders: new progress " + ", ".join(f"{k} +{n}" for k, n in pgain.items()))
            take_snapshot()
        self.save_state()

    def sync_is_stale(self) -> bool:
        """Last known arctracker sync is more than an hour older than the baseline."""
        synced = getattr(self, "stash_synced", None) or (self.state or {}).get("core_prev_synced")
        if not synced or not self.state:
            return False
        newest_round = max((r["syncedAt"] for r in self.rounds if r.get("syncedAt")), default=None)
        last = max(synced, newest_round) if newest_round else synced
        return evaluator.parse_time(last) < evaluator.parse_time(self.state["baseline"]) - STALE_SYNC

    async def poll_once(self) -> None:
        self.last_poll = time.monotonic()
        self.rounds = await self.fetch_new_rounds()
        eligible = evaluator.eligible_rounds(self.rounds, self.state["baseline"])
        newest = eligible[0] if eligible else None
        loadout_fresh = False
        if self.tracks_snapshot():
            before = self.loadout
            await self.update_snapshot(newest)
            loadout_fresh = self.loadout is not before
        p = evaluator.evaluate(self.slot_data, self.rounds, self.state["baseline"],
                               self.state.get("cores_looted"), self.state.get("progress_done"))
        self.progress = p

        new = {LOCATION_IDS[n] for n in p.locations} & self.missing_locations
        if new:
            await self.check_locations(new)
            logger.info(f"ARC Raiders: sent {len(new)} check(s).")

        if p.goal_done and not self.finished_game:
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            self.finished_game = True
            logger.info("ARC Raiders: goal complete!")
            self.notify("goal", "Goal complete!", title="ARC Raiders")

        if "DeathLink" in self.tags:
            fresh = [rid for rid in p.deaths if rid not in self.state["deaths_sent"]]
            if fresh:
                self.state["deaths_sent"] += fresh
                self.save_state()
                await self.send_death(f"{self.player_names[self.slot]} died topside.")

        newest_id = newest["id"] if newest else None
        if self.slot_data.get("referee_mode") == "warn":
            if not loadout_fresh and (self.loadout is None or newest_id != self.newest_round_id):
                self.loadout = (await asyncio.to_thread(self.api.loadout)).get("loadout")
            self.refresh_warnings()
        self.newest_round_id = newest_id

    def refresh_warnings(self) -> None:
        if self.loadout:
            self.warnings = referee.check(self.loadout, self.tiers(), self.licenses())
            self.ui_dirty = True

    # ------------------------------------------------------------------ text summary (also used by /arc_status)
    def status_lines(self) -> list:
        if not self.slot_data:
            return ["Not connected."]
        s, p = self.slot_data, self.progress
        lines = []
        if not self.api:
            lines.append("No arctracker.io keys yet. Enter them in the ARC Raiders tab.")
        if p:
            lines.append(f"Value: {p.total_value:,} / {s['value_goal']:,} ({s['value_metric']}) | "
                         f"Extractions: {p.extractions} | ARC kills: {p.arc_kills} | Best raid: {p.best_raid:,}")
        if self.tracks_cores() and self.state:
            looted = self.state.get("cores_looted", {})
            distinct, boss, met = evaluator.core_goal_status(s, looted)
            lines.append(f"Cores: {distinct}/{s['core_hunt_count']} types" +
                         (f", boss {'yes' if boss else 'no'}" if s.get("require_boss_core") else "") +
                         (" (done)" if met else ""))
        t = self.tiers()
        for name, rules in D.TIER_RULES.items():
            lines.append(f"{name.replace('Progressive ', '')}: {rules[t[name]]}")
        lines.append("Maps: " + ", ".join(self.maps()))
        lines.append("Weapon licenses: " + ", ".join(sorted(self.licenses())))
        tok = self.queued(D.FILLER_TOKENS, "tokens_spent")
        trap = self.queued(D.TRAPS + ["DeathLink: No Heals"], "traps_cleared")
        lines.append("Tokens: " + (", ".join(f"{n} x{c}" for n, c in tok.items()) or "none"))
        lines.append("Traps to do: " + (", ".join(f"{n} x{c}" for n, c in trap.items()) or "none"))
        for w in self.warnings:
            lines.append("Referee: " + w)
        if self.api and self.api.remaining is not None:
            lines.append(f"API calls left this hour: {self.api.remaining}")
        if self.last_error:
            lines.append("Last error: " + self.last_error)
        return lines

    def make_gui(self):
        from .ui import make_manager
        return make_manager()


async def main(args) -> None:
    ctx = ArcContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
    poll_task = asyncio.create_task(ctx.poll_loop(), name="arc poll loop")
    ctx.start_overlay()
    if gui_enabled and not getattr(args, "nogui", False):
        ctx.run_gui()
    ctx.run_cli()
    await ctx.exit_event.wait()
    poll_task.cancel()
    await ctx.shutdown()
