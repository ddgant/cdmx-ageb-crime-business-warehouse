"""Run the SQL scripts that build and populate the warehouse, then print the validation checks."""
from config import SQL
from db import get_connection

BUILD_SCRIPTS = ("01_schema.sql", "02_load.sql", "03_views.sql", "05_comments.sql")
VALIDATION_SCRIPT = "04_validation.sql"


def run_file(cx, name: str) -> None:
    with cx.cursor() as cur:
        cur.execute((SQL / name).read_text(encoding="utf-8"))
    cx.commit()
    print(f"[ok] {name}")


def split_statements(sql: str) -> list[str]:
    """Split a script on ';' and drop chunks that only contain comments."""
    out = []
    for chunk in sql.split(";"):
        code = "\n".join(l for l in chunk.splitlines() if not l.strip().startswith("--")).strip()
        if code:
            out.append(code)
    return out


def run_validation(cx) -> bool:
    """Print every result set of the validation script; return True when all checks pass."""
    all_pass = True
    with cx.cursor() as cur:
        for stmt in split_statements((SQL / VALIDATION_SCRIPT).read_text(encoding="utf-8")):
            cur.execute(stmt)
            cols = [d[0] for d in cur.description]
            print("\n" + " | ".join(cols))
            for row in cur.fetchall():
                print(" | ".join(str(v) for v in row))
                if "pass" in cols and row[cols.index("pass")] is not True:
                    all_pass = False
    return all_pass


def main() -> None:
    cx = get_connection()
    for script in BUILD_SCRIPTS:
        run_file(cx, script)
    ok = run_validation(cx)
    cx.close()
    if not ok:
        raise SystemExit("Validation failed: see the table above.")


if __name__ == "__main__":
    main()
