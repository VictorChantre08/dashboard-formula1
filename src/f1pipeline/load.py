"""Carga: grava CSVs (para Power BI / SQL) e um Excel formatado com as mesmas tabelas."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F3864")


def write_csvs(tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d")


def write_manifest(manifest: dict, tables: dict[str, pd.DataFrame], out_dir: Path) -> None:
    info = {**manifest, "rows": {name: len(df) for name, df in tables.items()}}
    (out_dir / "manifest.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _readme(tables: dict[str, pd.DataFrame], manifest: dict, year: int) -> pd.DataFrame:
    cal = tables["Calendario"]
    last = cal[cal["Status"] == "Concluída"].iloc[-1]
    upcoming = cal[cal["Status"] != "Concluída"]
    rows = [
        (f"Fórmula 1 — temporada {year}: base de dados", ""),
        ("Cobertura", f"Rodadas 1 a {int(last['Rodada'])} ({last['GP']}, {last['Data']:%d/%m/%Y}). "
                      f"Restam {len(upcoming)} corrida(s)."),
        ("Fonte", f"F1DB ({manifest['source']}), versão {manifest['release']}, commit {manifest['commit'][:7]} "
                  f"({manifest['commit_date']}). Licença {manifest['license']}."),
        ("Atribuição", f'Dados: F1DB ({manifest["source"].replace("https://", "")}), {manifest["license"]}.'),
        ("Notas", "Horários em UTC; nomes em inglês como na fonte; Posicao vazia = não classificado (veja Situacao)."),
        ("", ""),
        ("Aba", "Linhas"),
    ]
    rows += [(name, len(df)) for name, df in tables.items()]
    return pd.DataFrame(rows)


def _style(ws, df: pd.DataFrame, *, table: bool) -> None:
    for row in ws.iter_rows():
        for cell in row:
            cell.font = Font(name=FONT, size=10)
    for cell in ws[1]:
        cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for j, name in enumerate(df.columns, start=1):
        sample = df[name].head(300).astype(str).str.len()
        width = max([len(str(name))] + ([int(sample.max())] if len(sample) else []))
        ws.column_dimensions[get_column_letter(j)].width = min(max(width + 2, 8), 44)
        if pd.api.types.is_datetime64_any_dtype(df[name]):
            for i in range(2, len(df) + 2):
                ws.cell(row=i, column=j).number_format = "yyyy-mm-dd"
    ws.freeze_panes = "A2"
    if table and len(df):
        ref = f"A1:{get_column_letter(len(df.columns))}{len(df) + 1}"
        tab = Table(displayName=f"tbl_{ws.title.lower()}", ref=ref)
        tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(tab)


def write_excel(tables: dict[str, pd.DataFrame], report: pd.DataFrame, manifest: dict, year: int, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = {**tables, "Validacao": report}
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        _readme(tables, manifest, year).to_excel(xw, sheet_name="LEIA-ME", index=False, header=False)
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
        readme = xw.sheets["LEIA-ME"]
        readme.column_dimensions["A"].width = 30
        readme.column_dimensions["B"].width = 110
        for row in readme.iter_rows():
            for cell in row:
                cell.font = Font(name=FONT, size=10, bold=cell.column == 1)
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        readme["A1"].font = Font(name=FONT, size=14, bold=True)
        for name, df in sheets.items():
            _style(xw.sheets[name], df, table=True)
