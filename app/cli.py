from __future__ import annotations

import argparse
from pathlib import Path

from .models import mask_url, sha256_text


def main() -> None:
    parser = argparse.ArgumentParser(prog="raasfinder")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--mask", metavar="URL")
    args = parser.parse_args()

    if args.self_check:
        root = Path(__file__).resolve().parents[1]
        assert (root / "web" / "index.html").exists()
        raw = "example.com/report/2026"
        assert mask_url("https://" + raw) == raw[:5] + ("•" * (len(raw) - 8)) + raw[-3:]
        assert len(sha256_text("RaaSFinder")) == 64
        print("RaaSFinder self-check: OK")
        return

    if args.mask:
        print(mask_url(args.mask))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
