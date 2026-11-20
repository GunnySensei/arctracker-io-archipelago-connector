# ARC Raiders × Archipelago: How to Play

Play ARC Raiders as one game in an Archipelago multiworld. **Checks come from real raids**: extract, kill ARC,
loot cores, and finish quests. They're detected automatically through arctracker.io. **Items you receive change
what you're allowed to bring topside.** You follow those rules on your honor, and a referee tells you if your
synced loadout breaks them.

Works on **existing accounts**: only progress made *after* you first connect counts.

---

## What you need
- **ARC Raiders on Steam or Epic**, linked to a free **arctracker.io** account (via the *ARC Tracker Link* app).
- **Archipelago 0.6.4 or newer** (built and tested on 0.6.7): <https://archipelago.gg/tutorial/Archipelago/setup/en>
- Windows. The desktop HUD needs the game in **borderless windowed** mode.

## 1. Install
1. Double-click **`arc_raiders.apworld`**. The Archipelago Launcher opens and installs it.
   (Or copy it into `Archipelago\custom_worlds\` yourself.)
2. Restart the Launcher. You should now see **ARC Raiders Client** and **ARC Raiders HUD** in the list.

## 2. Get your arctracker.io keys (one time, ~3 minutes)
The client reads your raids from arctracker.io's API. It never touches the game itself, so there are no anti-cheat concerns.
1. Sign in at **arctracker.io** and make sure your ARC Raiders account is linked (ARC Tracker Link app).
2. **Settings → Developer Access → create a key.** Give it the read scopes (profile, rounds, stash, loadout,
   quests, blueprints, hideout, projects). It starts with `arc_u1_`. This is your **user key**.
3. **Developer Dashboard → register an app** (any name, e.g. "my archipelago"). It gives you an **app key**
   starting with `arc_k1_`. Make your own rather than sharing one: each app key has a 500 calls/hour limit.
4. You'll paste both into the client once. They're saved only on your PC (`Archipelago\arc_raiders_keys.json`).

## 3. Make your settings file (YAML)
Copy **`ARC Raiders.yaml`**, set `name:` to your slot name, tweak the options (each is commented), and send it
to whoever is hosting. Defaults are a good first run: Core Hunt goal (10 different ARC cores, one must be a
Matriarch or Queen Reactor), about 105 checks, 25% of fillers are traps.

## 4. Hosting (one person)
1. Put everyone's YAMLs in `Archipelago\Players\` and run **Generate** (the host needs `arc_raiders.apworld`
   installed, plus apworlds for any other custom games in the multiworld).
2. Host the result: upload the `.zip` from `Archipelago\output\` to <https://archipelago.gg/uploads>, or run
   *Host* locally.
3. Only ARC Raiders players need this apworld on their own PCs. Everyone else plays their own game as normal.

## 5. Playing
1. **Sync arctracker.io first** (their website's sync button), so your latest raids are already in.
2. Open **ARC Raiders Client** from the Launcher and connect (server address and your slot name).
3. First time: in the **ARC Raiders** tab, click **Keys**, paste both keys, and click **Save keys**.
4. On first connect the client takes a **starting snapshot**. Nothing before this moment counts.
5. Click **Desktop HUD** for the in-game overlay (see below). Then go raid.
6. **After raids, sync arctracker.io.** Free accounts sync from the website; subscribers sync automatically.
   The client checks every 2 minutes, or press **CHECK** on the HUD.

### The desktop HUD
A transparent panel that sits on top of the game (borderless windowed mode). It shows what you may bring,
your traps, Core Hunt progress, and **pop-up cards** for every check you hit and every item someone sends you.
- **Move it** by dragging the dotted triangle in its top-right corner. **Right-click** to change the view
  (Full / Compact / Pop-ups only), scale, opacity, reset its position, or close it.
- **DONE** clears a trap. **CHECK** looks for new raids now. **SYNC** opens arctracker.io (this tabs you out).
- It never takes focus from the game, so clicking it or getting new cards won't release your mouse.
- Prefer the Steam overlay? Click **Browser overlay** in the client and pin `http://127.0.0.1:38300/` in the
  Steam browser (Shift+Tab). Steam draws a grey background around it, though.

---

## The rules: what you may bring
You start under-geared. Items you receive raise these tiers. Your current tiers are always shown in the client and on the HUD.

| Item | Tier 0 (start) → max |
|---|---|
| **Progressive Weapon Rarity** | Grey → Green → Blue → Purple → Gold |
| **Progressive Weapon Tier** | I only → up to II → up to III → up to IV (Gold/Legendary guns count as IV) |
| **Progressive Shields** | None → Light → Medium → Heavy |
| **Progressive Healing** | 2 grey heals → 4 (≤ green) → 6 (≤ blue) → 10 (any) → unlimited |
| **Progressive Throwables** | None → 2 → 5 → unlimited (grenades and mines) |
| **Progressive Augment** | Free/basic → ≤ green → ≤ blue → any |
| **Progressive Weapon Slots** | 1 gun → 2 guns |
| **Weapon License: <class>** | You may only use weapon classes you're licensed for (you start with 2) |
| **Map Access: <map>** | You may only deploy to unlocked maps (you start with 1) |

A gun is allowed only if its **rarity, tier and class** are all unlocked.

### Traps (red cards) apply to your next raid, then press DONE
| Trap | Next raid… |
|---|---|
| Free Loadout Only | use a free loadout |
| Pistol Only | pistols only |
| No Heals | bring no healing items |
| Loud Raid | make noise: fire a flare or play the guitar |
| Drop Your Best Item | leave your most valuable item topside |

### Tokens: spend them in the client (or with `/arc_spend`) before a raid
| Token | One raid with… |
|---|---|
| +1 Heal Token | one heal over your limit |
| Shield Bump Token | a shield one tier higher |
| Rarity Bump Token | one gun one rarity higher |
| Free Throwable Token | one extra grenade/mine |
| Insurance Token | skip one trap (spend it, then DONE the trap) |

Mis-clicked? **Undo** in the client (or `/arc_undo`) reverses your last Spend/Done.

---

## Checks (what sends items out)
All counted only from after your first connect:
- **Extraction #N** (any map) and **<Map> Extraction #N** (needs that map unlocked)
- **Extract a Raid Worth 10k / 25k / 50k / 100k / 150k / 200k+**
- **Total Extracted Milestone #N**: every 50k of value you extract
- **ARC Kills: 10 / 25 / 50 / 100 / 200 / 350 / 500**
- **Loot a <Core> #1/#2**: 19 ARC cores (small: Tick Pod, Pop Trigger, Wasp Driver…; mid: Rocketeer Driver,
  Bastion Cell…; boss: Matriarch Reactor, Queen Reactor). Proven by the core appearing in your stash/backpack.
