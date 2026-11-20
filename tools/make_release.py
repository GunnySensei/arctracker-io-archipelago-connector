"""Build the friends package: dist/ArcRaidersAP-v<version>.zip with the apworld, YAML template, guide, changelog.
Version comes from worlds/arc_raiders/archipelago.json."""
import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERSION = json.loads((ROOT / "worlds" / "arc_raiders" / "archipelago.json").read_text())["world_version"]
NAME = f"ArcRaidersAP-v{VERSION}"
DIST = ROOT / "dist"


def main() -> None:
    subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "build_apworld.py")], check=True)
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{NAME}.zip"
    files = {
        "arc_raiders.apworld": ROOT / "build" / "arc_raiders.apworld",
        "ARC Raiders.yaml": ROOT / "ARC Raiders.yaml",
        "HOW TO PLAY.md": ROOT / "docs" / "HOW_TO_PLAY.md",
        "CHANGELOG.md": ROOT / "CHANGELOG.md",
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in files.items():
            z.write(src, f"{NAME}/{arc}")
    shutil.copy2(ROOT / "build" / "arc_raiders.apworld", DIST / "arc_raiders.apworld")
    print(f"{out}  ({out.stat().st_size // 1024} KB)")
    for arc in files:
        print("  ", arc)


if __name__ == "__main__":
    main()
