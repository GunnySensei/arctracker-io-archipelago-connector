# ARC Raiders: Archipelago World Design (draft v1, 2026-11-20)

## Pillars
1. **Works on veteran accounts.** Every check counts progress made *after* the session starts (a baseline snapshot), never existing progress.
2. **Automatic checks, honor-system items.** The client finds checks through the arctracker.io API. Items you receive change what you may bring into a raid, and you follow those rules on your honor. The client also inspects your loadout to warn you when you break a rule.
3. **Progressive kit is the core loop.** You start a seed under-geared. Items gradually loosen the limits: more heals, better shields, higher-rarity weapons.

---

## Items (what other players send you)

### Progressive kit (the main progression)
| Item | Count | Tiers (a raid loadout may include…) |
|---|---|---|
| Progressive Healing | 4 | T0: 2 common heals · T1: 4 heals, Uncommon max · T2: 6 heals, Rare max · T3: 10 heals, any rarity · T4: unlimited |
| Progressive Shields | 3 | T0: none · T1: Light · T2: Medium · T3: Heavy |
| Progressive Weapon Rarity | 4 | T0: Common (grey) · T1: Uncommon (green) · T2: Rare (blue) · T3: Epic (purple) · T4: Legendary (gold) |
| Progressive Weapon Tier | 3 | T0: tier I only · T1: up to II · T2: up to III · T3: IV |
| Progressive Throwables | 3 | T0: none · T1: 2 grenades/mines · T2: 5 · T3: unlimited |
| Progressive Augment | 3 | T0: Free/basic only · then up by rarity |
| Progressive Weapon Slots | 1 | T0: 1 weapon · T1: 2 weapons |

**Two weapon axes.** A weapon is allowed only if **both** its rarity and its tier are unlocked. Each base weapon has a fixed rarity, so rarity decides *which* guns you may bring, and tier decides *how upgraded* they can be. The data has 22 tiered weapons (I–IV): Common: Ferro, Hairpin, Kettle, Rattler, Stitcher · Uncommon: Arpeggio, Bantam, Burletta, Il Toro, Stiletto · Rare: Anvil, Canto, Osprey, Rascal, Renegade, Torrente, Venator · Epic: Bettina, Bobcat, Hullcracker, Tempest, Vulcano. Legendaries (Aphelion, Dolabra, Equalizer, Jupiter) and every "Amplified ___" variant have no tier and count as tier IV. They need Rarity T4 plus Tier T3. The referee reads the roman numeral from the name of the gun in your loadout.

These are the planned tier tables. The exact numbers still need tuning, and the item categories will come from the data (`mechanics.classification`: Utility.Regenerative, Utility.Grenade, Utility.Mine, Augment, Shield…).

### Unlocks
- **Map Access** ×6: you start on one map (an option), and the 7 maps are Dam Battlegrounds, Spaceport, Buried City, Blue Gate, Stella Montis, Riven Tides and Pendola Pass.
- **Weapon Class License** ×~11: you start with 1 or 2. The classes are Assault Rifle, Battle Rifle, SMG, Shotgun, Pistol, Hand Cannon, Sniper, LMG and Special. Firearm.* gives the exact split.
- Optional: **Trader / Hideout Station licenses**, for permission to buy from Celeste or to craft at the Gunsmith, and so on.

### Filler and traps (a big part of this design)
Useful filler, saved up as **tokens** that you spend from the client UI:
- `+1 Heal (one raid)`, `+1 Shield Tier (one raid)`, `Rarity Bump (one raid)`, `Free Throwable`
- `Insurance`: cancels your next trap.

Traps are queued in the client as obligations, and each one is cleared when you tick it after the raid:
- `Free Loadout Only`, `Pistol Only`, `No Heals`, `Drop Your Best Item`, `Loud Raid` (you must fire the flare or ring the guitar), `Solo Drop`.

---

