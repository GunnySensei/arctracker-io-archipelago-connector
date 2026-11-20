# ARC Raiders Archipelago

An [Archipelago](https://archipelago.gg) world + client for **ARC Raiders**. Checks come from real raids via the
[arctracker.io](https://arctracker.io) API. Items change what you may bring topside (honor system with a
referee), and a desktop HUD shows everything in game.

- **Players:** see [docs/HOW_TO_PLAY.md](docs/HOW_TO_PLAY.md) (also included in each release zip).
- **Design notes:** [DESIGN.md](DESIGN.md) · **Changes:** [CHANGELOG.md](CHANGELOG.md)

## Layout
| Path | What |
|---|---|
| `worlds/arc_raiders/` | the apworld: world (`__init__.py`, `data.py`, `options.py`), `client/` (client, evaluator, referee, API, overlay server, desktop HUD), `assets/` |
| `tools/` | `build_apworld.py`, `make_release.py`, `build_data.py`, `test_gen.py`, `test_ut.py`, `e2e.py`, `partner.py`, `spike.py` |
| `tests/` | offline client tests + arctracker fixtures |
| `data_raw/` | public arctracker.io game data (`/api/items`, quests, hideout, projects) |
| `overlay/` | browser-overlay preview page |

## Dev quickstart
Uses the Archipelago 0.6.7 source + venv in `C:\Games\APLocalTracker` (see `tools/*.py` for paths).
```
python -I tools/build_apworld.py --install <custom_worlds dir>   # build (+ install)
<venv>/python tests/test_client.py                                # offline evaluator/referee tests
python -I tools/test_gen.py                                       # generation smoke tests
<venv>/python tools/test_ut.py                                    # Universal Tracker regen test
python -I tools/make_release.py                                   # dist/ArcRaidersAP-v<ver>.zip
```
Keys for dev tools live in `.env` (`ARC_APP_KEY`, `ARC_USER_KEY`). It's git-ignored.
