"""Replace identifiers in tests/fixtures with fake ones (request ids, round/match ids). Game data is kept so the
offline tests still exercise real shapes and numbers. Idempotent."""
import json
import pathlib
import uuid

FIX = pathlib.Path(__file__).resolve().parent.parent / "tests" / "fixtures"
NS = uuid.UUID("6f1d2a3e-0000-4000-8000-a5c0ffee0000")


def main() -> None:
    for f in sorted(FIX.glob("*.json")):
        if f.name == "profile.json":
            continue  # never committed (.gitignore); not used by tests
        d = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(d.get("meta"), dict) and "requestId" in d["meta"]:
            d["meta"]["requestId"] = "00000000-0000-4000-8000-000000000000"
        if f.name == "rounds.json":
            for i, r in enumerate(d["data"]["rounds"]):
                r["id"] = str(uuid.uuid5(NS, f"round-{i}"))
                r["roundId"] = f"fixture-round-{i:02d}"
        f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("anonymized", f.name)


if __name__ == "__main__":
    main()
