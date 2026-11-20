"""Drive the scripted 'TestPartner' slot on the local test server, so the other (human) slot receives items on cue.
Usage (venv python):
  partner.py send [N]   check N partner locations that hold the player's items (default 1)
  partner.py trap       check one partner location holding a trap for the player
  partner.py prog       check one partner location holding a progression item for the player
  partner.py status     how many of the player's items the partner still holds"""
import asyncio
import json
import random
import sys

import websockets

URL = "ws://127.0.0.1:38999"
SLOT = "TestPartner"


async def main(cmd: str, n: int) -> None:
    async with websockets.connect(URL, max_size=None) as ws:
        await ws.recv()  # RoomInfo
        await ws.send(json.dumps([{"cmd": "Connect", "game": "ARC Raiders", "name": SLOT, "password": "",
                                   "uuid": "arc-partner", "version": {"major": 0, "minor": 6, "build": 7,
                                                                       "class": "Version"},
                                   "items_handling": 0, "tags": [], "slot_data": False}]))
        connected = None
        while connected is None:
            for msg in json.loads(await ws.recv()):
                if msg["cmd"] == "Connected":
                    connected = msg
                elif msg["cmd"] == "ConnectionRefused":
                    sys.exit(f"refused: {msg}")
        # send to the first other slot (the human player), whatever it's called
        target, target_name = next((int(k), v["name"]) for k, v in connected["slot_info"].items() if v["name"] != SLOT)
        missing = connected["missing_locations"]
        await ws.send(json.dumps([{"cmd": "LocationScouts", "locations": missing, "create_as_hint": 0}]))
        scouted = None
        while scouted is None:
            for msg in json.loads(await ws.recv()):
                if msg["cmd"] == "LocationInfo":
                    scouted = msg["locations"]
        for_target = [l for l in scouted if l["player"] == target]
        if cmd == "status":
            print(f"partner holds {len(for_target)} items for {target_name} "
                  f"({sum(1 for l in for_target if l['flags'] & 4)} traps, "
                  f"{sum(1 for l in for_target if l['flags'] & 1)} progression)")
            return
        pool = {"trap": [l for l in for_target if l["flags"] & 4],
                "prog": [l for l in for_target if l["flags"] & 1]}.get(cmd, for_target)
        pick = random.sample(pool, min(n, len(pool)))
        if not pick:
            print("nothing left to send for that kind")
            return
        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": [l["location"] for l in pick]}]))
        await asyncio.sleep(1)
        print(f"sent {len(pick)} item(s) to {target_name}")


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "status"
    asyncio.run(main(c, int(sys.argv[2]) if len(sys.argv) > 2 else 1))
