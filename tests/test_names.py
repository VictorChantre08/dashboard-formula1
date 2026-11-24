"""Nomes de exibição: arquivos e planilhas saem com a grafia correta em português."""
import pandas as pd
import pytest

from f1pipeline.load import _restantes, write_csvs, write_excel
from f1pipeline.names import COLUMN_NAMES, TABLE_NAMES, ascii_slug, display_columns, table_name
from f1pipeline.transform import build_tables
from f1pipeline.validate import run_checks

MANIFEST = {"release": "v-test", "commit": "abcdef123456", "commit_date": "2026-01-01",
            "source": "https://github.com/f1db/f1db", "license": "CC BY 4.0"}


def test_every_display_name_is_the_accented_form_of_its_key():
    for mapping in (TABLE_NAMES, COLUMN_NAMES):
        for key, shown in mapping.items():
            assert key != shown and ascii_slug(shown) == key.lower()


def test_table_name_and_slug():
    assert table_name("Calendario") == "Calendário" and table_name("Pilotos") == "Pilotos"
    assert ascii_slug("Voltas_Rápidas") == "voltas_rapidas"


def test_csv_files_and_headers_are_accented(raw_dir, tmp_path):
    tables = build_tables(raw_dir, 2026)
    stale = tmp_path / "Calendario.csv"
    stale.write_text("velho", encoding="utf-8")
    write_csvs(tables, tmp_path)
    assert not stale.exists()
    header = (tmp_path / "Resultados_Corrida.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert "Posição" in header and "Situação" in header and "Número" in header
    assert (tmp_path / "Calendário.csv").exists() and (tmp_path / "Voltas_Rápidas.csv").exists()
    assert pd.read_csv(tmp_path / "Calendário.csv").loc[0, "Status"] == "Concluída"


def test_excel_sheets_headers_and_readme_are_accented(raw_dir, tmp_path):
    import openpyxl
    tables = build_tables(raw_dir, 2026)
    out = tmp_path / "base.xlsx"
    write_excel(tables, run_checks(tables), MANIFEST, 2026, out)
    wb = openpyxl.load_workbook(out)
    assert {"Calendário", "Qualificação", "Voltas_Rápidas", "Validação", "LEIA-ME"} <= set(wb.sheetnames)
    assert [c.value for c in wb["Validação"][1]] == ["Verificação", "Valor", "Resultado", "Descrição"]
    assert "Posição" in [c.value for c in wb["Resultados_Corrida"][1]]
    readme = "\n".join(str(c.value) for row in wb["LEIA-ME"].iter_rows() for c in row if c.value)
    assert "Posição vazia" in readme and "A temporada está encerrada." in readme and "corrida(s)" not in readme
    assert wb["Calendário"].tables and list(wb["Calendário"].tables)[0] == "tbl_calendario"


def test_remaining_races_text_has_correct_singular_and_plural():
    assert _restantes(0) == "A temporada está encerrada."
    assert _restantes(1) == "Resta 1 corrida."
    assert _restantes(2) == "Restam 2 corridas."
