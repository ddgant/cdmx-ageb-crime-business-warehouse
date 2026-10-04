"""Unpack the original INEGI downloads into data/raw/ with the layout expected by config.py.

Put the original zip files in data/raw/downloads/ and run:  python src/00_unpack_raw.py
Expected zips (names may carry a prefix, matching is by suffix):
  resageburb_09csv20.zip   -> data/raw/census/
  2020_1_09_AGEB.zip                             -> data/raw/mg2020/ageb_urbano/
  2020_1_09_AGEE.zip                                    -> data/raw/mg2020/agee/
  denue_09_1124_csv.zip (DENUE 11/2024)                 -> data/raw/denue/ed1124/
  carpetasFGJ_acumulado_2025_01.zip (FGJ crime, CDMX)   -> data/raw/crime/
Raw files are only extracted, never modified.
"""
import zipfile
from config import RAW

DL = RAW / "downloads"
TARGETS = {
    "resageburb_09csv20.zip": RAW / "census",
    "2020_1_09_AGEB.zip": RAW / "mg2020" / "ageb_urbano",
    "2020_1_09_AGEE.zip": RAW / "mg2020" / "agee",
    "denue_09_1124_csv.zip": RAW / "denue" / "ed1124",
    "carpetasFGJ_acumulado_2025_01.zip": RAW / "crime",
}


def find(name: str):
    hits = list(DL.rglob(f"*{name}"))
    return hits[0] if hits else None


def main():
    for name, dest in TARGETS.items():
        z = find(name)
        if z is None:
            print(f"[missing] {name} not found under {DL}")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(dest)
        print(f"[ok] {z.name} -> {dest}")


if __name__ == "__main__":
    main()
