import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

"""Mini-temporada compartilhada pelos testes: 1 corrida, 2 pilotos, 2 equipes."""
FILES = {
    "drivers/ab-one.yml": "id: ab-one\nname: Ana One\nfullName: Ana Maria One\nabbreviation: ONE\npermanentNumber: 1\n"
                          "nationalityCountryId: italy\ncountryOfBirthCountryId: italy\nplaceOfBirth: Roma\ndateOfBirth: 2000-01-02\n",
    "drivers/cd-two.yml": "id: cd-two\nname: Beto Two\nfullName: Beto Two\nabbreviation: TWO\npermanentNumber: 2\n"
                          "nationalityCountryId: italy\ncountryOfBirthCountryId: italy\nplaceOfBirth: Milao\ndateOfBirth: 2001-03-04\n",
    "constructors/alpha.yml": "id: alpha\nname: Alpha\nfullName: Alpha Racing\ncountryId: italy\n",
    "constructors/beta.yml": "id: beta\nname: Beta\nfullName: Beta Racing\ncountryId: italy\n",
    "countries/italy.yml": "id: italy\nname: Italy\ndemonym: Italian\n",
    "grands-prix/testland.yml": "id: testland\nfullName: Testland Grand Prix\n",
    "circuits/test-circuit.yml": "id: test-circuit\nfullName: Test Circuit\nplaceName: Testville\ncountryId: italy\n",
    "engine-manufacturers/motor.yml": "id: motor\nname: Motor\n",
    "entrants/alpha-team.yml": "id: alpha-team\nname: Alpha Team\n",
    "entrants/beta-team.yml": "id: beta-team\nname: Beta Team\n",
    "chassis/chassis-a.yml": "id: chassis-a\nname: A1\n",
    "chassis/chassis-b.yml": "id: chassis-b\nname: B1\n",
    "engines/engine-x.yml": "id: engine-x\nname: X-16\n",
    "tyre-manufacturers/pirelli.yml": "id: pirelli\nname: Pirelli\n",
    "seasons/2026/entrants.yml": (
        "- entrantId: alpha-team\n  constructorId: alpha\n  engineManufacturerId: motor\n  chassisId: chassis-a\n"
        "  engineId: engine-x\n  tyreManufacturerId: pirelli\n  drivers:\n    - driverId: ab-one\n      rounds: 1\n"
        "- entrantId: beta-team\n  constructorId: beta\n  engineManufacturerId: motor\n  chassisId: chassis-b\n"
        "  engineId: engine-x\n  tyreManufacturerId: pirelli\n  drivers:\n    - driverId: cd-two\n      rounds: 1\n"),
    "seasons/2026/driver-standings.yml": "- position: 1\n  driverId: ab-one\n  points: 25\n"
                                         "- position: 2\n  driverId: cd-two\n  points: 0\n",
    "seasons/2026/constructor-standings.yml": "- position: 1\n  constructorId: alpha\n  points: 25\n"
                                              "- position: 2\n  constructorId: beta\n  points: 0\n",
    "seasons/2026/races/01-testland/race.yml": (
        "id: 1\nround: 1\ndate: 2026-03-08\ntime: 14:00\ngrandPrixId: testland\nofficialName: Test GP 2026\n"
        "qualifyingFormat: KNOCKOUT\ncircuitId: test-circuit\ncircuitType: RACE\ndirection: CLOCKWISE\n"
        "courseLength: 5.0\nturns: 10\nlaps: 50\ndistance: 250.0\n"),
    "seasons/2026/races/01-testland/race-results.yml": (
        "- position: 1\n  driverNumber: 1\n  driverId: ab-one\n  constructorId: alpha\n  engineManufacturerId: motor\n"
        "  laps: 50\n  time: \"1:20:00.000\"\n  points: 25\n  gridPosition: 1\n"
        "- position: DNF\n  driverNumber: 2\n  driverId: cd-two\n  constructorId: beta\n  engineManufacturerId: motor\n"
        "  laps: 10\n  reasonRetired: Engine\n  points:\n  gridPosition: 2\n"),
    "seasons/2026/races/01-testland/qualifying-results.yml": (
        "- position: 1\n  driverNumber: 1\n  driverId: ab-one\n  constructorId: alpha\n  q1: \"1:30.000\"\n"
        "  q2: \"1:29.500\"\n  q3: \"1:29.000\"\n  laps: 12\n"
        "- position: 2\n  driverNumber: 2\n  driverId: cd-two\n  constructorId: beta\n  q1: \"1:30.500\"\n"
        "  q2: \"1:30.000\"\n  q3: \"1:29.800\"\n  laps: 12\n"),
    "seasons/2026/races/01-testland/driver-standings.yml": "- position: 1\n  driverId: ab-one\n  points: 25\n"
                                                          "- position: 2\n  driverId: cd-two\n  points: 0\n",
    "seasons/2026/races/01-testland/constructor-standings.yml": "- position: 1\n  constructorId: alpha\n  points: 25\n"
                                                               "- position: 2\n  constructorId: beta\n  points: 0\n",
    "seasons/2026/races/01-testland/pit-stops.yml": (
        "- position: 1\n  driverNumber: 1\n  driverId: ab-one\n  constructorId: alpha\n  engineManufacturerId: motor\n"
        "  tyreManufacturerId: pirelli\n  stop: 1\n  lap: 20\n  time: \"22.500\"\n"
        "- position: 2\n  driverNumber: 2\n  driverId: cd-two\n  constructorId: beta\n  engineManufacturerId: motor\n"
        "  tyreManufacturerId: pirelli\n  stop: 1\n  lap: 3\n  time: \"30:46.248\"\n"),
    "seasons/2026/races/01-testland/fastest-laps.yml": (
        "- position: 1\n  driverNumber: 1\n  driverId: ab-one\n  constructorId: alpha\n  engineManufacturerId: motor\n"
        "  tyreManufacturerId: pirelli\n  lap: 30\n  time: \"1:28.000\"\n"),
}


@pytest.fixture()
def raw_dir(tmp_path: Path) -> Path:
    for rel, text in FILES.items():
        path = tmp_path / "src" / "data" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path
