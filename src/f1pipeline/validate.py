"""Validações de qualidade: o pipeline só é considerado bem-sucedido se os dados fecham."""
from __future__ import annotations

import pandas as pd


def run_checks(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rc, rs = tables["Resultados_Corrida"], tables["Resultados_Sprint"]
    cal, pil, eq = tables["Calendario"], tables["Pilotos"], tables["Equipes"]
    cp, cc = tables["Classif_Pilotos"], tables["Classif_Construtores"]
    rows: list[dict] = []

    def check(name: str, value, ok: bool, description: str) -> None:
        rows.append({"Verificacao": name, "Valor": value, "Resultado": "OK" if ok else "VERIFICAR",
                     "Descricao": description})

    done = int((cal["Status"] == "Concluída").sum())
    last_round = int(rc["Rodada"].max())
    check("Rodadas concluídas", done, last_round == done,
          "Rodadas com status Concluída = última rodada com resultado de corrida.")

    pts_pil_off, pts_pil_calc = int(cp["Pontos"].sum()), int(pil["Pontos_Calculados"].sum())
    check("Pontos de pilotos (oficial)", pts_pil_off, pts_pil_off == pts_pil_calc,
          f"Deve ser igual aos pontos calculados de corridas + sprints ({pts_pil_calc}).")
    pts_con_off, pts_con_calc = int(cc["Pontos"].sum()), int(eq["Pontos_Calculados"].sum())
    check("Pontos de construtores (oficial)", pts_con_off, pts_con_off == pts_con_calc,
          f"Deve ser igual aos pontos calculados por equipe ({pts_con_calc}).")
    check("Pontos pilotos x construtores", pts_pil_off - pts_con_off, pts_pil_off == pts_con_off,
          "Os dois campeonatos devem somar o mesmo total.")
    check("Pilotos com diferença de pontos", int((pil["Diferenca"] != 0).sum()), (pil["Diferenca"] == 0).all(),
          "Total oficial do piloto difere do calculado.")
    check("Equipes com diferença de pontos", int((eq["Diferenca"] != 0).sum()), (eq["Diferenca"] == 0).all(),
          "Total oficial da equipe difere do calculado.")
    check("Vitórias contadas", int(pil["Vitorias"].sum()), int(pil["Vitorias"].sum()) == done,
          "Uma vitória por corrida concluída.")
    dup = int(rc.duplicated(["Rodada", "Piloto_ID"]).sum())
    check("Duplicatas em Resultados_Corrida", dup, dup == 0, "Chave (Rodada, Piloto_ID) deve ser única.")
    check("Sprints com resultado", int(rs["Rodada"].nunique()),
          int(rs["Rodada"].nunique()) == int((cal["Fim_de_Semana_Sprint"].eq("Sim") & cal["Status"].eq("Concluída")).sum()),
          "Todo fim de semana de sprint concluído tem resultado de sprint.")
    unnamed = int(rc["Piloto"].isna().sum() + rc["Equipe"].isna().sum())
    check("IDs sem nome em Resultados_Corrida", unnamed, unnamed == 0, "Todo piloto/equipe deve ter nome no cadastro.")
    return pd.DataFrame(rows)


def all_ok(report: pd.DataFrame) -> bool:
    return bool((report["Resultado"] == "OK").all())