## Locations (checks): all counted from the baseline, all repeatable
| Group | Count (default) | Detected from |
|---|---|---|
| Extractions | Extract #1…#N (N=20) | /user/rounds outcome=extracted |
| Map extracts | per map you can enter: Extract on X #1…#k (k=2) | rounds.map |
| Single-raid value | one check each for an extraction worth ≥ 10k, 25k, 50k, 100k or 200k | round value |
| Cumulative value | one check for every 50k extracted, up to the goal | sum of round value |
| Kill milestones | 10, 25, 50, 100, 200 kills total | rounds.kills |
| **Enemy cores** | first and second loot of each enemy part (see below) | round loot or stash delta |
| Trinkets | N distinct trinkets looted (pool of 92) | loot or stash delta |
| Quest / Blueprint / Hideout / Project | "any new quest #1…#N" and so on (optional, count-based so veteran accounts still work) | delta from the baseline |

### Enemy core tiers (also used for logic)
- **Small:** Tick Pod, Pop Trigger, Wasp Driver, Hornet Driver, Snitch Scanner, Spotter Relay, Firefly Burner, Turbine Compressor
- **Mid:** Rocketeer Driver, Leaper Pulse Unit, Bastion Cell, Bombardier Cell, Sentinel Firing Core, Shredder Gyro, Surveyor Vault
- **Boss:** Matriarch Reactor, Queen Reactor

(The "Damaged ___" variants also count as proof of the kill.)

---

## Goals (pick one in the YAML)
1. **Core Hunt** (the default): loot N distinct enemy cores after the baseline (N is an option, default 10), and optionally require a Matriarch or Queen Reactor as the last one.
2. **Extracted Value**: extract a total of X (option, default 500k) after the baseline.
3. **Both**: you need to finish both goals.

## Logic (soft and adjustable, with an option for `logic_difficulty`: casual, standard or sweaty)
- Map-specific checks need that map's access.
- Small cores need nothing beyond the starting kit.
- Mid cores need Rarity T1, Weapon Tier T1 (II), Shields T1 and Healing T1.
- Boss cores need Rarity T2, Weapon Tier T2 (III), Shields T2, Healing T2 and Throwables T1.
- Each value threshold needs a matching rarity or shield tier, for example 100k+ needs Shields T2.
- Goal: the Core Hunt goal needs the boss tier, and the Value goal needs about 60% of the progressive items.

## Player options (YAML)
`goal`, `core_hunt_count`, `require_boss_core`, `value_goal`, `starting_maps`, `starting_weapon_classes`,
`extraction_checks`, `map_extract_checks`, `include_value_checks`, `include_kill_checks`,
`include_trinkets`, `include_quests/blueprints/hideout/projects` (counts), `trap_percentage`,
`filler_token_weights`, `logic_difficulty`, `death_link`, `referee_mode` (off, warn or strict).

## Multiplayer / social
- Every raider has their own slot and their own ARC Tracker key. A squad raid still counts for each player separately.
- DeathLink: a round with outcome=died sends a death to everyone. A death received adds a "No Heals" trap to your queue.

## API facts (spike 2026-11-20, fixtures in tests/fixtures)
- **rounds**: id, map (slug), outcome (extracted/died), durationMs, valueBroughtIn, valueExtracted, **netValue** (+/-),
  kills, **arcKills**, playerKills, playerDowns, damage, score, roundEndedAt (only accurate to the half hour), syncedAt, seasonNumber, isLegacy.
  `lootedItems` was **null on all 20 rounds**, so there is no itemized loot. Rounds appeared about 10–15 min after the raid ended.
- **stash**: itemId + quantity for every stack (227 of 232 slots), a total value, and syncedAt. → **Cores and trinkets come from comparing stash snapshots.**
- **loadout**: shield, augment, weapon1/2 (itemId includes the tier, e.g. `anvil_iv`, plus attachments), quickItems with quantity, backpack, safePocket.
  → The referee is fully possible. Caveat: this snapshot is taken at sync time (after the raid), so it may not match what you brought in.
- **quests** completed bool · **blueprints** learned bool · **hideout** currentLevel/maxLevel · **projects** phases with `submitted` counts per requirement.

## Design consequences
- Value goal: count the sum of `valueExtracted` (option: or `netValue`) over rounds after the baseline. Single-raid checks use `valueExtracted`.
- Kill checks use `arcKills`. PvP (`playerKills`) is a separate, optional check group.
- Core check: compare the count of each core item between consecutive stash snapshots. Any increase is counted as looted.
  Selling, recycling or project hand-ins only lower the count, so they can't create false positives. Buying a core from a trader would, but that's rare.
- Extra check ideas: raid duration (survive 20+ minutes) and `score` thresholds.

