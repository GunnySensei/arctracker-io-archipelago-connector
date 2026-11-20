"""ARC Raiders tab for the standard Archipelago client window (KivyMD, as used by kvui)."""
# isort: off
from kvui import GameManager  # must be imported before kivy
# isort: on
import webbrowser

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText

from .. import data as D

WARN = "ff7a5c"
GOOD = "7ddc7d"
DIM = "9a9a9a"


def label(text: str, size: str = "medium", bold: bool = False) -> MDLabel:
    lbl = MDLabel(text=text, markup=True, adaptive_height=True, font_style="Body", role=size, bold=bold)
    return lbl


def header(text: str) -> MDLabel:
    return label(f"[b]{text}[/b]", "large")


def button(text: str, on_press, style: str = "outlined") -> MDButton:
    b = MDButton(MDButtonText(text=text), style=style)
    b.bind(on_release=lambda *_: on_press())
    return b


def row(*widgets) -> MDBoxLayout:
    """Horizontal row with everything vertically centred (labels stretch, buttons keep their size)."""
    r = MDBoxLayout(orientation="horizontal", adaptive_height=True, spacing=dp(8))
    for w in widgets:
        w.pos_hint = {"center_y": 0.5}
        if isinstance(w, MDLabel):
            w.valign = "middle"
        else:
            w.size_hint_x = None
        r.add_widget(w)
    return r


def item_row(text: str, btn_text: str, on_press) -> MDBoxLayout:
    """A label + button line with a fixed height so the text sits level with the button."""
    lbl = MDLabel(text=text, markup=True, font_style="Body", role="medium", valign="middle",
                  size_hint_y=None, height=dp(44))
    r = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(8))
    r.add_widget(lbl)
    b = button(btn_text, on_press)
    b.pos_hint = {"center_y": 0.5}
    b.size_hint_x = None
    r.add_widget(b)
    return r


