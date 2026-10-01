"""Write the warehouse models that are generated from Python (see turnaround_pipeline.generated_sql).

python scripts/build_warehouse_sql.py          # check, exit 1 if a generated model is stale
python scripts/build_warehouse_sql.py --write  # write them
"""

from __future__ import annotations

import argparse
import sys

from turnaround_pipeline.generated_sql import models, stale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        written = models()
        for path, text in written.items():
            path.write_text(text, encoding="utf-8")
        print(f"wrote {len(written)} generated warehouse files")
        return 0
    problems = stale()
    if problems:
        print("generated warehouse models are stale: " + ", ".join(problems))
        return 1
    print("generated warehouse models are current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
