"""Exportação: tabelas analíticas -> JSON compacto consumido pelo painel (dashboard/index.html).

O painel calcula tudo no navegador (classificações por intervalo de rodadas, estatísticas,
pit stops...), então o JSON leva só os fatos mínimos: cadastros + uma linha por piloto por corrida.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# GP (nome na fonte) -> (código de 3 letras, nome em português). Fora do mapa, cai no automático.
GP_LABELS = {
    "Australian Grand Prix": ("AUS", "Austrália"), "Chinese Grand Prix": ("CHN", "China"),
    "Japanese Grand Prix": ("JPN", "Japão"), "Miami Grand Prix": ("MIA", "Miami"),
    "Canadian Grand Prix": ("CAN", "Canadá"), "Monaco Grand Prix": ("MON", "Mônaco"),
    "Barcelona-Catalunya Grand Prix": ("BCN", "Barcelona-Catalunha"), "Austrian Grand Prix": ("AUT", "Áustria"),
    "British Grand Prix": ("GBR", "Grã-Bretanha"), "Belgian Grand Prix": ("BEL", "Bélgica"),
    "Hungarian Grand Prix": ("HUN", "Hungria"), "Dutch Grand Prix": ("NED", "Holanda"),
    "Italian Grand Prix": ("ITA", "Itália"), "Spanish Grand Prix": ("MAD", "Espanha (Madri)"),
    "Azerbaijan Grand Prix": ("AZE", "Azerbaijão"), "Bahrain Grand Prix": ("BHR", "Bahrein (Sepang)"),
    "Singapore Grand Prix": ("SGP", "Singapura"), "United States Grand Prix": ("USA", "Estados Unidos"),
    "Mexican Grand Prix": ("MEX", "México"), "São Paulo Grand Prix": ("BRA", "São Paulo"),
    "Las Vegas Grand Prix": ("LAS", "Las Vegas"), "Qatar Grand Prix": ("QAT", "Catar"),
    "Abu Dhabi Grand Prix": ("ABU", "Abu Dhabi"),
}
RED_FLAG_SECONDS = 600  # paradas acima disso são corrida interrompida, não pit stop


def _gp_label(gp: str) -> tuple[str, str]:
    if gp in GP_LABELS:
        return GP_LABELS[gp]
    short = gp.replace(" Grand Prix", "")
    return short[:3].upper(), short


def _clean(v):
    return None if pd.isna(v) else v


def build_dashboard_data(tables: dict[str, pd.DataFrame], manifest: dict, year: int) -> dict:
    rc, rs = tables["Resultados_Corrida"], tables["Resultados_Sprint"]
    cal, pil, eq = tables["Calendario"], tables["Pilotos"], tables["Equipes"]
    quali, vr, pit = tables["Qualificacao"], tables["Voltas_Rapidas"], tables["Pit_Stops"]

    team_idx = {tid: i for i, tid in enumerate(eq["Equipe_ID"])}
    racing = pil[pil["Papel"] == "Piloto de corrida"].reset_index(drop=True)
    drv_idx = {did: i for i, did in enumerate(racing["Piloto_ID"])}

    teams = [{"id": r.Equipe_ID, "name": r.Nome, "engine": _clean(r.Motor_Fabricante)} for r in eq.itertuples()]
    drivers = []
    for r in racing.itertuples():
        used = rc[rc["Piloto_ID"] == r.Piloto_ID]["Equipe_ID"].value_counts()
        drivers.append({"id": r.Piloto_ID, "name": r.Nome, "full": r.Nome_Completo, "abbr": r.Sigla,
                        "num": None if pd.isna(r.Numero) else int(r.Numero), "nat": _clean(r.Nacionalidade),
                        "teams": [team_idx[t] for t in used.index]})

    rounds = []
    for r in cal.itertuples():
        code, pt = _gp_label(r.GP)
        rounds.append({"r": int(r.Rodada), "date": r.Data.strftime("%Y-%m-%d"), "code": code, "name": pt, "gp": r.GP,
                       "circuit": _clean(r.Circuito), "city": _clean(r.Cidade), "laps": _clean(r.Voltas),
                       "sprint": r.Fim_de_Semana_Sprint == "Sim", "done": r.Status == "Concluída"})
        if rounds[-1]["laps"] is not None:
            rounds[-1]["laps"] = int(rounds[-1]["laps"])

    pole = set(zip(*quali[(quali["Sessao"] == "Qualificação") & (quali["Posicao"] == 1)][["Rodada", "Piloto_ID"]].T.values))
    fl = set(zip(*vr[vr["Ranking"] == 1][["Rodada", "Piloto_ID"]].T.values))
    sprint = {(r.Rodada, r.Piloto_ID): (int(r.Pontos), None if pd.isna(r.Posicao) else int(r.Posicao))
              for r in rs.itertuples()}
    matched = set()

    results = []
    for r in rc.sort_values(["Rodada", "Posicao", "Piloto_ID"], na_position="last").itertuples():
        key = (r.Rodada, r.Piloto_ID)
        sp = sprint.get(key)
        matched.add(key) if sp else None
        grid = None if pd.isna(r.Grid) or r.Grid == 0 else int(r.Grid)
        pos = None if pd.isna(r.Posicao) else int(r.Posicao)
        if r.Situacao == "Classificado":
            info = _clean(r.Tempo) if pos == 1 else _clean(r.Gap)
        else:
            info = _clean(r.Motivo_Abandono)
        results.append([int(r.Rodada), drv_idx[r.Piloto_ID], team_idx[r.Equipe_ID], grid, pos, r.Situacao,
                        int(r.Pontos), sp[0] if sp else 0, sp[1] if sp else None,
                        int(key in pole), int(key in fl), info])
    missing = set(sprint) - matched
    if missing:
        raise ValueError(f"Sprints sem linha de corrida correspondente: {sorted(missing)}")

    stops = pit[pit["Tempo_s"].notna()]
    long_stops = stops[stops["Tempo_s"] >= RED_FLAG_SECONDS]
    stops = stops[stops["Tempo_s"] < RED_FLAG_SECONDS]
    pits = [[int(r.Rodada), drv_idx[r.Piloto_ID], team_idx[r.Equipe_ID], int(r.Volta), round(float(r.Tempo_s), 3)]
            for r in stops.itertuples() if r.Piloto_ID in drv_idx]

    return {
        "meta": {"year": year, "release": manifest["release"], "commit": manifest["commit"][:7],
                 "commitDate": manifest["commit_date"], "source": manifest["source"], "license": manifest["license"],
                 "lastRound": int(rc["Rodada"].max()), "totalRounds": len(rounds),
                 "pitExcluded": int(len(long_stops)),
                 "pitExcludedRounds": sorted({int(x) for x in long_stops["Rodada"]}),
                 "pitExcludedLaps": sorted({int(x) for x in long_stops["Volta"]}),
                 "pitExcludedMinutes": int(round(long_stops["Tempo_s"].min() / 60)) if len(long_stops) else 0},
        "teams": teams, "drivers": drivers, "rounds": rounds,
        "resultCols": ["round", "driver", "team", "grid", "pos", "status", "ptsRace", "ptsSprint", "sprintPos",
                       "pole", "fl", "info"],
        "results": results,
        "pitCols": ["round", "driver", "team", "lap", "time"],
        "pits": pits,
    }


def write_dashboard_data(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