class ArcPanel(MDScrollView):
    def __init__(self, ctx, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.root_box = MDBoxLayout(orientation="vertical", adaptive_height=True, padding=dp(12), spacing=dp(6))
        self.add_widget(self.root_box)
        self.keys_box = self._build_keys_box()      # persistent so typing isn't wiped by refreshes
        self.dynamic = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(6))
        self.root_box.add_widget(self.dynamic)
        self.keys_visible = False
        self.show_keys(ctx.api is None)

    # ---------------------------------------------------------------- keys
    def _build_keys_box(self) -> MDBoxLayout:
        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(6))
        box.add_widget(header("arctracker.io keys"))
        box.add_widget(label(f"[color={DIM}]App key (arc_k1_...) from the Developer Dashboard; user key "
                             f"(arc_u1_...) from Settings > Developer Access. Saved only on this PC.[/color]"))
        self.app_field = MDTextField(MDTextFieldHintText(text="App key"), password=True, mode="outlined")
        self.user_field = MDTextField(MDTextFieldHintText(text="User key"), password=True, mode="outlined")
        box.add_widget(self.app_field)
        box.add_widget(self.user_field)
        box.add_widget(row(button("Save keys", self.save_keys, "filled"),
                           button("Cancel", lambda: self.show_keys(False))))
        return box

    def show_keys(self, visible: bool) -> None:
        if visible and not self.keys_visible:
            self.root_box.add_widget(self.keys_box, index=len(self.root_box.children))
        elif not visible and self.keys_visible:
            self.root_box.remove_widget(self.keys_box)
        self.keys_visible = visible

    def save_keys(self) -> None:
        app, user = self.app_field.text.strip(), self.user_field.text.strip()
        if not (app.startswith("arc_k1_") and user.startswith("arc_u1_")):
            self.ctx.ui_dirty = True
            from CommonClient import logger
            logger.warning("Keys should start with arc_k1_ (app) and arc_u1_ (user).")
            return
        self.ctx.set_keys(app, user)
        self.app_field.text = self.user_field.text = ""
        self.show_keys(False)

    # ---------------------------------------------------------------- dynamic content
    def maybe_refresh(self, _dt) -> None:
        if self.ctx.ui_dirty:
            self.ctx.ui_dirty = False
            self.refresh()

    def refresh(self) -> None:
        ctx, box = self.ctx, self.dynamic
        box.clear_widgets()
        s = ctx.slot_data
        if not s:
            box.add_widget(label("Connect to the room to start. Your keys and baseline load after connecting."))
            return

        # status
        api = ctx.api
        status = [f"Baseline: {ctx.state['baseline'] if ctx.state else '...'}"]
        if api and api.remaining is not None:
            status.append(f"API calls left this hour: {api.remaining}")
        if ctx.last_error:
            status.append(f"[color={WARN}]{ctx.last_error}[/color]")
        box.add_widget(label("  |  ".join(status)))
        if ctx.sync_is_stale():
            box.add_widget(label(f"[color={WARN}][b]Sync arctracker.io before your first raid.[/b] Your last sync is "
                                 f"older than when you connected, so older raids could get mixed into your first "
                                 f"core count.[/color]"))
        box.add_widget(row(button("Check now", ctx.request_poll, "filled"),
                           button("Sync on arctracker.io", lambda: webbrowser.open("https://arctracker.io")),
                           button("Keys", lambda: self.show_keys(not self.keys_visible))))
        st = ctx.settings
        box.add_widget(row(
            button("Desktop HUD", ctx.open_hud, "filled"),
            button("Browser overlay", lambda: (ctx.start_overlay(), webbrowser.open(ctx.overlay_url()))),
            button(f"Toasts: {'on' if st.get('toasts') else 'off'}",
                   lambda: ctx.set_setting("toasts", not st.get("toasts"))),
            button(f"Voice: {'on' if st.get('voice') else 'off'}",
                   lambda: ctx.set_setting("voice", not st.get("voice")))))
        if ctx.overlay_server:
            box.add_widget(label(f"[color={DIM}]Overlay: {ctx.overlay_url()}  (in game: Shift+Tab, Steam "
                                 f"browser, open that address, pin it)[/color]"))

        # progress
        p = ctx.progress
        box.add_widget(header("Progress"))
        if p:
            pct = max(0, min(100, 100 * p.total_value / s["value_goal"]))
            box.add_widget(label(f"Value ({s['value_metric']}): [b]{p.total_value:,}[/b] / {s['value_goal']:,}"
                                 + (f"  [color={GOOD}]GOAL![/color]" if p.goal_done else "")))
            bar = MDLinearProgressIndicator(value=pct, size_hint_y=None, height=dp(6))
            box.add_widget(bar)
            maps = ", ".join(f"{m} {n}" for m, n in p.per_map.items()) or "none yet"
            box.add_widget(label(f"Extractions: {p.extractions} ({maps})  |  ARC kills: {p.arc_kills}  |  "
                                 f"Best raid: {p.best_raid:,}"))
        else:
            box.add_widget(label(f"[color={DIM}]Waiting for the first check of arctracker.io...[/color]"))

        # core hunt
        if ctx.tracks_cores() and ctx.state:
            from .evaluator import core_goal_status
            looted = ctx.state.get("cores_looted", {})
            distinct, boss, met = core_goal_status(s, looted)
            goal_txt = f"{distinct} / {s['core_hunt_count']} types"
            if s.get("require_boss_core"):
                goal_txt += f"  |  boss core: {'[color=' + GOOD + ']yes[/color]' if boss else 'not yet'}"
            if s.get("goal") == "extracted_value":
                goal_txt += f"  [color={DIM}](checks only, not your goal)[/color]"
            elif met:
                goal_txt += f"  [color={GOOD}]DONE[/color]"
            box.add_widget(header("Core Hunt"))
            box.add_widget(label(goal_txt))
            if ctx.state.get("core_prev") is None:
                box.add_widget(label(f"[color={DIM}]Taking the starting snapshot of your cores...[/color]"))
            for tier in ("small", "mid", "boss"):
                parts = []
                for iid, display, t in s["cores"]:
                    if t != tier:
                        continue
                    n = looted.get(iid, 0)
                    parts.append(f"[color={GOOD}]{display} x{n}[/color]" if n else f"[color={DIM}]{display}[/color]")
                box.add_widget(label(f"[b]{tier.title()}:[/b] " + ", ".join(parts)))

        # permissions
        box.add_widget(header("What you may bring"))
        tiers = ctx.tiers()
        for name, rules in D.TIER_RULES.items():
            t = tiers[name]
            box.add_widget(label(f"{name.replace('Progressive ', '')}: [b]{rules[t]}[/b]"
                                 f"  [color={DIM}]({t}/{D.PROGRESSIVE[name]})[/color]"))
        box.add_widget(label("Maps: [b]" + (", ".join(ctx.maps()) or "none") + "[/b]"))
        box.add_widget(label("Weapon licenses: [b]" + (", ".join(sorted(ctx.licenses())) or "none") + "[/b]"))

        # referee
        if s.get("referee_mode") == "warn":
            box.add_widget(header("Referee (last synced loadout)"))
            if ctx.warnings:
                for w in ctx.warnings:
                    box.add_widget(label(f"[color={WARN}]- {w}[/color]"))
            elif ctx.loadout:
                box.add_widget(label(f"[color={GOOD}]Loadout is within your unlocks.[/color]"))
            else:
                box.add_widget(label(f"[color={DIM}]No loadout synced yet.[/color]"))

        # tokens & traps
        tokens = ctx.queued(D.FILLER_TOKENS, "tokens_spent")
        traps = ctx.queued(D.TRAPS + ["DeathLink: No Heals"], "traps_cleared")
        last = ctx.last_action()
        if last:
            box.add_widget(item_row(f"[color={DIM}]Last: {last}[/color]", "Undo", ctx.undo_last))
        box.add_widget(header("Traps to do"))
        if not traps:
            box.add_widget(label(f"[color={DIM}]None.[/color]"))
        for name, n in traps.items():
            box.add_widget(item_row(f"[color={WARN}]{name}[/color] x{n}", "Done",
                                    lambda nm=name: ctx.use_queued(nm, list(traps), "traps_cleared", "Cleared")))
        box.add_widget(header("Tokens"))
        if not tokens:
            box.add_widget(label(f"[color={DIM}]None.[/color]"))
        for name, n in tokens.items():
            box.add_widget(item_row(f"{name} x{n}", "Spend",
                                    lambda nm=name: ctx.use_queued(nm, list(tokens), "tokens_spent", "Spent")))


def make_manager():
    class ArcManager(GameManager):
        base_title = "ARC Raiders Client"
        logging_pairs = [("Client", "Archipelago")]

        def build(self):
            container = super().build()
            self.arc_panel = ArcPanel(self.ctx)
            self.add_client_tab("ARC Raiders", self.arc_panel)
            Clock.schedule_interval(self.arc_panel.maybe_refresh, 1.0)
            return container

    return ArcManager
