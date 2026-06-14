from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from skill_centric_agent_system.control_plane import (  # noqa: E402
    build_seed_records,
    generate_seed_sql,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate D1 seed SQL from selectable module metadata."
    )
    parser.add_argument(
        "--modules-dir",
        type=Path,
        default=Path("registry/modules"),
        help="Directory containing governed registry module folders.",
    )
    parser.add_argument(
        "--tenants-dir",
        type=Path,
        default=Path("examples/tenants"),
        help="Directory containing neutral tenant registry fixtures.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("examples/control-plane/dev-seed.sql"),
        help="Output SQL file.",
    )
    parser.add_argument(
        "--principal-kind",
        default="role",
        help="Principal kind for generated scope bindings.",
    )
    parser.add_argument(
        "--principal-id",
        default="repository-maintainer",
        help="Principal id for generated scope bindings.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    module_paths = sorted(args.modules_dir.rglob("module.json"))
    tenant_paths = sorted(args.tenants_dir.glob("*.json")) if args.tenants_dir.exists() else []
    records = build_seed_records(
        module_paths,
        tenant_paths=tenant_paths,
        principal_kind=args.principal_kind,
        principal_id=args.principal_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate_seed_sql(records), encoding="utf-8")
    print(
        f"Wrote {args.output} from {len(module_paths)} module file(s) "
        f"and {len(tenant_paths)} tenant fixture(s)."
    )


if __name__ == "__main__":
    main()
