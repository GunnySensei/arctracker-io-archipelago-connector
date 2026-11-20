# Changelog

## v0.4.0 (2026-11-20): first friends release
- **Desktop HUD**: a transparent, always-on-top panel that runs inside the client (about 10 MB). It shows your kit
  rules, traps (with DONE buttons), Core Hunt progress and value, plus pop-up cards for checks you hit, items
  people send you, traps and cores. It never takes focus from the game. Drag it by the dotted corner; right-click
  for view, scale, opacity and position.
- CHECK and SYNC buttons in the HUD and the browser overlay.
- Pop-up cards queue (4 at a time) instead of dropping extras. Every item gets its own card.
- Long-polling between the HUD and the client: close to zero CPU when idle.
- Uses 127.0.0.1 everywhere (`localhost` added about 2 seconds to every request on Windows).
- Windows notifications are now off by default.

## v0.3.0
- New-progress checks: quests, blueprints, hideout upgrades, project phases.
- Universal Tracker support (rebuilds a seed from slot data, no YAML needed).
- Browser overlay (`http://127.0.0.1:38300/`), Windows toasts, voice callouts.

## v0.2.0
- Core Hunt goal and core checks (19 ARC cores; credited by comparing stash snapshots).
- Undo; protection against old raids arriving in the same sync (the "backlog").

## v0.1.0
- World: progressive kit, map access, weapon licenses, tokens and traps; extraction, value, kill and milestone checks.
- Client: polls arctracker.io, sends checks, referee, DeathLink.
