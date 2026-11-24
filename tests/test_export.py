"""Testes da exportação para o painel (JSON) sobre a mini-temporada de conftest.py."""
import json

import pytest

from f1pipeline.export import build_dashboard_data, write_dashboard_data
from f1pipeline.transform import build_tables

MANIFEST = {"release": "v-test", "commit": "abcdef123456", "commit_date": "2026-01-01",
            "source": "F1DB", "license": "CC BY 4.0"}


@pytest.fixture()
def data(raw_dir):
    return build_dashboard_data(build_tables(raw_dir, 2026), MANIFEST, 2026)


def test_structure_and_row_shape(data):
    assert [d["id"] for d in data["drivers"]] == ["ab-one", "cd-two"]
    assert [t["id"] for t in data["teams"]] == ["alpha", "beta"]
    assert len(data["results"]) == 2
    assert all(len(row) == len(data["resultCols"]) for row in data["results"])
    assert all(len(row) == len(data["pitCols"]) for row in data["pits"])
    assert data["meta"]["lastRound"] == 1 and data["meta"]["commit"] == "abcdef1"


def test_result_rows_carry_points_pole_and_fastest_lap(data):
    cols = data["resultCols"]
    winner, retired = (dict(zip(cols, row)) for row in data["results"])
    assert (winner["pos"], winner["ptsRace"], winner["pole"], winner["fl"]) == (1, 25, 1, 1)
    assert (retired["pos"], retired["status"], retired["pole"], retired["fl"]) == (None, "DNF", 0, 0)
    assert retired["info"] == "Engine"


def test_red_flag_stops_are_excluded_but_reported(data):
    assert len(data["pits"]) == 1 and data["pits"][0][4] == 22.5
    meta = data["meta"]
    assert (meta["pitExcluded"], meta["pitExcludedRounds"], meta["pitExcludedLaps"]) == (1, [1], [3])
    assert meta["pitExcludedMinutes"] == 31


def test_unknown_grand_prix_gets_automatic_label(data):
    assert data["rounds"][0]["code"] == "TES" and data["rounds"][0]["name"] == "Testland"


def test_sprint_without_race_row_is_rejected(raw_dir):
    tables = build_tables(raw_dir, 2026)
    ghost = tables["Resultados_Corrida"].iloc[[0]].copy()
    ghost["Rodada"] = 99
    tables["Resultados_Sprint"] = ghost
    with pytest.raises(ValueError, match="Sprints sem linha de corrida"):
        build_dashboard_data(tables, MANIFEST, 2026)


def test_write_is_valid_compact_utf8_json(data, tmp_path):
    data["teams"][0]["name"] = "Equipé"
    out = tmp_path / "sub" / "data.json"
    write_dashboard_data(data, out)
    text = out.read_text(encoding="utf-8")
    assert "Equipé" in text and ", " not in text.split('"results"')[0]
    assert json.loads(text)["meta"]["year"] == 2026
