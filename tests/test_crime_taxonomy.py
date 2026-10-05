import pandas as pd
import pytest

from crime_taxonomy import OTHER, crime_group, normalize, parse_hour


@pytest.mark.parametrize("offense,expected", [
    ("ROBO A TRANSEUNTE EN VIA PUBLICA CON VIOLENCIA", "Robbery"),
    ("ROBO DE MOTOCICLETA SIN VIOLENCIA", "Robbery"),
    ("VIOLENCIA FAMILIAR", "Family violence"),
    ("HOMICIDIO POR ARMA DE FUEGO", "Homicide"),
    ("FEMINICIDIO", "Homicide"),
    ("LESIONES INTENCIONALES POR GOLPES", "Injuries and threats"),
    ("AMENAZAS", "Injuries and threats"),
    ("FRAUDE", "Fraud and extortion"),
    ("USURPACIÓN DE IDENTIDAD", "Fraud and extortion"),
    ("ABUSO SEXUAL", "Sexual offenses"),
    ("VIOLACION EQUIPARADA", "Sexual offenses"),
    ("DAÑO EN PROPIEDAD AJENA INTENCIONAL A AUTOMOVIL", "Property damage"),
    ("NARCOMENUDEO POSESION SIMPLE", "Drug offenses"),
    ("SECUESTRO", "Kidnapping and liberty"),
    ("DISCRIMINACION", OTHER),
])
def test_crime_group(offense, expected):
    assert crime_group(offense) == expected


def test_normalize_strips_accents_and_spaces():
    assert normalize("  Daño   en  propiedad ") == "DANO EN PROPIEDAD"


def test_robbery_rule_does_not_catch_words_that_only_contain_robo():
    # anchored at the start, so offenses like 'ENCUBRIMIENTO DE ROBO' are not robbery
    assert crime_group("ENCUBRIMIENTO DE ROBO") == OTHER


def test_parse_hour_handles_both_formats_and_invalid_values():
    s = pd.Series(["16:30:00", "06:30:00:00", "23:59:59", "24:00:00", "bad", None])
    out = parse_hour(s)
    assert out.tolist()[:3] == [16, 6, 23]
    assert out.isna().tolist() == [False, False, False, True, True, True]