- **New Quest Completed / New Blueprint Learned / Hideout Upgrade / Project Phase Completed #N**

Harder checks expect more kit (logic), e.g. boss cores expect blue guns, tier III, Medium shields and 6 heals.

## Goals
- **core_hunt** (default): loot N different cores (optionally including a boss reactor)
- **extracted_value**: extract a total value (default 500k)
- **both**

## Client commands
`/arc_status` · `/arc_poll` · `/arc_sync` · `/arc_spend <token>` · `/arc_done <trap>` · `/arc_undo` ·
`/arc_hud` · `/arc_overlay` · `/arc_voice on|off` (spoken callouts) · `/arc_toasts on|off` (Windows notifications;
Windows hides these while a game is focused, so the HUD is better)

---

## Troubleshooting
- **"Sync arctracker.io before your first raid"** (red): your last arctracker sync is older than your snapshot.
  Sync on the website. If a sync brings in old raids, their cores are skipped (and the client tells you).
- **Nothing happens after a raid**: the raid isn't on arctracker yet. Sync on the website, then press CHECK.
- **HUD not visible in game**: switch the game to borderless windowed (exclusive fullscreen draws over it).
- **Keys error (401/403)**: re-create the user key with all read scopes, and check the app key is right.
- **"API calls left" getting low**: the client slows down automatically. Each player should use their own app key.
- **Port 38300 in use**: change `overlay_port` in `Archipelago\arc_raiders_client.json`.

## Privacy
Your keys stay on your PC. The client only *reads* from arctracker.io (raids, stash, loadout, progress) and talks
to your Archipelago server. Nothing is installed into or read from the game.
