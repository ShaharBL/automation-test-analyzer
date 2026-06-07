from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from .dashboard import build_dashboard
from .parser import parse_trx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "dashboard.html"


def main() -> int:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    trx_files = sorted(INPUT_DIR.glob("*.trx"))
    if not trx_files:
        print(f"No .trx files found in {INPUT_DIR}. Drop a file there and run again.")
        return 1

    runs = []
    for path in trx_files:
        print(f"Parsing {path.name} ...")
        try:
            runs.append(parse_trx(path))
        except Exception as exc:
            print(f"  ! failed to parse {path.name}: {exc}", file=sys.stderr)

    if not runs:
        print("No parseable runs.", file=sys.stderr)
        return 1

    print("Building dashboard ...")
    html = build_dashboard(runs)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} — opening in browser.")

    webbrowser.open(OUTPUT_FILE.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
