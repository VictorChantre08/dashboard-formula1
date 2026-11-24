"""Teste de ponta a ponta do transform + validate em uma mini-temporada (1 corrida, 2 pilotos)."""
from f1pipeline.transform import build_tables
from f1pipeline.validate import all_ok, run_checks

def test_tables_are_built_and_consistent(raw_dir):
    tables = build_tables(raw_dir, 2026)

    results = tables["Resultados_Corrida"]
    assert len(results) == 2
    dnf = results.set_index("Piloto_ID").loc["cd-two"]
    assert dnf["Situacao"] == "DNF" and dnf["Pontos"] == 0 and dnf["Motivo_Abandono"] == "Engine"

    cal = tables["Calendario"].iloc[0]
    assert cal["Status"] == "Concluída" and cal["Vencedor"] == "Ana One" and cal["Pole"] == "Ana One"
    assert cal["Hora_UTC"] == "14:00"

    pilots = tables["Pilotos"].set_index("Piloto_ID")
    assert pilots.loc["ab-one", ["Vitorias", "Podios", "Poles", "Pontos_Calculados"]].tolist() == [1, 1, 1, 25]
    assert pilots.loc["cd-two", "Abandonos"] == 1
    assert tables["Qualificacao"]["Q3_s"].tolist() == [89.0, 89.8]


def test_validation_passes_on_consistent_data(raw_dir):
    report = run_checks(build_tables(raw_dir, 2026))
    assert all_ok(report), report.to_string()


def test_validation_catches_points_mismatch(raw_dir):
    tables = build_tables(raw_dir, 2026)
    tables["Classif_Pilotos"].loc[0, "Pontos"] = 26  # classificação oficial adulterada
    report = run_checks(tables)
    assert not all_ok(report)
