"""Transformação: YAML bruto do F1DB -> tabelas analíticas planas (pandas).

Modelo de saída (nomes das colunas em português, IDs preservados para joins):
  Dimensões : Calendario, Pilotos, Equipes, Equipe_Pilotos
  Fatos     : Resultados_Corrida, Resultados_Sprint, Qualificacao, Grid_Largada,
              Pit_Stops, Voltas_Rapidas, Piloto_do_Dia
  Classif.  : Classif_Pilotos, Classif_Construtores, *_Rodada (evolução do campeonato)
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .yamlio import read_yaml

warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

QUALI = "Qualificação"
SPRINT_QUALI = "Sprint Qualifying"

# nome interno -> arquivo YAML dentro de cada pasta de corrida
SOURCES = {
    "race": "race-results",
    "sprint": "sprint-race-results",
    "quali": "qualifying-results",
    "sprint_quali": "sprint-qualifying-results",
    "grid": "starting-grid-positions",
    "pit": "pit-stops",
    "fastest": "fastest-laps",
    "dotd": "driver-of-the-day-results",
    "drivers_by_round": "driver-standings",
    "constructors_by_round": "constructor-standings",
}


# ------------------------------------------------------------- helpers ----
def col(df: pd.DataFrame, name: str) -> pd.Series:
    """Coluna se existir; senão uma série vazia (NA) com o mesmo índice."""
    if name in df.columns:
        return df[name]
    return pd.Series(pd.NA, index=df.index, dtype="object")


def to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def to_points(s: pd.Series) -> pd.Series:
    pts = pd.to_numeric(s, errors="coerce").fillna(0)
    return pts.astype("int64") if (pts % 1 == 0).all() else pts


def _seconds(value) -> float | None:
    if pd.isna(value) or value == "":
        return None
    try:
        parts = str(value).split(":")
        total = sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))
        return round(total, 3)
    except ValueError:
        return None


def to_seconds(s: pd.Series) -> pd.Series:
    """'1:27:39.624' | '1:34.684' | '27.768' -> segundos (float)."""
    return s.map(_seconds).astype("Float64")


def split_position(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Separa posição numérica de situação (Classificado / DNF / DNS / NC / DSQ...)."""
    num = pd.to_numeric(s, errors="coerce").astype("Int64")
    situacao = s.where(num.isna(), "Classificado").astype("string")
    return num, situacao


def read_dim(raw_dir: Path, kind: str, ids) -> pd.DataFrame:
    """Lê cadastros (drivers, constructors, circuits...) apenas para os IDs usados."""
    wanted = sorted({i for i in ids if isinstance(i, str)})
    rows = []
    for i in wanted:
        row = dict(read_yaml(raw_dir / "src" / "data" / kind / f"{i}.yml") or {})
        row.setdefault("id", i)
        rows.append(row)
    return pd.DataFrame(rows) if rows else pd.DataFrame({"id": []})


def names(raw_dir: Path, kind: str, ids, key: str = "name") -> dict:
    dim = read_dim(raw_dir, kind, ids)
    if key not in dim.columns:
        return {}
    return dict(zip(dim["id"], dim[key]))


def collect(season: Path, filename: str) -> pd.DataFrame:
    """Empilha um arquivo YAML de todas as corridas da temporada, marcando a rodada."""
    frames = []
    for race_dir in sorted(season.glob("races/*/")):
        data = read_yaml(race_dir / f"{filename}.yml")
        if not data:
            continue
        df = pd.DataFrame(data)
        df.insert(0, "round", read_yaml(race_dir / "race.yml")["round"])
        frames.append(df)
    if not frames:
        return pd.DataFrame({"round": pd.Series(dtype="int64")})
    return pd.concat(frames, ignore_index=True)


# ------------------------------------------------------------- lookups ----
@dataclass
class Lookups:
    races: pd.DataFrame
    drivers: pd.DataFrame
    constructors: pd.DataFrame
    driver_names: dict
    constructor_names: dict
    engine_names: dict
    round_gp: dict
    round_date: dict


