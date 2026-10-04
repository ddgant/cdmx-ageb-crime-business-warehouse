"""Crime grouping and time parsing helpers (pure functions, unit tested).

The FGJ CDMX 'categoria_delito' field puts ~86% of incidents in one bucket
('DELITO DE BAJO IMPACTO'), so the ETL builds its own analytical groups from
the specific offense name ('delito').
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

NON_CRIME_CATEGORY = "HECHO NO DELICTIVO"   # FGJ category for events that are not offenses
OTHER = "Other offenses"

# Ordered rules: the first match wins. They run on the accent-free upper-case offense name.
RULES: list[tuple[str, str]] = [
    ("Homicide", r"HOMICIDIO|FEMINICIDIO"),
    ("Sexual offenses", r"ABUSO SEXUAL|ACOSO SEXUAL|VIOLACION|INTIMIDAD SEXUAL|ESTUPRO|HOSTIGAMIENTO SEXUAL|CORRUPCION DE MENORES|PORNOGRAFIA"),
    ("Family violence", r"VIOLENCIA FAMILIAR|OBLIGACION ALIMENTARIA"),
    ("Kidnapping and liberty", r"SECUESTRO|PRIVACION DE LA LIBERTAD|RETENCION DE MENORES|SUSTRACCION DE MENORES"),
    ("Robbery", r"^ROBO"),
    ("Injuries and threats", r"^LESIONES|AMENAZAS"),
    ("Property damage", r"^DANO"),
    ("Fraud and extortion", r"FRAUDE|ABUSO DE CONFIANZA|USURPACION|FALSIFICACION|EXTORSION|COBRANZA ILEGITIMA|DESPOJO|TITULOS AL PORTADOR|DOCUMENTOS DE CREDITO"),
    ("Drug offenses", r"NARCOMENUDEO|CONTRA LA SALUD"),
]
_COMPILED = [(name, re.compile(pat)) for name, pat in RULES]


def normalize(text: str) -> str:
    """Upper-case, strip accents and collapse whitespace."""
    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", ascii_text).strip().upper()


def crime_group(offense: str) -> str:
    """Map a specific offense name to one of the analytical crime groups."""
    name = normalize(offense)
    for group, pattern in _COMPILED:
        if pattern.search(name):
            return group
    return OTHER


def parse_hour(values: pd.Series) -> pd.Series:
    """Extract the hour (0-23) from strings like 'HH:MM:SS' or 'HH:MM:SS:SS'.

    The source mixes both formats; anything that is not a valid hour becomes <NA>.
    """
    hour = pd.to_numeric(values.str.extract(r"^(\d{1,2}):")[0], errors="coerce")
    return hour.where((hour >= 0) & (hour <= 23)).astype("Int16")
