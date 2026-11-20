"""Static game data for the ARC Raiders world. IDs come from list order: only append, never reorder."""

GAME = "ARC Raiders"
ITEM_BASE = 77_330_000
LOCATION_BASE = 77_340_000

# (api slug, display name). Slugs match the `map` field of /api/v2/user/rounds.
MAPS = [
    ("dam-battleground", "Dam Battlegrounds"),
    ("buried-city", "Buried City"),
    ("the-spaceport", "The Spaceport"),
    ("blue-gate", "The Blue Gate"),
    ("stella-montis", "Stella Montis"),
    ("riven-tides", "Riven Tides"),
    ("pendola-pass", "Pendola Pass"),
]
MAP_NAMES = [name for _, name in MAPS]

WEAPON_CLASSES = ["Assault Rifle", "Battle Rifle", "SMG", "Shotgun", "Pistol",
                  "Hand Cannon", "Sniper Rifle", "LMG", "Special"]

HEALING = "Progressive Healing"
SHIELDS = "Progressive Shields"
RARITY = "Progressive Weapon Rarity"
TIER = "Progressive Weapon Tier"
THROWABLES = "Progressive Throwables"
AUGMENT = "Progressive Augment"
SLOTS = "Progressive Weapon Slots"

# name -> copies in the pool. Tier 0 is what you have before receiving any copy.
PROGRESSIVE = {HEALING: 4, SHIELDS: 3, RARITY: 4, TIER: 3, THROWABLES: 3, AUGMENT: 3, SLOTS: 1}
LOGIC_KIT = [HEALING, SHIELDS, RARITY, TIER, THROWABLES]  # the ones rules depend on
LOGIC_KIT_TOTAL = sum(PROGRESSIVE[n] for n in LOGIC_KIT)

# What each tier allows. Sent to the client in slot_data for the permissions panel and referee.
TIER_RULES = {
    HEALING: ["2 common heals", "4 heals, up to Uncommon", "6 heals, up to Rare", "10 heals, any rarity", "Unlimited"],
    SHIELDS: ["No shield", "Light shield", "Medium shield", "Heavy shield"],
    RARITY: ["Common (grey)", "Uncommon (green)", "Rare (blue)", "Epic (purple)", "Legendary (gold)"],
    TIER: ["Tier I", "Up to II", "Up to III", "Up to IV (and Legendaries)"],
    THROWABLES: ["None", "2 grenades/mines", "5 grenades/mines", "Unlimited"],
    AUGMENT: ["Free/basic augment only", "Up to Uncommon", "Up to Rare", "Any"],
    SLOTS: ["1 weapon", "2 weapons"],
}

FILLER_TOKENS = ["+1 Heal Token", "Shield Bump Token", "Rarity Bump Token", "Free Throwable Token", "Insurance Token"]
TRAPS = ["Free Loadout Only Trap", "Pistol Only Trap", "No Heals Trap", "Loud Raid Trap", "Drop Your Best Item Trap"]

# ---- locations
MAX_EXTRACTIONS = 60
MAX_MAP_EXTRACTIONS = 5
MAX_VALUE_MILESTONES = 40

# (threshold, label, requirements by progressive item name)
RAID_VALUE_TIERS = [
    (10_000, "10k", {}),
    (25_000, "25k", {RARITY: 1}),
    (50_000, "50k", {RARITY: 1, SHIELDS: 1}),
    (100_000, "100k", {RARITY: 2, SHIELDS: 2, TIER: 1, HEALING: 1}),
    (150_000, "150k", {RARITY: 2, SHIELDS: 2, TIER: 2, HEALING: 2}),
    (200_000, "200k", {RARITY: 3, SHIELDS: 3, TIER: 2, HEALING: 2, THROWABLES: 1}),
]
ARC_KILL_TIERS = [
    (10, {}),
    (25, {}),
    (50, {RARITY: 1}),
    (100, {RARITY: 1, TIER: 1}),
    (200, {RARITY: 2, TIER: 1, SHIELDS: 1}),
    (350, {RARITY: 2, TIER: 2, SHIELDS: 2}),
    (500, {RARITY: 3, TIER: 2, SHIELDS: 2, HEALING: 2}),
]


