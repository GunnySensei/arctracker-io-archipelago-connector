"""Desktop HUD: a borderless, always-on-top, transparent Tk window that draws the overlay panel + pop-up cards.
Reads http://localhost:<port>/state.json from the client. Separate process (started via launch_subprocess).
- Only the panel/cards are painted; everything else is a colour-key hole (see-through and click-through).
- WS_EX_NOACTIVATE: clicking Done doesn't steal focus from the game; WS_EX_TOOLWINDOW: no taskbar button.
- Drag by the title row. Right-click: view, scale, opacity, reset position, close.
Needs the game in borderless-windowed mode (exclusive fullscreen draws over everything)."""
import json
import os
import sys
import time
import urllib.request

KEY = "#010203"  # transparent colour key
PANEL = "#0c0e10"
EDGE = "#2a2d31"
TEXT, DIM = "#ece6da", "#8f8a80"
TEAL, AMBER, RED, GREEN, GOLD = "#4fb3c8", "#f0b44c", "#ff6a4d", "#8fd694", "#ffc24a"
RAR = ["#c9c9c9", "#7fd36b", "#5aa8ff", "#c07cff", GOLD]
RAR_SHORT = ["Grey", "Green", "Blue", "Purple", "Gold"]
TIER = ["I", "II", "III", "IV"]
SHIELD = ["None", "Light", "Medium", "Heavy"]
HEALS, HEAL_RAR = ["2", "4", "6", "10", "∞"], [0, 1, 2, 4, 4]
NADES = ["None", "2", "5", "∞"]
AUG = ["Basic", "≤ green", "≤ blue", "Any"]
POP_COLOURS = {"found": TEAL, "received": AMBER, "trap": RED, "core": GREEN, "goal": GOLD}
TAGS = {"found": "CHECK", "received": "RECEIVED", "trap": "TRAP", "core": "CORES", "goal": "GOAL"}
POP_SECONDS = 8


def _settings_path() -> str:
    try:
        import Utils
        return Utils.user_path("arc_raiders_hud.json")
    except Exception:  # noqa: BLE001
        return os.path.join(os.path.expanduser("~"), "arc_raiders_hud.json")


