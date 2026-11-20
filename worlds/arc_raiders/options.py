from dataclasses import dataclass

from Options import Choice, DeathLink, PerGameCommonOptions, Range, Toggle


class Goal(Choice):
    """What wins the seed. Only progress after you first connect counts.
    extracted_value: extract a total value.
    core_hunt: loot a number of different ARC enemy cores (Tick Pod, Rocketeer Driver, Matriarch Reactor...).
    both: finish both."""
    display_name = "Goal"
    option_extracted_value = 0
    option_core_hunt = 1
    option_both = 2
    default = 1


class CoreHuntCount(Range):
    """Core Hunt: how many *different* core types you must loot (19 exist: 8 small, 9 mid, 2 boss)."""
    display_name = "Core Hunt Count"
    range_start = 3
    range_end = 19
    default = 10


class RequireBossCore(Toggle):
    """Core Hunt: one of your cores must be a Matriarch Reactor or Queen Reactor."""
    display_name = "Require Boss Core"
    default = 1


class CoreChecksPerType(Range):
    """Checks for your 1st, 2nd, 3rd loot of each core type (0 turns core checks off; the goal still works)."""
    display_name = "Core Checks Per Type"
    range_start = 0
    range_end = 3
    default = 2


class ValueGoal(Range):
    """Total value to extract, counting only raids after you first connect."""
    display_name = "Value Goal"
    range_start = 100_000
    range_end = 2_000_000
    default = 500_000


class ValueMilestoneStep(Range):
    """You get a check each time your total extracted value passes another multiple of this.
    Raised automatically if it would make more than 40 milestones."""
    display_name = "Value Milestone Step"
    range_start = 25_000
    range_end = 250_000
    default = 50_000


class ValueMetric(Choice):
    """extracted: count what you walked out with.
    net: count profit (extracted minus brought in). Deaths subtract."""
    display_name = "Value Metric"
    option_extracted = 0
    option_net = 1
    default = 0


class ExtractionChecks(Range):
    """Checks for your 1st, 2nd, ... Nth successful extraction on any map."""
    display_name = "Extraction Checks"
    range_start = 0
    range_end = 60
    default = 20


class MapExtractionChecks(Range):
    """Checks per map for extracting from that map. Needs that map's access."""
    display_name = "Per-Map Extraction Checks"
    range_start = 0
    range_end = 5
    default = 2


class StartingMaps(Range):
    """How many random maps you can raid from the start."""
    display_name = "Starting Maps"
    range_start = 1
    range_end = 7
    default = 1


class StartingWeaponClasses(Range):
    """How many random weapon class licenses you start with."""
    display_name = "Starting Weapon Classes"
    range_start = 1
    range_end = 9
    default = 2


class RaidValueChecks(Toggle):
    """Checks for extracting a single raid worth 10k / 25k / 50k / 100k / 150k / 200k+."""
    display_name = "Single-Raid Value Checks"
    default = 1


class ArcKillChecks(Toggle):
    """Checks for total ARC kills: 10 / 25 / 50 / 100 / 200 / 350 / 500."""
    display_name = "ARC Kill Checks"
    default = 1


class NewQuestChecks(Range):
    """Checks for quests you complete after connecting (any quest; old completions don't count)."""
    display_name = "New Quest Checks"
    range_start = 0
    range_end = 30
    default = 5


class NewBlueprintChecks(Range):
    """Checks for blueprints you learn after connecting."""
    display_name = "New Blueprint Checks"
    range_start = 0
    range_end = 20
    default = 3


class HideoutUpgradeChecks(Range):
    """Checks for hideout station levels you gain after connecting."""
    display_name = "Hideout Upgrade Checks"
    range_start = 0
    range_end = 15
    default = 2


class ProjectPhaseChecks(Range):
    """Checks for project phases (Expeditions, Trophy Display...) you complete after connecting."""
    display_name = "Project Phase Checks"
    range_start = 0
    range_end = 15
    default = 0


class TrapPercentage(Range):
    """Percent of filler items that are traps (Free Loadout Only, Pistol Only, No Heals...)."""
    display_name = "Trap Percentage"
    range_start = 0
    range_end = 100
    default = 20


class LogicDifficulty(Choice):
    """How much kit the logic expects you to have before it sends you after harder checks."""
    display_name = "Logic Difficulty"
    option_casual = 0
    option_standard = 1
    option_sweaty = 2
    default = 1


class RefereeMode(Choice):
    """Client only: compare your synced loadout with what you have unlocked.
    off, or warn (show any rule breaks)."""
    display_name = "Referee Mode"
    option_off = 0
    option_warn = 1
    default = 1


@dataclass
class ArcRaidersOptions(PerGameCommonOptions):
    goal: Goal
    core_hunt_count: CoreHuntCount
    require_boss_core: RequireBossCore
    core_checks_per_type: CoreChecksPerType
    value_goal: ValueGoal
    value_milestone_step: ValueMilestoneStep
    value_metric: ValueMetric
    extraction_checks: ExtractionChecks
    map_extraction_checks: MapExtractionChecks
    starting_maps: StartingMaps
    starting_weapon_classes: StartingWeaponClasses
    raid_value_checks: RaidValueChecks
    arc_kill_checks: ArcKillChecks
    new_quest_checks: NewQuestChecks
    new_blueprint_checks: NewBlueprintChecks
    hideout_upgrade_checks: HideoutUpgradeChecks
    project_phase_checks: ProjectPhaseChecks
    trap_percentage: TrapPercentage
    logic_difficulty: LogicDifficulty
    referee_mode: RefereeMode
    death_link: DeathLink
