"""Fail when tracked dotenv files could carry secrets into the repository."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ALLOWED_DOTENV_NAMES = {".env.example", ".env.sample", ".env.template"}


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_forbidden_dotenv(path: str) -> bool:
    name = Path(path).name
    if name in ALLOWED_DOTENV_NAMES:
        return False
    return name == ".env" or name.startswith(".env.")


def find_forbidden_dotenv_files(root: Path | None = None) -> list[str]:
    repo_root = root or Path.cwd()
    return [path for path in tracked_files(repo_root) if is_forbidden_dotenv(path)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    forbidden = find_forbidden_dotenv_files(args.root)
    if forbidden:
        print("Tracked dotenv files are forbidden:")
        for path in forbidden:
            print(f"- {path}")
        return 1
    print("No tracked dotenv files found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
