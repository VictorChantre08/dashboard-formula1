#!/usr/bin/env python3
"""Executa o pipeline completo: extract -> transform -> validate -> load.

Exemplos:
    python run_pipeline.py                       # baixa/atualiza o F1DB e gera tudo
    python run_pipeline.py --skip-extract        # reaproveita data/raw/f1db já baixado
    python run_pipeline.py --year 2025
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from f1pipeline import export, extract, load, transform, validate  # noqa: E402
from f1pipeline.config import DASHBOARD_DIR, DEFAULT_YEAR, OUTPUT_DIR, PROCESSED_DIR, RAW_DIR  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="temporada (padrão: %(default)s)")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help="onde fica o clone do F1DB")
    parser.add_argument("--skip-extract", action="store_true", help="não baixa/atualiza o F1DB")
    args = parser.parse_args(argv)

    print("1/4 Extração")
    manifest = extract.read_manifest(args.raw_dir) if args.skip_extract else extract.sync_f1db(args.raw_dir)
    print(f"    F1DB {manifest['release']} (commit {manifest['commit'][:7]}, {manifest['commit_date']})")

    print("2/4 Transformação")
    tables = transform.build_tables(args.raw_dir, args.year)
    for name, df in tables.items():
        print(f"    {name:<28}{len(df):>6} linhas")

    print("3/4 Validação")
    report = validate.run_checks(tables)
    print(report[["Verificacao", "Valor", "Resultado"]].to_string(index=False))

    print("4/4 Carga")
    load.write_csvs(tables, PROCESSED_DIR)
    load.write_manifest(manifest, tables, PROCESSED_DIR)
    xlsx = OUTPUT_DIR / f"F1_{args.year}_base_de_dados.xlsx"
    load.write_excel(tables, report, manifest, args.year, xlsx)
    print(f"    CSVs em {PROCESSED_DIR} | Excel em {xlsx}")
    export.write_dashboard_data(export.build_dashboard_data(tables, manifest, args.year),
                                DASHBOARD_DIR / "data.json")
    print(f"    Dados do painel em {DASHBOARD_DIR / 'data.json'}")

    if not validate.all_ok(report):
        print("ATENÇÃO: há validações com status VERIFICAR.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
