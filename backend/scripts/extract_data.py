"""Extract the retail zip into backend/data/.

Drop the 8451_The_Complete_Journey_2_Sample*.zip (from the assignment) into
`backend/data/`, then run:

    python -m scripts.extract_data

It unzips any *.zip in that directory alongside its source, extracting only
the three expected CSVs (households, products, transactions).
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXPECTED = ("household", "product", "transaction")


def main() -> int:
    zips = sorted(DATA_DIR.glob("*.zip"))
    if not zips:
        print(f"No .zip found in {DATA_DIR}. Drop the retail zip there first.", file=sys.stderr)
        return 1

    for archive in zips:
        print(f"Extracting {archive.name}...")
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not name.lower().endswith(".csv"):
                    continue
                if not any(keyword in name.lower() for keyword in EXPECTED):
                    continue
                target = DATA_DIR / name
                with zf.open(info) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                print(f"  -> {target.relative_to(DATA_DIR.parent)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
