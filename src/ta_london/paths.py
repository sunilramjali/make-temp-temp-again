"""All project paths, resolved from the repo root. Nothing else should hard-code a path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"
SOURCES_CSV = DATA / "sources.csv"

POLICY = ROOT / "policy"
SERVICES_MAP = POLICY / "services_map.csv"

OUTPUTS = ROOT / "outputs"
