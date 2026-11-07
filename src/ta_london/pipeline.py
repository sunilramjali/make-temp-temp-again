"""Run all ingest -> validate -> indicators -> write parquet steps.

No loaders exist yet: they are added per dataset once the raw files have been inspected.
Run with `uv run python -m ta_london.pipeline`.
"""

from ta_london.paths import RAW


def main() -> None:
    files = [p for p in RAW.rglob("*") if p.is_file() and p.name != ".gitkeep"]
    print(f"{len(files)} raw file(s) in {RAW}. No loaders implemented yet, nothing written.")


if __name__ == "__main__":
    main()