## Core Hunt as built (v0.2)
- 19 cores: small 8 (Tick Pod, Pop Trigger, Fireball Burner, Wasp/Hornet Driver, Snitch Scanner, Spotter Relay, Firefly Burner),
  mid 9 (Rocketeer Driver, Leaper Pulse Unit, Bastion/Bombardier Cell, Sentinel Firing Core, Shredder Gyro, Surveyor Vault,
  Comet Igniter, Turbine Compressor), boss 2 (Matriarch/Queen Reactor). Damaged variants count as the base core.
  The tiers for Comet Igniter, Turbine Compressor and Surveyor Vault are guesses.
- Detection: when you first connect, the client takes a core snapshot with no credit. On every new raid it fetches stash + loadout (2 calls)
  and credits increases. It waits until the stash's syncedAt is at least as new as the raid.
- Options: goal (extracted_value / core_hunt [default] / both), core_hunt_count (3-19, default 10), require_boss_core,
  core_checks_per_type (0-3, default 2: "Loot a X #1/#2").

## Still open
- Which maps does the Matriarch or Queen spawn on? That would make the boss logic depend on maps too.
- How does a free account get its sync? These rounds have source "app", meaning the Link app.


## Phase 6: In-game overlay (design approved 2026-11-20)
- Mockup: `overlay/overlay.html` (preview over a real 1440p frame: `?scale=1.33&bg=preview_bg.png`; controls bar, H toggles it).
- **Never injected into the game** (Easy Anti-Cheat). It's a page the client serves on localhost, viewed in one of these:
  Steam overlay browser pinned (Shift+Tab), an always-on-top window (borderless windowed), OBS, or a phone/second screen (optional LAN).
- Placement: top right, under the in-game perf line (top 40px, right 24px at 1x). It stays clear of the compass/timer (top centre)
  and the weapon slots (bottom right). Ultrawide gets an inward offset setting; `scale` for resolution (1.33 at 1440p).
- Look: Bahnschrift condensed, warm off-white text, teal accent from the health bar, 78% dark panel with blur, game rarity colours.
- Full view: GUNS rarity pips + "≤ Blue", TIER, SHIELD, HEALS, NADES, AUG, SLOTS, LIC, MAPS · traps (max 2 + "+N more", Done button)
  · CORES n/N, BOSS, "+ <new core>" · VALUE bar.
- Compact view (during raids): traps + cores + value only.
- Changes flash amber and fade; new cores show as "+ Rocketeer Driver" for a while.
- Data: the client serves /state.json; the page polls it every ~2s. Done/Spend POST back to the client. Zero extra arctracker calls.
- Extras: Windows toast notifications and optional text-to-speech for items/traps/checks.

## Phase 5 + 6 as built (v0.3.0)
- New-progress checks: New Quest Completed / New Blueprint Learned / Hideout Upgrade / Project Phase Completed #N,
  counted from the shared snapshot (taken together with cores, re-taken the same way when a sync carries old raids).
- Universal Tracker: `ut_can_gen_without_yaml`; slot_data["options"] + starting maps/classes rebuild the seed exactly (tools/test_ut.py).
  A custom PopTracker pack was skipped in favour of this.
- Overlay: the client serves http://localhost:38300/ (port and LAN setting in arc_raiders_client.json). /state.json, POST /action.
  Pop-up cards for: checks you hit (incl. items you send others), items others send you, traps (red), cores, goal.
  Views: full / compact / pop-ups only; scale + inset (for ultrawide) sliders; H shows the controls.
- Toasts + voice (PowerShell 5.1, no installs). Bursts are combined into one summary. Windows hides toasts while a game
  is in the foreground, so the overlay pop-ups + voice are the in-game channels.

## Desktop HUD (v0.3.1)
- `client/hud.py`: Tk window (bundled with frozen AP). Borderless, topmost, colour-key transparent (click-through outside panels), WS_EX_NOACTIVATE + TOOLWINDOW.
  Auto-sizes to the panel + pop-up cards; drag by the title row; right-click for view/scale/opacity/reset/close; settings in arc_raiders_hud.json.
- Opened from the client ("Desktop HUD" button, /arc_hud) or the Launcher ("ARC Raiders HUD"). Needs borderless windowed.
- The Steam overlay browser is kept as a fallback (it draws a grey window background and ignores page transparency).
