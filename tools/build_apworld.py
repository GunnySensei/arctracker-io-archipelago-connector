"""Zip worlds/arc_raiders into build/arc_raiders.apworld with the manifest fields AP 0.6.x expects.
Optional: --install <custom_worlds dir> copies it there too."""
import json
import pathlib
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "worlds" / "arc_raiders"
OUT = ROOT / "build" / "arc_raiders.apworld"


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    manifest = json.loads((SRC / "archipelago.json").read_text())
    manifest.update({"version": 7, "compatible_version": 7})
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SRC.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and f.name != "archipelago.json":
                z.write(f, "arc_raiders/" + f.relative_to(SRC).as_posix())
        z.writestr("arc_raiders/archipelago.json", json.dumps(manifest, indent=4))
    print("built", OUT)
    if "--install" in sys.argv:
        dest = pathlib.Path(sys.argv[sys.argv.index("--install") + 1])
        shutil.copy2(OUT, dest / OUT.name)
        print("installed to", dest)


if __name__ == "__main__":
    main()
