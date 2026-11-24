"""Leitura de YAML sem a armadilha sexagesimal do YAML 1.1.

O PyYAML padrão converte valores como `14:00` em inteiros (14*60 = 840).
O F1DB usa horários nesse formato, então removemos essa regra do loader.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml


class _Loader(yaml.SafeLoader):
    pass


_Loader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers
          if tag not in ("tag:yaml.org,2002:int", "tag:yaml.org,2002:float")]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:int", re.compile(r"^[-+]?[0-9]+$"), list("-+0123456789"))
_Loader.add_implicit_resolver(
    "tag:yaml.org,2002:float", re.compile(r"^[-+]?[0-9]+\.[0-9]+$"), list("-+0123456789"))

_cache: dict[Path, object] = {}


def read_yaml(path: Path):
    """Lê um arquivo YAML (com cache). Retorna None se o arquivo não existir."""
    path = Path(path)
    if path not in _cache:
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                _cache[path] = yaml.load(fh, Loader=_Loader)
        else:
            _cache[path] = None
    return _cache[path]
