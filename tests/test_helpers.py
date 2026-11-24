import pandas as pd

from f1pipeline.transform import split_position, to_points, to_seconds
from f1pipeline.yamlio import read_yaml


def test_to_seconds_handles_all_time_formats():
    s = pd.Series(["1:27:39.624", "1:34.684", "27.768", None, ""])
    out = to_seconds(s)
    assert out.iloc[0] == 5259.624
    assert out.iloc[1] == 94.684
    assert out.iloc[2] == 27.768
    assert out.iloc[3] is pd.NA and out.iloc[4] is pd.NA


def test_split_position_separates_number_and_status():
    num, status = split_position(pd.Series([1, "DNF", 3, "NC"], dtype="object"))
    assert num.tolist() == [1, pd.NA, 3, pd.NA]
    assert status.tolist() == ["Classificado", "DNF", "Classificado", "NC"]


def test_to_points_missing_becomes_zero():
    assert to_points(pd.Series([25, None, 18])).tolist() == [25, 0, 18]


def test_yaml_clock_times_stay_strings(tmp_path):
    f = tmp_path / "race.yml"
    f.write_text("time: 14:00\nlaps: 58\n", encoding="utf-8")
    data = read_yaml(f)
    assert data["time"] == "14:00"  # PyYAML puro devolveria 840
    assert data["laps"] == 58
