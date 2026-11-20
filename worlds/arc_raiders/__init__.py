"""ARC Raiders world: automatic checks from the arctracker.io API, items followed on the honor system."""
import math

from BaseClasses import Item, ItemClassification, Location, Region, Tutorial
from Options import OptionError
from worlds.AutoWorld import WebWorld, World

from . import components  # noqa: F401  (registers "ARC Raiders Client" in the Launcher)
from . import data as D
from .options import ArcRaidersOptions


class ArcRaidersItem(Item):
    game = D.GAME


class ArcRaidersLocation(Location):
    game = D.GAME


class ArcRaidersWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial("Setup Guide", "Playing ARC Raiders in Archipelago with arctracker.io.",
                          "English", "setup_en.md", "setup/en", ["GunnySensei"])]


def _classification(name: str) -> ItemClassification:
    if name in D.LOGIC_KIT or name.startswith("Map Access: "):
        return ItemClassification.progression
    if name in D.TRAPS:
        return ItemClassification.trap
    if name in D.FILLER_TOKENS:
        return ItemClassification.filler
    return ItemClassification.useful  # Augment, Weapon Slots, Weapon Licenses


class ArcRaidersWorld(World):
    """ARC Raiders is a PvPvE extraction shooter. Raid topside, kill ARC, and get out alive.
    Checks come from your synced raids on arctracker.io. Items unlock what you may bring in."""
    game = D.GAME
    web = ArcRaidersWeb()
    options_dataclass = ArcRaidersOptions
    options: ArcRaidersOptions
    topology_present = False

    item_name_to_id = {n: D.ITEM_BASE + i for i, n in enumerate(D.all_item_names())}
    location_name_to_id = {n: D.LOCATION_BASE + i for i, n in enumerate(D.all_location_names())}
    item_name_groups = {
        "Map Access": {D.map_access_name(m) for m in D.MAP_NAMES},
        "Weapon Licenses": {D.license_name(c) for c in D.WEAPON_CLASSES},
        "Kit": set(D.PROGRESSIVE),
        "Tokens": set(D.FILLER_TOKENS),
        "Traps": set(D.TRAPS),
    }

    milestone_step: int
    milestone_count: int
    starting_maps: list
    starting_classes: list

    # Universal Tracker can rebuild this world from slot_data alone (no YAML needed).
    ut_can_gen_without_yaml = True

    @staticmethod
    def interpret_slot_data(slot_data: dict) -> dict:
        return slot_data

    # options that shape the location set / logic; echoed in slot_data so trackers can regenerate
    REGEN_OPTIONS = ("goal", "core_hunt_count", "require_boss_core", "core_checks_per_type", "value_goal",
                     "value_milestone_step", "extraction_checks", "map_extraction_checks", "raid_value_checks",
                     "arc_kill_checks", "new_quest_checks", "new_blueprint_checks", "hideout_upgrade_checks",
                     "project_phase_checks", "logic_difficulty", "starting_maps", "starting_weapon_classes")

    # ------------------------------------------------------------------ setup
    def generate_early(self) -> None:
        passthrough = (getattr(self.multiworld, "re_gen_passthrough", None) or {}).get(self.game)
        if passthrough:
            for key, value in passthrough.get("options", {}).items():
                getattr(self.options, key).value = value

        goal = self.options.value_goal.value
        step = max(self.options.value_milestone_step.value, math.ceil(goal / D.MAX_VALUE_MILESTONES))
        self.milestone_step = step
        self.milestone_count = math.ceil(goal / step)

        if passthrough:
            self.starting_maps = list(passthrough["starting_maps"])
            self.starting_classes = list(passthrough["starting_weapon_classes"])
        else:
            self.starting_maps = self.random.sample(D.MAP_NAMES, self.options.starting_maps.value)
            self.starting_classes = self.random.sample(D.WEAPON_CLASSES,
                                                       self.options.starting_weapon_classes.value)
        for m in self.starting_maps:
            self.push_precollected(self.create_item(D.map_access_name(m)))
        for c in self.starting_classes:
            self.push_precollected(self.create_item(D.license_name(c)))

    def _active_locations(self) -> list:
        o = self.options
        names = [D.extraction_name(i) for i in range(1, o.extraction_checks.value + 1)]
        names += [D.map_extraction_name(m, i) for m in D.MAP_NAMES
                  for i in range(1, o.map_extraction_checks.value + 1)]
        if o.raid_value_checks:
            names += [D.raid_value_name(label) for _, label, _ in D.RAID_VALUE_TIERS]
        names += [D.milestone_name(i) for i in range(1, self.milestone_count + 1)]
        if o.arc_kill_checks:
            names += [D.kill_name(n) for n, _ in D.ARC_KILL_TIERS]
        names += [D.core_name(display, i) for _, display, _ in D.CORES
                  for i in range(1, o.core_checks_per_type.value + 1)]
        for key, label, _ in D.NEW_PROGRESS:
            names += [D.progress_name(label, i) for i in range(1, self._progress_count(key) + 1)]
        return names

    def _progress_count(self, key: str) -> int:
        return getattr(self.options, D.PROGRESS_OPTIONS[key]).value

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        topside = Region("Topside", self.player, self.multiworld)
        self.multiworld.regions += [menu, topside]
        menu.connect(topside)
        for name in self._active_locations():
            topside.locations.append(
                ArcRaidersLocation(self.player, name, self.location_name_to_id[name], topside))
        goal = ArcRaidersLocation(self.player, "Goal Reached", None, topside)
        goal.place_locked_item(ArcRaidersItem("Victory", ItemClassification.progression, None, self.player))
        topside.locations.append(goal)

    # ------------------------------------------------------------------ items
    def create_item(self, name: str) -> ArcRaidersItem:
        return ArcRaidersItem(name, _classification(name), self.item_name_to_id[name], self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choice(D.FILLER_TOKENS)

    def create_items(self) -> None:
        pool = [n for n, copies in D.PROGRESSIVE.items() for _ in range(copies)]
        pool += [D.map_access_name(m) for m in D.MAP_NAMES if m not in self.starting_maps]
        required = len(pool)
        pool += [D.license_name(c) for c in D.WEAPON_CLASSES if c not in self.starting_classes]

        slots = len(self._active_locations())
        if slots < required:
            raise OptionError(f"ARC Raiders ({self.player_name}): {slots} checks can't hold the {required} "
                              f"required items. Raise extraction_checks or map_extraction_checks.")
        if slots < len(pool):  # drop extra licenses rather than fail; the dropped ones become free
            for name in pool[slots:]:
                self.push_precollected(self.create_item(name))
            pool = pool[:slots]

        filler = slots - len(pool)
        traps = round(filler * self.options.trap_percentage.value / 100)
        pool += [self.random.choice(D.TRAPS) for _ in range(traps)]
        pool += [self.get_filler_item_name() for _ in range(filler - traps)]
        self.multiworld.itempool += [self.create_item(n) for n in pool]

    # ------------------------------------------------------------------ rules
    def _scaled(self, reqs: dict) -> dict:
        shift = {0: 1, 1: 0, 2: -1}[self.options.logic_difficulty.value]
        return {n: max(0, min(D.PROGRESSIVE[n], c + shift)) for n, c in reqs.items() if c}

    def _kit_fraction(self, frac: float) -> int:
        mult = {0: 1.25, 1: 1.0, 2: 0.65}[self.options.logic_difficulty.value]
        return min(D.LOGIC_KIT_TOTAL, round(frac * 0.6 * mult * D.LOGIC_KIT_TOTAL))

    def set_rules(self) -> None:
        p = self.player
        kit = D.LOGIC_KIT
        get = self.get_location
        per = {0: 3, 1: 4, 2: 6}[self.options.logic_difficulty.value]
        cap = int(D.LOGIC_KIT_TOTAL * 0.7)

        for i in range(1, self.options.extraction_checks.value + 1):
            need = min((i - 1) // per, cap)
            get(D.extraction_name(i)).access_rule = lambda s, n=need: s.has_from_list(kit, p, n)

        for m in D.MAP_NAMES:
            access = D.map_access_name(m)
            for i in range(1, self.options.map_extraction_checks.value + 1):
                need = (i - 1) * 2
                get(D.map_extraction_name(m, i)).access_rule = \
                    lambda s, a=access, n=need: s.has(a, p) and s.has_from_list(kit, p, n)

        if self.options.raid_value_checks:
            for _, label, reqs in D.RAID_VALUE_TIERS:
                r = self._scaled(reqs)
                get(D.raid_value_name(label)).access_rule = lambda s, r=r: s.has_all_counts(r, p)

        if self.options.arc_kill_checks:
            for n, reqs in D.ARC_KILL_TIERS:
                r = self._scaled(reqs)
                get(D.kill_name(n)).access_rule = lambda s, r=r: s.has_all_counts(r, p)

        maps = list(self.item_name_groups["Map Access"])
        total = self.milestone_count
        for k in range(1, total + 1):
            need_kit = self._kit_fraction(k / total)
            need_maps = min(len(maps), 1 + (2 * k) // total)
            get(D.milestone_name(k)).access_rule = \
                lambda s, nk=need_kit, nm=need_maps: s.has_from_list(kit, p, nk) and s.has_from_list(maps, p, nm)

        core_rules = {tier: self._scaled(reqs) for tier, reqs in D.CORE_TIER_REQS.items()}
        for _, display, tier in D.CORES:
            r = core_rules[tier]
            for i in range(1, self.options.core_checks_per_type.value + 1):
                get(D.core_name(display, i)).access_rule = lambda s, r=r: s.has_all_counts(r, p)

        # new-progress checks: a little more kit expected for every couple of checks
        step = {0: 1, 1: 2, 2: 3}[self.options.logic_difficulty.value]
        for key, label, _ in D.NEW_PROGRESS:
            for i in range(1, self._progress_count(key) + 1):
                need = min((i - 1) // step, cap)
                get(D.progress_name(label, i)).access_rule = lambda s, n=need: s.has_from_list(kit, p, n)

        value_rule = get(D.milestone_name(total)).access_rule
        # Core Hunt needs whichever tier the count (or the boss requirement) forces you into.
        n_small = sum(1 for c in D.CORES if c[2] == "small")
        n_mid = sum(1 for c in D.CORES if c[2] == "mid")
        count = self.options.core_hunt_count.value
        if self.options.require_boss_core or count > n_small + n_mid:
            hunt = core_rules["boss"]
        elif count > n_small:
            hunt = core_rules["mid"]
        else:
            hunt = core_rules["small"]
        core_rule = lambda s, r=hunt: s.has_all_counts(r, p)  # noqa: E731
        goal = self.options.goal.value
        if goal == 0:
            rule = value_rule
        elif goal == 1:
            rule = core_rule
        else:
            rule = lambda s: value_rule(s) and core_rule(s)  # noqa: E731
        get("Goal Reached").access_rule = rule
        self.multiworld.completion_condition[p] = lambda s: s.has("Victory", p)

    # ------------------------------------------------------------------ client data
    def fill_slot_data(self) -> dict:
        o = self.options
        return {
            "world_version": "0.4.0",
            "options": {k: getattr(o, k).value for k in self.REGEN_OPTIONS},
            "progress_checks": {key: self._progress_count(key) for key, _, _ in D.NEW_PROGRESS},
            "progress_labels": {key: label for key, label, _ in D.NEW_PROGRESS},
            "goal": o.goal.current_key,
            "core_hunt_count": o.core_hunt_count.value,
            "require_boss_core": bool(o.require_boss_core),
            "core_checks_per_type": o.core_checks_per_type.value,
            "cores": [list(c) for c in D.CORES],
            "core_aliases": D.CORE_ALIASES,
            "value_goal": o.value_goal.value,
            "value_metric": o.value_metric.current_key,
            "milestone_step": self.milestone_step,
            "milestone_count": self.milestone_count,
            "extraction_checks": o.extraction_checks.value,
            "map_extraction_checks": o.map_extraction_checks.value,
            "raid_value_checks": bool(o.raid_value_checks),
            "arc_kill_checks": bool(o.arc_kill_checks),
            "referee_mode": o.referee_mode.current_key,
            "death_link": bool(o.death_link),
            "maps": {slug: name for slug, name in D.MAPS},
            "raid_value_tiers": {label: v for v, label, _ in D.RAID_VALUE_TIERS},
            "arc_kill_tiers": [n for n, _ in D.ARC_KILL_TIERS],
            "tier_rules": D.TIER_RULES,
            "starting_maps": self.starting_maps,
            "starting_weapon_classes": self.starting_classes,
        }