def build_races(raw_dir: Path, season: Path) -> pd.DataFrame:
    """Calendário enriquecido (GP, circuito, cidade, país) via merges."""
    rows = [read_yaml(d / "race.yml") for d in sorted(season.glob("races/*/"))]
    races = pd.DataFrame(rows).sort_values("round", ignore_index=True)
    gps = read_dim(raw_dir, "grands-prix", races["grandPrixId"])[["id", "fullName"]]
    gps.columns = ["grandPrixId", "GP"]
    circ = read_dim(raw_dir, "circuits", races["circuitId"])
    circ = circ[["id", "fullName", "placeName", "countryId"]]
    circ.columns = ["circuitId", "Circuito", "Cidade", "circuitCountryId"]
    ctry = read_dim(raw_dir, "countries", circ["circuitCountryId"])[["id", "name"]]
    ctry.columns = ["circuitCountryId", "Pais"]
    races = (races.merge(gps, on="grandPrixId", how="left")
                  .merge(circ, on="circuitId", how="left")
                  .merge(ctry, on="circuitCountryId", how="left"))
    races["date"] = pd.to_datetime(races["date"])
    return races


def build_lookups(raw_dir: Path, races: pd.DataFrame, frames: dict, entrants: pd.DataFrame,
                  final_d: pd.DataFrame, final_c: pd.DataFrame, entrant_drivers: pd.DataFrame) -> Lookups:
    driver_ids, constructor_ids, engine_ids = set(), set(), set()
    for df in frames.values():
        driver_ids |= set(col(df, "driverId").dropna())
        constructor_ids |= set(col(df, "constructorId").dropna())
        engine_ids |= set(col(df, "engineManufacturerId").dropna())
    driver_ids |= set(entrant_drivers["driverId"].dropna()) | set(col(final_d, "driverId").dropna())
    constructor_ids |= set(entrants["constructorId"].dropna()) | set(col(final_c, "constructorId").dropna())
    drivers = read_dim(raw_dir, "drivers", driver_ids)
    constructors = read_dim(raw_dir, "constructors", constructor_ids)
    return Lookups(
        races=races, drivers=drivers, constructors=constructors,
        driver_names=dict(zip(drivers["id"], drivers["name"])),
        constructor_names=dict(zip(constructors["id"], constructors["name"])),
        engine_names=names(raw_dir, "engine-manufacturers", engine_ids),
        round_gp=dict(zip(races["round"], races["GP"])),
        round_date=dict(zip(races["round"], races["date"])),
    )