# ---- ARC enemy cores: (item id, display name, tier). Proof of a kill when it shows up in stash/loadout.
CORES = [
    ("tick_pod", "Tick Pod", "small"),
    ("pop_trigger", "Pop Trigger", "small"),
    ("fireball_burner", "Fireball Burner", "small"),
    ("wasp_driver", "Wasp Driver", "small"),
    ("hornet_driver", "Hornet Driver", "small"),
    ("snitch_scanner", "Snitch Scanner", "small"),
    ("spotter_relay", "Spotter Relay", "small"),
    ("firefly_burner", "Firefly Burner", "small"),
    ("rocketeer_driver", "Rocketeer Driver", "mid"),
    ("leaper_pulse_unit", "Leaper Pulse Unit", "mid"),
    ("bastion_cell", "Bastion Cell", "mid"),
    ("bombardier_cell", "Bombardier Cell", "mid"),
    ("sentinel_firing_core", "Sentinel Firing Core", "mid"),
    ("shredder_gyro", "Shredder Gyro", "mid"),
    ("surveyor_vault", "Surveyor Vault", "mid"),
    ("comet_igniter", "Comet Igniter", "mid"),
    ("turbine_compressor", "Turbine Compressor", "mid"),
    ("matriarch_reactor", "Matriarch Reactor", "boss"),
    ("queen_reactor", "Queen Reactor", "boss"),
]
# Damaged drops still prove the kill; they count as the base core.
CORE_ALIASES = {f"damaged_{c}": c for c in
                ("tick_pod", "fireball_burner", "wasp_driver", "hornet_driver", "snitch_scanner", "rocketeer_driver")}
CORE_TIER_REQS = {
    "small": {},
    "mid": {RARITY: 1, TIER: 1, SHIELDS: 1, HEALING: 1},
    "boss": {RARITY: 2, TIER: 2, SHIELDS: 2, HEALING: 2, THROWABLES: 1},
}
MAX_CORE_CHECKS = 3


def core_name(display: str, i: int) -> str:
    return f"Loot a {display} #{i}"


# ---- "new progress" checks: counted only from progress made after you connect (veteran-account friendly).
# (key, location label, max checks)
NEW_PROGRESS = [
    ("quest", "New Quest Completed", 30),
    ("blueprint", "New Blueprint Learned", 20),
    ("hideout", "Hideout Upgrade", 15),
    ("project", "Project Phase Completed", 15),
]


PROGRESS_OPTIONS = {"quest": "new_quest_checks", "blueprint": "new_blueprint_checks",
                    "hideout": "hideout_upgrade_checks", "project": "project_phase_checks"}


def progress_name(label: str, i: int) -> str:
    return f"{label} #{i}"


def extraction_name(i: int) -> str:
    return f"Extraction #{i}"


def map_extraction_name(map_name: str, i: int) -> str:
    return f"{map_name} Extraction #{i}"


def raid_value_name(label: str) -> str:
    return f"Extract a Raid Worth {label}+"


def milestone_name(i: int) -> str:
    return f"Total Extracted Milestone #{i}"


def kill_name(n: int) -> str:
    return f"ARC Kills: {n}"


def map_access_name(map_name: str) -> str:
    return f"Map Access: {map_name}"


def license_name(weapon_class: str) -> str:
    return f"Weapon License: {weapon_class}"


def all_location_names() -> list:
    names = [extraction_name(i) for i in range(1, MAX_EXTRACTIONS + 1)]
    names += [map_extraction_name(m, i) for m in MAP_NAMES for i in range(1, MAX_MAP_EXTRACTIONS + 1)]
    names += [raid_value_name(label) for _, label, _ in RAID_VALUE_TIERS]
    names += [milestone_name(i) for i in range(1, MAX_VALUE_MILESTONES + 1)]
    names += [kill_name(n) for n, _ in ARC_KILL_TIERS]
    # appended in v0.2: core checks (keep after everything above so earlier IDs never shift)
    names += [core_name(display, i) for _, display, _ in CORES for i in range(1, MAX_CORE_CHECKS + 1)]
    # appended in v0.3: new-progress checks
    names += [progress_name(label, i) for _, label, n in NEW_PROGRESS for i in range(1, n + 1)]
    return names


def all_item_names() -> list:
    return (list(PROGRESSIVE) + [map_access_name(m) for m in MAP_NAMES]
            + [license_name(c) for c in WEAPON_CLASSES] + FILLER_TOKENS + TRAPS)
