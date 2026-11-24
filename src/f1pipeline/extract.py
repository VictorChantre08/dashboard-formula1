"""Extração: sincroniza o repositório aberto F1DB (CC BY 4.0) em data/raw/f1db.

O F1DB publica uma nova versão depois de cada corrida. Para atualizar os dados
basta rodar o pipeline de novo: o clone raso é atualizado para o commit mais recente.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import F1DB_URL, RAW_DIR


def _git(*args: str, cwd: Path | None = None) -> str:
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1"}  # só precisamos dos YAML
    done = subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True)
    return done.stdout.strip()


def read_manifest(raw_dir: Path = RAW_DIR) -> dict:
    """Identifica exatamente qual versão da fonte foi usada (proveniência)."""
    commit, date, subject = _git("log", "-1", "--format=%H%n%cs%n%s", cwd=raw_dir).splitlines()
    return {"source": F1DB_URL, "license": "CC BY 4.0",
            "commit": commit, "commit_date": date, "release": subject.replace("release: ", "")}


def sync_f1db(raw_dir: Path = RAW_DIR) -> dict:
    """Clona (primeira vez) ou atualiza (demais vezes) o F1DB e devolve o manifesto."""
    raw_dir = Path(raw_dir)
    if (raw_dir / ".git").exists():
        _git("fetch", "--depth", "1", "origin", "HEAD", cwd=raw_dir)
        _git("reset", "--hard", "FETCH_HEAD", cwd=raw_dir)
    else:
        raw_dir.parent.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", F1DB_URL, str(raw_dir))
    return read_manifest(raw_dir)