def _load() -> dict:
    try:
        with open(_settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(cfg: dict) -> None:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def _short(n: int) -> str:
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{round(n / 1000)}k" if n >= 1000 else str(n)


def run(url: str = "http://127.0.0.1:38300", in_process: bool = False) -> None:
    """in_process=True: running as a thread inside the client. Leave process-wide settings (DPI) alone."""
    # "localhost" costs ~2s per request on Windows (IPv6 tried first); the client listens on IPv4 loopback
    url = url.replace("//localhost", "//127.0.0.1")
    import ctypes
    import tkinter as tk
    import tkinter.font as tkfont

    if not in_process:
        try:  # crisp text on scaled displays; coordinates become physical pixels
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa: BLE001
            pass

    # single instance: hold a localhost port as a lock; a second HUD just exits
    import socket
    lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock.bind(("127.0.0.1", int(url.rsplit(":", 1)[1].strip("/")) + 1))
    except OSError:
        return

    cfg = {"scale": 1.33, "mode": "full", "alpha": 0.9, "x": None, "y": None, **_load()}
    root = tk.Tk()
    root.title("ARC·AP HUD")
    root.overrideredirect(True)
    root.configure(bg=KEY)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", KEY)
    root.attributes("-alpha", cfg["alpha"])
    canvas = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)
    root.pack_propagate(False)

    families = set(tkfont.families())
    family = next((f for f in ("Bahnschrift SemiCondensed", "Bahnschrift", "Segoe UI") if f in families), "Arial")
    fonts: dict = {}

    def font(px: float, bold=False):
        key = (round(px), bold)
        if key not in fonts:
            fonts[key] = tkfont.Font(root=root, family=family, size=-max(8, round(px)),
                                     weight="bold" if bold else "normal")
        return fonts[key]

    win = {"hwnd": None, "placed": None}
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_NOOWNERZORDER = 0x1, 0x2, 0x10, 0x200
    HWND_TOPMOST = -1

    def place(x=None, y=None, w=None, h=None):
        """Move/resize/re-topmost WITHOUT activating the window. Tk's own geometry()/-topmost activate it,
        which steals the game's mouse capture."""
        hwnd = win["hwnd"]
        if not hwnd:
            return
        flags = SWP_NOACTIVATE | SWP_NOOWNERZORDER
        if x is None:
            flags |= SWP_NOMOVE
        if w is None:
            flags |= SWP_NOSIZE
        try:
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, int(x or 0), int(y or 0), int(w or 0),
                                              int(h or 0), flags)
        except Exception:  # noqa: BLE001
            pass

    def win_style():
        # no activation on click + no taskbar button
        try:
            u = ctypes.windll.user32
            hwnd = u.GetAncestor(root.winfo_id(), 2)
            win["hwnd"] = hwnd
            GWL_EXSTYLE, NOACT, TOOL, APPWIN = -20, 0x08000000, 0x00000080, 0x00040000
            ex = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, (ex | NOACT | TOOL) & ~APPWIN)
        except Exception:  # noqa: BLE001
            pass

    state = {"data": None, "error": None}
    shown_pops: dict = {}  # id -> [event, shown_at or None while queued, first_seen]
    MAX_CARDS = 4
    hits: list = []        # (x0, y0, x1, y1, action) click targets
    drag = {"active": False, "dx": 0, "dy": 0}

    import threading
    flags = {"new": True}

    def fetch(since=None):
        q = f"?since={since}" if since is not None else ""
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/state.json" + q, timeout=25) as r:
                state["data"], state["error"] = json.load(r), None
        except Exception as e:  # noqa: BLE001
            state["data"], state["error"] = None, str(e)
        flags["new"] = True

    stopped = threading.Event()

    def poller():
        while not stopped.is_set():
            d = state["data"]
            since = d.get("version") if d and d.get("connected") else None
            fetch(since)
            if state["error"] or since is None:
                time.sleep(2)  # client not up yet / not connected: retry gently

    threading.Thread(target=poller, name="hud poll", daemon=True).start()

    pressed = {"key": None, "until": 0.0}

    def post(kind, name=""):
        """Fire the action in the background; light the button up immediately so the click feels instant."""
        pressed.update(key=(kind, name), until=time.time() + 0.6)
        flags["new"] = True

        def send():
            try:
                req = urllib.request.Request(url.rstrip("/") + "/action", method="POST",
                                             data=json.dumps({"kind": kind, "name": name}).encode(),
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=3).read()
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=send, daemon=True).start()

    def is_pressed(kind, name=""):
        return pressed["key"] == (kind, name) and time.time() < pressed["until"]

    # ---------------------------------------------------------------- drawing
    def draw():
        s = cfg["scale"]
        W, pad, lh = round(360 * s), round(12 * s), round(20 * s)
        canvas.delete("all")
        hits.clear()
        y = 0
        d = state["data"]

        def corner_grip(top_y):
            """Dotted triangle in the top-right corner, pointing into the corner: 'grab here to move'."""
            n, gap, r = 5, 4 * s, max(1.0, 1.25 * s)
            x0, y0 = W - round(5 * s), top_y + round(5 * s)
            for i in range(n):          # row (down from the top edge)
                for j in range(n - i):  # column (left from the right edge)
                    cx, cyy = x0 - j * gap, y0 + i * gap
                    canvas.create_oval(cx - r, cyy - r, cx + r, cyy + r, fill="#b4ada2", width=0)
            size = round(22 * s)
            hits.insert(0, (W - size, top_y, W, top_y + size, ("drag", "")))

        def text(x, yy, t, colour=TEXT, px=15, bold=False, anchor="nw"):
            return canvas.create_text(x, yy, text=t, fill=colour, font=font(px * s, bold), anchor=anchor)

        def width(t, px=15, bold=False):
            return font(px * s, bold).measure(t)

        def fit_list(items, avail, sep=" · "):
            """Join as many items as fit in `avail` pixels; the rest become '+N'."""
            for n in range(len(items), 0, -1):
                t = sep.join(items[:n]) + (f" +{len(items) - n}" if n < len(items) else "")
                if width(t, 15, True) <= avail:
                    return t
            return f"{len(items)} classes"

        if cfg["mode"] != "popups":
            top = y
            items = []  # draw panel after measuring height: collect lambdas
            cy = y + pad

            def title_row(cy):
                corner_grip(top)
                x = pad + 3
                text(x, cy, "ARC·AP", TEAL, 12, True)
                # right side: [↻] [SYNC] then the sync age to their left
                bh = round(16 * s)
                bx = W - pad - round(16 * s)
                for label, kind in (("SYNC", "sync"), ("CHECK", "check")):
                    bw = width(label, 11, True) + round(12 * s)
                    on = is_pressed(kind)
                    canvas.create_rectangle(bx - bw, cy - round(1 * s), bx, cy - round(1 * s) + bh,
                                            outline=TEAL if on else EDGE, fill=TEAL if on else PANEL)
                    text(bx - bw / 2, cy - round(1 * s) + bh / 2, label, PANEL if on else TEXT, 11, True,
                         anchor="center")
                    hits.append((bx - bw, cy - round(1 * s), bx, cy - round(1 * s) + bh, (kind, "")))
                    bx -= bw + round(4 * s)
                right, colour = "OFFLINE", DIM
                if d and d.get("connected"):
                    if d.get("checking"):
                        right, colour = "CHECKING…", TEAL
                    elif d.get("stale"):
                        right, colour = "SYNC NEEDED", RED
                    elif d.get("synced"):
                        mins = max(0, round((time.time() - _iso(d["synced"])) / 60))
                        right = "NOW" if mins < 1 else f"{mins}M AGO" if mins < 60 else f"{round(mins / 60)}H AGO"
                    else:
                        right = "NO RAIDS YET"
                text(bx - round(4 * s), cy, right, colour, 12, anchor="ne")
                return cy + round(20 * s)

            # first pass: compute height by drawing into canvas directly, then put panel behind
            cy = title_row(cy)
            if not d or not d.get("connected"):
                text(pad + 3, cy, "Waiting for the ARC Raiders client…" if not state["error"]
                     else "ARC Raiders client not running", DIM, 14)
                cy += lh
            else:
                k = d["kit"]
                if cfg["mode"] == "full":
                    c1, c2, c3, c4 = pad + 3, pad + round(58 * s), round(W / 2 + 8 * s), round(W / 2 + 54 * s)

                    def kv(x, xv, yy, key, val, colour=TEXT):
                        text(x, yy + round(2 * s), key.upper(), DIM, 11)
                        text(xv, yy, val, colour, 15, True)

                    # guns: pips + rarity label
                    text(c1, cy + round(2 * s), "GUNS", DIM, 11)
                    px = c2
                    for i in range(5):
                        canvas.create_rectangle(px, cy + round(6 * s), px + round(6 * s), cy + round(12 * s),
                                                fill=TEAL if i <= k["rarity"] else "#3a3f44", width=0)
                        px += round(8 * s)
                    text(px + round(3 * s), cy, f"≤ {RAR_SHORT[k['rarity']]}", RAR[k["rarity"]], 15, True)
                    kv(c3, c4, cy, "Tier", f"≤ {TIER[k['tier']]}")
                    cy += lh
                    kv(c1, c2, cy, "Shield", SHIELD[k["shields"]])
                    text(c3, cy + round(2 * s), "HEALS", DIM, 11)
                    hx = c4
                    text(hx, cy, HEALS[k["healing"]], TEXT, 15, True)
                    hr = HEAL_RAR[k["healing"]]
                    text(hx + width(HEALS[k["healing"]] + " ", 15, True), cy,
                         f"≤ {RAR_SHORT[hr].lower()}", RAR[hr], 15, True)
                    cy += lh
                    kv(c1, c2, cy, "Nades", NADES[k["throwables"]])
                    kv(c3, c4, cy, "Aug", AUG[k["augment"]])
                    cy += lh
                    kv(c1, c2, cy, "Slots", "2 guns" if k["slots"] else "1 gun")
                    kv(c3, c4, cy, "Lic", fit_list(d["licenses"], W - pad - c4) or "none")
                    cy += lh
                    kv(c1, c1 + round(46 * s), cy, "Maps", fit_list(d["maps"], W - pad - c1 - round(46 * s)) or "none")
                    cy += lh
                traps = d.get("traps") or []
                if traps:
                    canvas.create_line(pad, cy + round(4 * s), W - pad, cy + round(4 * s), fill=EDGE)
                    cy += round(10 * s)
                    for name, count in traps[:2]:
                        label = "▲ " + name.replace(" Trap", "") + (f" ×{count}" if count > 1 else "")
                        text(pad + 3, cy, label, RED, 15, True)
                        bw, bh = round(52 * s), round(18 * s)
                        bx = W - pad - bw
                        on = is_pressed("done", name)
                        canvas.create_rectangle(bx, cy, bx + bw, cy + bh, outline=TEAL if on else EDGE, width=1,
                                                fill=TEAL if on else PANEL)
                        text(bx + bw / 2, cy + bh / 2, "DONE", PANEL if on else TEXT, 11, True, anchor="center")
                        hits.append((bx, cy, bx + bw, cy + bh, ("done", name)))
                        cy += round(22 * s)
                    if len(traps) > 2:
                        text(pad + 3, cy, f"+{len(traps) - 2} more traps", DIM, 13)
                        cy += round(18 * s)
                cores, goal = d.get("cores"), d.get("goal")
                if cores or goal != "core_hunt":
                    canvas.create_line(pad, cy + round(4 * s), W - pad, cy + round(4 * s), fill=EDGE)
                    cy += round(10 * s)
                if cores:
                    x = pad + 3
                    text(x, cy + round(2 * s), "CORES", DIM, 11)
                    x += round(48 * s)
                    t = f"{cores['distinct']} / {cores['target']}"
                    text(x, cy, t, TEXT, 15, True)
                    x += width(t, 15, True) + round(10 * s)
                    if cores.get("boss_required"):
                        text(x, cy + round(2 * s), "BOSS", DIM, 11)
                        x += round(38 * s)
                        text(x, cy, "✓" if cores["boss"] else "✗", GREEN if cores["boss"] else TEXT, 15, True)
                        x += round(20 * s)
                    if cores.get("recent"):
                        text(x, cy, "+ " + cores["recent"][:28], AMBER, 14, True)
                    cy += lh
                if goal != "core_hunt":
                    v = d["value"]
                    text(pad + 3, cy + round(2 * s), "VALUE", DIM, 11)
                    label = f"{_short(v['total'])} / {_short(v['goal'])}"
                    lx = W - pad - width(label, 15, True)
                    bx0, bx1 = pad + round(48 * s), lx - round(10 * s)
                    by = cy + round(8 * s)
                    canvas.create_rectangle(bx0, by, bx1, by + round(5 * s), fill="#2a2e33", width=0)
                    pct = min(1, v["total"] / v["goal"]) if v["goal"] else 0
                    canvas.create_rectangle(bx0, by, bx0 + (bx1 - bx0) * pct, by + round(5 * s), fill=TEAL, width=0)
                    text(lx, cy, label, TEXT, 15, True)
                    cy += lh
                if d.get("goal_done"):
                    text(pad + 3, cy, "GOAL COMPLETE", GREEN, 15, True)
                    cy += lh
            bottom = cy + pad - round(4 * s)
            panel = canvas.create_rectangle(0, top, W, bottom, fill=PANEL, outline=EDGE)
            bar = canvas.create_rectangle(0, top, round(3 * s), bottom, fill=TEAL, width=0)
            canvas.tag_lower(bar)
            canvas.tag_lower(panel)
            y = bottom + round(8 * s)

        if cfg["mode"] == "popups":
            hs = round(22 * s)
            canvas.create_rectangle(W - hs - 1, 0, W - 1, hs, fill=PANEL, outline=EDGE)
            corner_grip(0)
            y = hs + round(4 * s)

        # pop-up cards
        now = time.time()
        for e in (d or {}).get("events", []) if d else []:
            # anything newer than ~30s that we haven't seen yet joins the queue (oldest first)
            if e["age"] <= 30 and e["id"] not in shown_pops:
                shown_pops[e["id"]] = [e, None, now - e["age"]]
        active = [v for v in shown_pops.values() if v[1] is not None and now - v[1] < POP_SECONDS]
        waiting = sorted((v for v in shown_pops.values() if v[1] is None), key=lambda v: int(v[0]["id"]))
        for v in waiting[:max(0, MAX_CARDS - len(active))]:
            v[1] = now                      # a slot freed up: this card's 8 seconds start now
            active.append(v)
        live = [(v[0], v[1]) for v in sorted(active, key=lambda v: -int(v[0]["id"]))]
        for ev, t0 in live:
            colour = POP_COLOURS.get(ev["kind"], TEAL)
            top = y
            ch = round(46 * s)
            canvas.create_rectangle(0, top, W, top + ch, fill=PANEL, outline=EDGE)
            canvas.create_rectangle(0, top, round(3 * s), top + ch, fill=colour, width=0)
            tag = TAGS.get(ev["kind"], ev["kind"].upper())
            text(pad + 3, top + round(6 * s), tag, colour, 11, True)
            text(pad + 3 + width(tag + "  ", 11, True), top + round(5 * s), ev["title"][:48], DIM, 13)
            body_colour = RED if ev["kind"] == "trap" else GOLD if ev["kind"] == "goal" else \
                GOLD if (ev.get("flags", 0) & 1) else TEXT
            text(pad + 3, top + round(22 * s), ev["text"][:44], body_colour, 16, True)
            y = top + ch + round(6 * s)
        for k_ in [k_ for k_, v in shown_pops.items() if now - v[2] > 300]:
            del shown_pops[k_]

        # fixed-size window (tall enough for the panel + 4 cards); the unused part is see-through and
        # click-through, so we never resize it per update (resizing is what used to grab focus)
        H = round(600 * s)
        sw = root.winfo_screenwidth()
        x = cfg["x"] if cfg["x"] is not None else sw - W - round(24 * s)
        yy = cfg["y"] if cfg["y"] is not None else round(40 * s)
        box = (int(x), int(yy), W, H)
        if box != win["placed"]:
            win["placed"] = box
            if win["hwnd"]:
                place(*box)
            else:
                root.geometry(f"{W}x{H}+{int(x)}+{int(yy)}")  # first show only (before we have the hwnd)

    # ---------------------------------------------------------------- interaction
    def on_press(ev):
        for x0, y0, x1, y1, (kind, name) in hits:
            if x0 <= ev.x <= x1 and y0 <= ev.y <= y1:
                if kind == "drag":
                    drag.update(active=True, dx=ev.x_root - root.winfo_x(), dy=ev.y_root - root.winfo_y())
                else:
                    post(kind, name)
                return

    def on_motion(ev):
        if drag["active"]:
            cfg["x"], cfg["y"] = ev.x_root - drag["dx"], ev.y_root - drag["dy"]
            win["placed"] = (int(cfg["x"]), int(cfg["y"]), win["placed"][2], win["placed"][3])
            place(*win["placed"])

    def on_release(_ev):
        if drag["active"]:
            drag["active"] = False
            _save(cfg)

    menu = tk.Menu(root, tearoff=0)

    def set_cfg(**kw):
        cfg.update(kw)
        if "alpha" in kw:
            root.attributes("-alpha", cfg["alpha"])
        _save(cfg)
        draw()

    for label, mode in (("Full", "full"), ("Compact", "compact"), ("Pop-ups only", "popups")):
        menu.add_command(label=f"View: {label}", command=lambda m=mode: set_cfg(mode=m))
    menu.add_separator()
    for sc in (1.0, 1.15, 1.33, 1.5, 1.75):
        menu.add_command(label=f"Scale {sc:g}x", command=lambda v=sc: set_cfg(scale=v))
    menu.add_separator()
    for a in (0.7, 0.8, 0.9, 1.0):
        menu.add_command(label=f"Opacity {int(a * 100)}%", command=lambda v=a: set_cfg(alpha=v))
    menu.add_separator()
    menu.add_command(label="Reset position", command=lambda: set_cfg(x=None, y=None))
    menu.add_command(label="Close HUD", command=root.destroy)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_motion)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Button-3>", lambda ev: menu.tk_popup(ev.x_root, ev.y_root))

    last = {"top": 0.0, "sig": None, "minute": -1, "expiry": 0.0}

    def tick(force=False):
        now = time.time()
        minute = int(now // 60)
        # redraw only when: new data arrived, the "x min ago" text changes, or a pop-up expires
        press_ended = pressed["key"] is not None and now >= pressed["until"]
        if press_ended:
            pressed["key"] = None
        if force or flags["new"] or press_ended or minute != last["minute"] or                 (last["expiry"] and now >= last["expiry"]):
            flags["new"] = False
            last["minute"] = minute
            draw()
            live = [v[1] + POP_SECONDS for v in shown_pops.values() if v[1] is not None and v[1] + POP_SECONDS > now]
            last["expiry"] = min(live) if live else 0.0
        if now - last["top"] >= 3 and not drag["active"]:
            last["top"] = now
            place()  # re-assert topmost over borderless games, without activating
        if not force:
            root.after(250, tick)

    root.after(50, win_style)
    tick()
    try:
        root.mainloop()
    finally:
        stopped.set()
        lock.close()


def _iso(s: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:38300")