def decorate(df: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    """Adiciona GP, Data, nomes de piloto/equipe e padroniza as colunas-chave."""
    out = df.copy()
    for c in ("driverId", "driverNumber", "constructorId"):
        if c not in out.columns:
            out[c] = pd.NA
    out = out.rename(columns={"round": "Rodada", "driverId": "Piloto_ID",
                              "driverNumber": "Numero", "constructorId": "Equipe_ID"})
    if "Rodada" not in out.columns:  # classificação final da temporada não tem rodada
        out["Rodada"] = pd.NA
    out["Numero"] = to_int(out["Numero"])
    out["GP"] = out["Rodada"].map(lk.round_gp)
    out["Data"] = pd.to_datetime(out["Rodada"].map(lk.round_date))
    out["Piloto"] = out["Piloto_ID"].map(lk.driver_names)
    out["Equipe"] = out["Equipe_ID"].map(lk.constructor_names)
    return out


# ------------------------------------------------------------- fatos ----
def build_results(df: pd.DataFrame, lk: Lookups, *, with_engine: bool) -> pd.DataFrame:
    out = decorate(df, lk)
    out["Posicao"], out["Situacao"] = split_position(col(df, "position"))
    out["Grid"] = to_int(col(df, "gridPosition"))
    out["Pontos"] = to_points(col(df, "points"))
    out["Motor"] = col(df, "engineManufacturerId").map(lk.engine_names)
    out = out.rename(columns={"laps": "Voltas", "time": "Tempo", "timePenalty": "Penalidade_Tempo",
                              "gap": "Gap", "interval": "Intervalo", "reasonRetired": "Motivo_Abandono"})
    cols = ["Rodada", "GP", "Data", "Piloto_ID", "Piloto", "Numero", "Equipe_ID", "Equipe"]
    cols += ["Motor"] if with_engine else []
    cols += ["Grid", "Posicao", "Situacao", "Voltas", "Tempo", "Penalidade_Tempo", "Gap",
             "Intervalo", "Motivo_Abandono", "Pontos"]
    return out.reindex(columns=cols)


def build_quali(quali: pd.DataFrame, sprint_quali: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    frames = []
    for df, label in ((quali, QUALI), (sprint_quali, SPRINT_QUALI)):
        if df.empty:
            continue
        out = decorate(df, lk)
        out["Sessao"] = label
        out["Posicao"], out["Situacao"] = split_position(col(df, "position"))
        for q in ("q1", "q2", "q3"):
            out[q.upper()] = col(df, q)
            out[f"{q.upper()}_s"] = to_seconds(col(df, q))
        frames.append(out.rename(columns={"gap": "Gap", "laps": "Voltas"}))
    cols = ["Rodada", "GP", "Data", "Sessao", "Piloto_ID", "Piloto", "Numero", "Equipe_ID", "Equipe",
            "Posicao", "Situacao", "Q1", "Q2", "Q3", "Q1_s", "Q2_s", "Q3_s", "Gap", "Voltas"]
    if not frames:
        return pd.DataFrame(columns=cols)
    out = pd.concat(frames, ignore_index=True).sort_values("Rodada", kind="stable", ignore_index=True)
    return out.reindex(columns=cols)


def build_grid(df: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    out = decorate(df, lk)
    out["Posicao_Grid"] = to_int(col(df, "position"))
    out = out.rename(columns={"gridPenalty": "Penalidade_Grid", "time": "Tempo_Qualificacao"})
    return out.reindex(columns=["Rodada", "GP", "Data", "Piloto_ID", "Piloto", "Equipe_ID", "Equipe",
                                "Posicao_Grid", "Penalidade_Grid", "Tempo_Qualificacao"])


def build_pit_stops(df: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    out = decorate(df, lk)
    out["Tempo_s"] = to_seconds(col(df, "time"))
    out = out.rename(columns={"position": "Ranking_Parada", "stop": "Parada", "lap": "Volta", "time": "Tempo"})
    return out.reindex(columns=["Rodada", "GP", "Data", "Piloto_ID", "Piloto", "Numero", "Equipe_ID", "Equipe",
                                "Ranking_Parada", "Parada", "Volta", "Tempo", "Tempo_s"])


def build_fastest_laps(df: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    out = decorate(df, lk)
    out["Tempo_s"] = to_seconds(col(df, "time"))
    out = out.rename(columns={"position": "Ranking", "lap": "Volta", "time": "Tempo", "gap": "Gap"})
    return out.reindex(columns=["Rodada", "GP", "Data", "Piloto_ID", "Piloto", "Numero", "Equipe_ID", "Equipe",
                                "Ranking", "Volta", "Tempo", "Tempo_s", "Gap"])


def build_driver_of_the_day(df: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    out = decorate(df, lk).rename(columns={"position": "Ranking", "percentage": "Percentual_Votos"})
    return out.reindex(columns=["Rodada", "GP", "Data", "Piloto_ID", "Piloto", "Equipe_ID", "Equipe",
                                "Ranking", "Percentual_Votos"])


# ------------------------------------------------------ classificações ----
def build_standings(df: pd.DataFrame, lk: Lookups, *, kind: str, by_round: bool) -> pd.DataFrame:
    """kind: 'driver' | 'constructor'."""
    out = decorate(df, lk).rename(columns={"position": "Posicao", "points": "Pontos"})
    ident = ["Piloto_ID", "Piloto"] if kind == "driver" else ["Equipe_ID", "Equipe"]
    head = ["Rodada", "GP", "Data"] if by_round else []
    return out.reindex(columns=head + (ident if by_round else ["Posicao"] + ident) +
                       (["Posicao", "Pontos"] if by_round else ["Pontos"]))


# --------------------------------------------------------- dimensões ----
def flatten_entrants(entrants: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (equipe inscrita, piloto), usando explode + json_normalize."""
    exploded = entrants[["constructorId", "drivers"]].explode("drivers", ignore_index=True)
    drivers = pd.json_normalize(exploded["drivers"].tolist()).reindex(
        columns=["driverId", "rounds", "testDriver"])
    return pd.concat([exploded[["constructorId"]], drivers], axis=1)


def build_team_drivers(ed: pd.DataFrame, lk: Lookups) -> pd.DataFrame:
    out = pd.DataFrame({
        "Equipe_ID": ed["constructorId"],
        "Equipe": ed["constructorId"].map(lk.constructor_names),
        "Piloto_ID": ed["driverId"],
        "Piloto": ed["driverId"].map(lk.driver_names),
        "Rodadas": ed["rounds"].map(lambda v: "" if pd.isna(v) else str(v)),
        "Piloto_de_Testes": ed["testDriver"].eq(True).map({True: "Sim", False: "Não"}),
    })
    return out


def _count(df: pd.DataFrame, key: str, mask: pd.Series) -> pd.Series:
    return df[mask.fillna(False).astype(bool)].groupby(key).size()


def _metrics(base: pd.DataFrame, key: str, rc: pd.DataFrame, rs: pd.DataFrame, q: pd.DataFrame,
             extra: dict[str, pd.Series]) -> pd.DataFrame:
    """Métricas por piloto/equipe (key = Piloto_ID | Equipe_ID)."""
    ids = base[key]
    pole = q[q["Sessao"].eq(QUALI)]
    series = {
        "Pontos_Corridas": rc.groupby(key)["Pontos"].sum(),
        "Pontos_Sprints": rs.groupby(key)["Pontos"].sum(),
        "Vitorias": _count(rc, key, rc["Posicao"].eq(1)),
        "Podios": _count(rc, key, rc["Posicao"].le(3)),
        "Poles": _count(pole, key, pole["Posicao"].eq(1)),
        "Abandonos": _count(rc, key, rc["Situacao"].eq("DNF")),
        **extra,
    }
    for name, s in series.items():
        base[name] = ids.map(s).fillna(0).astype("int64")
    return base


def build_drivers(raw_dir: Path, lk: Lookups, tables: dict, final_d: pd.DataFrame, ed: pd.DataFrame) -> pd.DataFrame:
    rc, rs, q, vr = (tables[k] for k in ("Resultados_Corrida", "Resultados_Sprint", "Qualificacao", "Voltas_Rapidas"))
    d = lk.drivers.reindex(columns=["id", "name", "fullName", "abbreviation", "permanentNumber",
                                    "nationalityCountryId", "countryOfBirthCountryId", "placeOfBirth",
                                    "dateOfBirth"]).copy()
    countries = read_dim(raw_dir, "countries", set(d["nationalityCountryId"]) | set(d["countryOfBirthCountryId"]))
    d["Nacionalidade"] = d["nationalityCountryId"].map(dict(zip(countries["id"], countries["demonym"])))
    d["Pais_Nascimento"] = d["countryOfBirthCountryId"].map(dict(zip(countries["id"], countries["name"])))
    d = d.rename(columns={"id": "Piloto_ID", "name": "Nome", "fullName": "Nome_Completo", "abbreviation": "Sigla",
                          "permanentNumber": "Numero", "placeOfBirth": "Cidade_Nascimento",
                          "dateOfBirth": "Data_Nascimento"})
    d["Data_Nascimento"] = pd.to_datetime(d["Data_Nascimento"])

    # equipe(s) em 2026: só as equipes em que o piloto correu; reservas ficam com a equipe de origem
    ed = ed.assign(Equipe=ed["constructorId"].map(lk.constructor_names))

    def teams(g: pd.DataFrame) -> str:
        racing = g[g["rounds"].notna()]
        return "; ".join(dict.fromkeys((racing if len(racing) else g)["Equipe"]))

    d["Equipe_2026"] = d["Piloto_ID"].map(ed.groupby("driverId")[["rounds", "Equipe"]].apply(teams))
    d["Papel"] = d["Piloto_ID"].isin(set(rc["Piloto_ID"])).map(
        {True: "Piloto de corrida", False: "Piloto de testes/reserva"})

    official = final_d.set_index("driverId")
    d["Posicao_Campeonato"] = to_int(d["Piloto_ID"].map(official["position"]))
    d["Pontos_Oficiais"] = d["Piloto_ID"].map(official["points"]).fillna(0).astype("int64")
    extra = {"GPs_Disputados": _count(rc, "Piloto_ID", rc["Situacao"].ne("DNS")),
             "Voltas_Mais_Rapidas": _count(vr, "Piloto_ID", vr["Ranking"].eq(1))}
    d = _metrics(d, "Piloto_ID", rc, rs, q, extra)
    d["Pontos_Calculados"] = d["Pontos_Corridas"] + d["Pontos_Sprints"]
    d["Diferenca"] = d["Pontos_Oficiais"] - d["Pontos_Calculados"]
    d = d.sort_values(["Posicao_Campeonato", "Nome"], na_position="last", ignore_index=True)
    return d.reindex(columns=["Piloto_ID", "Nome", "Nome_Completo", "Sigla", "Numero", "Nacionalidade",
                              "Pais_Nascimento", "Cidade_Nascimento", "Data_Nascimento", "Equipe_2026", "Papel",
                              "Posicao_Campeonato", "Pontos_Oficiais", "Pontos_Corridas", "Pontos_Sprints",
                              "Pontos_Calculados", "Diferenca", "GPs_Disputados", "Vitorias", "Podios", "Poles",
                              "Voltas_Mais_Rapidas", "Abandonos"])


def build_constructors(raw_dir: Path, lk: Lookups, tables: dict, final_c: pd.DataFrame,
                       entrants: pd.DataFrame) -> pd.DataFrame:
    rc, rs, q = (tables[k] for k in ("Resultados_Corrida", "Resultados_Sprint", "Qualificacao"))
    c = lk.constructors.reindex(columns=["id", "name", "fullName", "countryId"]).copy()
    countries = names(raw_dir, "countries", c["countryId"])
    c["Pais"] = c["countryId"].map(countries)
    c = c.rename(columns={"id": "Equipe_ID", "name": "Nome", "fullName": "Nome_Completo"})

    e = entrants.copy()
    e["Equipe_Entrante"] = e["entrantId"].map(names(raw_dir, "entrants", e["entrantId"]))
    e["Motor_Fabricante"] = e["engineManufacturerId"].map(names(raw_dir, "engine-manufacturers", e["engineManufacturerId"]))
    e["Chassi"] = e["chassisId"].map(names(raw_dir, "chassis", e["chassisId"]))
    e["Unidade_de_Potencia"] = e["engineId"].map(names(raw_dir, "engines", e["engineId"]))
    e["Pneus"] = e["tyreManufacturerId"].map(names(raw_dir, "tyre-manufacturers", e["tyreManufacturerId"]))
    join = lambda s: "; ".join(dict.fromkeys(s.dropna()))  # noqa: E731
    for name in ("Equipe_Entrante", "Motor_Fabricante", "Chassi", "Unidade_de_Potencia", "Pneus"):
        c[name] = c["Equipe_ID"].map(e.groupby("constructorId")[name].agg(join))

    official = final_c.set_index("constructorId")
    c["Posicao_Campeonato"] = to_int(c["Equipe_ID"].map(official["position"]))
    c["Pontos_Oficiais"] = c["Equipe_ID"].map(official["points"]).fillna(0).astype("int64")
    c = _metrics(c, "Equipe_ID", rc, rs, q, {})
    c["Pontos_Calculados"] = c["Pontos_Corridas"] + c["Pontos_Sprints"]
    c["Diferenca"] = c["Pontos_Oficiais"] - c["Pontos_Calculados"]
    c = c.sort_values(["Posicao_Campeonato", "Nome"], na_position="last", ignore_index=True)
    return c.reindex(columns=["Equipe_ID", "Nome", "Nome_Completo", "Pais", "Equipe_Entrante", "Motor_Fabricante",
                              "Chassi", "Unidade_de_Potencia", "Pneus", "Posicao_Campeonato", "Pontos_Oficiais",
                              "Pontos_Corridas", "Pontos_Sprints", "Pontos_Calculados", "Diferenca", "Vitorias",
                              "Podios", "Poles", "Abandonos"])


def build_calendar(lk: Lookups, tables: dict) -> pd.DataFrame:
    rc, q, vr, rs = (tables[k] for k in ("Resultados_Corrida", "Qualificacao", "Voltas_Rapidas", "Resultados_Sprint"))
    cal = lk.races.copy()
    first = lambda df, mask: df[mask.fillna(False).astype(bool)].set_index("Rodada")["Piloto"]  # noqa: E731
    done = cal["round"].isin(set(rc["Rodada"]))
    sprint = cal["round"].isin(set(rs["Rodada"]))
    if "sprintRaceDate" in cal.columns:
        sprint |= cal["sprintRaceDate"].notna()
    cal["Fim_de_Semana_Sprint"] = sprint.map({True: "Sim", False: "Não"})
    cal["Status"] = done.map({True: "Concluída", False: "Agendada"})
    cal["Vencedor"] = cal["round"].map(first(rc, rc["Posicao"].eq(1))).where(done)
    cal["Pole"] = cal["round"].map(first(q, q["Sessao"].eq(QUALI) & q["Posicao"].eq(1)))
    cal["Volta_Mais_Rapida"] = cal["round"].map(first(vr, vr["Ranking"].eq(1))).where(done)
    cal = cal.rename(columns={"round": "Rodada", "date": "Data", "time": "Hora_UTC", "officialName": "Nome_Oficial",
                              "qualifyingFormat": "Formato_Qualificacao", "laps": "Voltas",
                              "distance": "Distancia_km", "courseLength": "Extensao_km", "turns": "Curvas",
                              "circuitType": "Tipo_Circuito", "direction": "Sentido"})
    return cal.reindex(columns=["Rodada", "Data", "Hora_UTC", "GP", "Nome_Oficial", "Circuito", "Cidade", "Pais",
                                "Formato_Qualificacao", "Fim_de_Semana_Sprint", "Voltas", "Distancia_km",
                                "Extensao_km", "Curvas", "Tipo_Circuito", "Sentido", "Status", "Vencedor", "Pole",
                                "Volta_Mais_Rapida"])


# ------------------------------------------------------------ orquestra ----
def build_tables(raw_dir: Path, year: int) -> dict[str, pd.DataFrame]:
    raw_dir = Path(raw_dir)
    season = raw_dir / "src" / "data" / "seasons" / str(year)
    frames = {name: collect(season, fname) for name, fname in SOURCES.items()}
    entrants = pd.DataFrame(read_yaml(season / "entrants.yml") or [])
    final_d = pd.DataFrame(read_yaml(season / "driver-standings.yml") or [])
    final_c = pd.DataFrame(read_yaml(season / "constructor-standings.yml") or [])
    ed = flatten_entrants(entrants)
    races = build_races(raw_dir, season)
    lk = build_lookups(raw_dir, races, frames, entrants, final_d, final_c, ed)

    t: dict[str, pd.DataFrame] = {}
    t["Resultados_Corrida"] = build_results(frames["race"], lk, with_engine=True)
    t["Resultados_Sprint"] = build_results(frames["sprint"], lk, with_engine=False)
    t["Qualificacao"] = build_quali(frames["quali"], frames["sprint_quali"], lk)
    t["Grid_Largada"] = build_grid(frames["grid"], lk)
    t["Pit_Stops"] = build_pit_stops(frames["pit"], lk)
    t["Voltas_Rapidas"] = build_fastest_laps(frames["fastest"], lk)
    t["Piloto_do_Dia"] = build_driver_of_the_day(frames["dotd"], lk)
    t["Classif_Pilotos"] = build_standings(final_d, lk, kind="driver", by_round=False)
    t["Classif_Construtores"] = build_standings(final_c, lk, kind="constructor", by_round=False)
    t["Classif_Pilotos_Rodada"] = build_standings(frames["drivers_by_round"], lk, kind="driver", by_round=True)
    t["Classif_Construtores_Rodada"] = build_standings(frames["constructors_by_round"], lk, kind="constructor", by_round=True)
    t["Equipe_Pilotos"] = build_team_drivers(ed, lk)
    t["Pilotos"] = build_drivers(raw_dir, lk, t, final_d, ed)
    t["Equipes"] = build_constructors(raw_dir, lk, t, final_c, entrants)
    t["Calendario"] = build_calendar(lk, t)

    order = ["Calendario", "Pilotos", "Equipes", "Equipe_Pilotos", "Resultados_Corrida", "Resultados_Sprint",
             "Qualificacao", "Grid_Largada", "Pit_Stops", "Voltas_Rapidas", "Piloto_do_Dia", "Classif_Pilotos",
             "Classif_Construtores", "Classif_Pilotos_Rodada", "Classif_Construtores_Rodada"]
    return {name: t[name] for name in order}
