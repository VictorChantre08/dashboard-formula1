"""Caminhos e constantes do projeto."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "f1db"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "output"
DASHBOARD_DIR = ROOT / "dashboard"

F1DB_URL = "https://github.com/f1db/f1db"
DEFAULT_YEAR = 2026
