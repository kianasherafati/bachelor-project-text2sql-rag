"""SELECT-only gold validation. Persists metadata, never result rows or secrets.

Run from the project root with .venv/Scripts/python.exe -B
evaluation/validate_text2sql_gold.py. Use --check-only for offline definition checks.
The output files must not already exist; validation never overwrites a prior run.
Reference SELECTs are fetched at most 10 rows deep, then cancelled. Full-result
counts and data-wide null profiles are deliberately not computed.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pprint
import re
import runpy
import sys
import time

import pyodbc
from dotenv import dotenv_values

from gold_sql_definitions import definitions


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "retrieval" / "erp_retrieval_heldout_benchmark.py"
GOLD = ROOT / "evaluation" / "text2sql_gold_benchmark.py"
EVIDENCE = ROOT / "evaluation" / "text2sql_gold_validation.json"
SAMPLE_LIMIT = 10


def safe_error(error):
    """Never render driver messages, connection strings, or configuration values."""
    state = error.args[0] if error.args else None
    detail = " ".join(str(arg) for arg in error.args)
    return {
        "type": type(error).__name__,
        "sqlstate": state if isinstance(state, str) and re.fullmatch(r"[A-Z0-9]{5}", state) else None,
        "native_codes": [int(code) for code in re.findall(r"\((\d+)\)", detail)],
        "security_context_failure": "current security context" in detail.lower(),
    }


def connect_read_only():
    # Use configuration internally only. Do not import extract_schema: it has
    # connection configuration at module scope and is outside this workflow.
    config = dotenv_values(ROOT / "schema_extraction" / ".env")

    def escaped(value):
        return "{" + str(value).replace("}", "}}") + "}"

    for key in ("DB_SERVER", "DB_DATABASE"):
        if not config.get(key):
            raise ValueError("Required database configuration is missing")
    parts = [
        "DRIVER=" + escaped(config.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")),
        "SERVER=" + escaped(config["DB_SERVER"]),
        "DATABASE=" + escaped(config["DB_DATABASE"]),
        "TrustServerCertificate=yes",
        "ApplicationIntent=ReadOnly",
    ]
    auth = config.get("DB_AUTH", "windows")
    if auth == "sql":
        if not config.get("DB_USERNAME") or not config.get("DB_PASSWORD"):
            raise ValueError("Required authentication configuration is missing")
        parts.extend(("UID=" + escaped(config["DB_USERNAME"]), "PWD=" + escaped(config["DB_PASSWORD"])))
    elif auth == "windows":
        parts.append("Trusted_Connection=yes")
    else:
        raise ValueError("Unsupported authentication configuration")
    # ODBC SQL_MODE_READ_ONLY = 1; advisory in addition to the account's permissions.
    connection = pyodbc.connect(
        ";".join(parts), timeout=10, autocommit=True,
        attrs_before={pyodbc.SQL_ATTR_ACCESS_MODE: 1},
    )
    connection.timeout = 120
    return connection


def select(cursor, sql, *parameters):
    statement = sql.strip().removesuffix(";")
    if not re.match(r"^SELECT\b", statement, re.I):
        raise ValueError("Only SELECT is permitted")
    if ";" in statement or re.search(
        r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|EXEC|EXECUTE|INTO|SET|DBCC)\b",
        statement, re.I,
    ):
        raise ValueError("Statement outside SELECT-only scope")
    return cursor.execute(sql, *parameters)


def qualified(name):
    if not re.fullmatch(r"gnd_[A-Za-z0-9_]+\.[A-Za-z0-9_]+", name):
        raise ValueError("Unexpected table identifier")
    return ".".join("[" + part + "]" for part in name.split("."))


def protected_hashes():
    paths = list((ROOT / "retrieval").glob("*.py"))
    paths += list((ROOT / "retrieval").glob("*.index"))
    paths += list((ROOT / "retrieval").glob("*.pkl"))
    paths += list((ROOT / "schema_extraction").glob("*.py"))
    paths += [ROOT / "schema_extraction" / "schema.json", ROOT / "schema_extraction" / "schema_documents.json"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def check_definitions():
    frozen = runpy.run_path(str(BENCHMARK))["tests"]
    if len(frozen) != 20 or Counter(t["difficulty"] for t in frozen) != {"easy": 5, "medium": 7, "hard": 8}:
        raise ValueError("Unexpected frozen benchmark shape")
    if {t["id"] for t in frozen} != set(definitions):
        raise ValueError("Gold IDs differ from frozen benchmark")
    documents = json.loads((ROOT / "schema_extraction" / "schema_documents.json").read_text(encoding="utf-8"))
    indexed = {d["full_name"] for d in documents}
    schema = json.loads((ROOT / "schema_extraction" / "schema.json").read_text(encoding="utf-8"))
    tables = {t["schema"] + "." + t["name"]: t for t in schema["tables"]}
    for case in frozen:
        spec = definitions[case["id"]]
        sql = spec["reference_sql"]
        referenced = {
            s + "." + t for s, t in re.findall(r"(?:FROM|JOIN)\s+\[([^]]+)\]\.\[([^]]+)\]", sql)
        }
        if referenced != set(case["expected_tables"]) or not referenced <= indexed:
            raise ValueError("Reference SQL tables differ from frozen expected tables")
        if re.search(r"\b(TOP|LIMIT|WHERE|DISTINCT|GROUP\s+BY)\b", sql, re.I):
            raise ValueError("Unrequested result restriction or aggregation")
        for path in case["fk_paths"]:
            source, target = path.split(" -> ")
            src_table, src_col = source.rsplit(".", 1)
            dst_table, dst_col = target.rsplit(".", 1)
            matches = [f for f in tables[src_table]["foreign_keys"]
                       if f["columns"] == [src_col]
                       and f["references"]["schema"] + "." + f["references"]["table"] == dst_table
                       and f["references"]["columns"] == [dst_col]]
            if not matches:
                raise ValueError("Frozen FK absent from local schema")
    return frozen, tables


def live_table_metadata(cursor, name):
    select(cursor, """SELECT c.name, ty.name, c.is_nullable, c.max_length, c.precision, c.scale,
    pk.key_ordinal
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
INNER JOIN sys.columns AS c ON c.object_id = t.object_id
INNER JOIN sys.types AS ty ON ty.user_type_id = c.user_type_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id, ic.key_ordinal
    FROM sys.indexes AS i
    INNER JOIN sys.index_columns AS ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
) AS pk ON pk.object_id = c.object_id AND pk.column_id = c.column_id
WHERE s.name + '.' + t.name = ?
ORDER BY c.column_id""", name)
    columns = [{"name": r[0], "type": r[1], "nullable": bool(r[2]), "max_length": r[3],
                "precision": r[4], "scale": r[5], "pk_ordinal": r[6]} for r in cursor.fetchall()]
    return {"columns": columns, "primary_key": [c["name"] for c in sorted(
        [c for c in columns if c["pk_ordinal"] is not None], key=lambda c: c["pk_ordinal"])]}


def live_fk_metadata(cursor, path):
    source, target = path.split(" -> ")
    src_table, src_col = source.rsplit(".", 1)
    dst_table, dst_col = target.rsplit(".", 1)
    select(cursor, """SELECT fk.name, fk.is_disabled, fk.is_not_trusted,
    (SELECT COUNT_BIG(*) FROM sys.foreign_key_columns AS other
     WHERE other.constraint_object_id = fk.object_id) AS column_count
FROM sys.foreign_keys AS fk
INNER JOIN sys.foreign_key_columns AS fc ON fc.constraint_object_id = fk.object_id
INNER JOIN sys.tables AS st ON st.object_id = fc.parent_object_id
INNER JOIN sys.schemas AS ss ON ss.schema_id = st.schema_id
INNER JOIN sys.columns AS sc ON sc.object_id = st.object_id AND sc.column_id = fc.parent_column_id
INNER JOIN sys.tables AS tt ON tt.object_id = fc.referenced_object_id
INNER JOIN sys.schemas AS ts ON ts.schema_id = tt.schema_id
INNER JOIN sys.columns AS tc ON tc.object_id = tt.object_id AND tc.column_id = fc.referenced_column_id
WHERE ss.name + '.' + st.name = ? AND sc.name = ?
  AND ts.name + '.' + tt.name = ? AND tc.name = ?""", src_table, src_col, dst_table, dst_col)
    return [{"constraint": r[0], "disabled": bool(r[1]), "not_trusted": bool(r[2]),
             "column_count": int(r[3])} for r in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    frozen, local_tables = check_definitions()
    print("Offline checks passed: 20 cases, 5/7/8 difficulty, all tables and FK paths verified.", flush=True)
    if args.check_only:
        return
    if GOLD.exists() or EVIDENCE.exists():
        raise FileExistsError("Validation outputs already exist; preserve the prior run")
    before = protected_hashes()
    evidence = {"started_at_utc": datetime.now(timezone.utc).isoformat(),
                "tables": {}, "foreign_keys": {}, "schema_differences": [],
                "protected_file_sha256": before,
                "validation_method": "Execute unchanged SELECTs; fetch at most 10 rows, then cancel. Retain column names, emptiness and sample counts only."}
    connection = connect_read_only()
    try:
        cursor = connection.cursor()
        names = sorted({n for case in frozen for n in case["expected_tables"]})
        for name in names:
            live = live_table_metadata(cursor, name)
            if not live["columns"]:
                raise ValueError("An expected live table is absent or not visible")
            evidence["tables"][name] = live
            local = local_tables[name]
            old_cols = [(c["name"], c["data_type"].lower(), bool(c["nullable"])) for c in local["columns"]]
            new_cols = [(c["name"], c["type"].lower(), c["nullable"]) for c in live["columns"]]
            if old_cols != new_cols or local["primary_key"] != live["primary_key"]:
                evidence["schema_differences"].append(name)
        for path in sorted({p for case in frozen for p in case["fk_paths"]}):
            fks = live_fk_metadata(cursor, path)
            if not fks or not any(f["column_count"] == 1 for f in fks):
                raise ValueError("A frozen FK path is absent from the live schema")
            evidence["foreign_keys"][path] = fks
        print(f"Live metadata verified: {len(names)} tables; {len(evidence['foreign_keys'])} FK paths.", flush=True)
        cases = []
        for source in frozen:
            spec = definitions[source["id"]]
            case = {key: source[key] for key in ("id", "question", "difficulty", "domain", "expected_tables", "fk_paths")}
            case.update(spec)
            case.update({"execution_valid": False, "result_columns": [], "row_count": None,
                         "is_empty": None, "review_reasons": [], "samples_retained": False})
            started = time.monotonic()
            print("Executing " + case["id"] + " ...", flush=True)
            try:
                select(cursor, case["reference_sql"])
                case["result_columns"] = [c[0] for c in cursor.description]
                nulls = [0] * len(cursor.description)
                blank = [0] * len(cursor.description)
                rows = cursor.fetchmany(SAMPLE_LIMIT)
                for row in rows:
                    for i, value in enumerate(row):
                        nulls[i] += value is None
                        blank[i] += isinstance(value, str) and not value.strip()
                count = len(rows)
                # A full batch establishes only a lower bound, even when the
                # actual result happens to contain exactly SAMPLE_LIMIT rows.
                fully_counted = count < SAMPLE_LIMIT
                cursor.cancel()
                cursor.close()
                cursor = connection.cursor()
                case.update(
                    execution_valid=True,
                    row_count=count if fully_counted else "not fully counted",
                    row_count_lower_bound=count,
                    row_count_is_exact=fully_counted,
                    is_empty=count == 0,
                    validation_scope="complete small result" if fully_counted else "execution and first 10 rows only",
                    sample_rows_fetched=count,
                )
                case["sample_null_counts"] = dict(zip(case["result_columns"], nulls))
                case["sample_blank_string_counts"] = dict(zip(case["result_columns"], blank))
                if count == 0:
                    case["review_reasons"].append("Empty result: executable, but this snapshot cannot support meaningful result-based accuracy evaluation.")
                if count:
                    case["sample_entirely_null_or_blank_columns"] = [col for col, n, b in zip(case["result_columns"], nulls, blank) if n + b == count]
                    if case["sample_entirely_null_or_blank_columns"]:
                        case["review_reasons"].append("Some requested columns are NULL or blank throughout the bounded sample; this is not a full-table profile.")
            except pyodbc.Error as error:
                case["execution_error"] = safe_error(error)
                case["review_reasons"].append("Execution or bounded-sample validation failed; inspect metadata before accepting SQL.")
                cursor.close()
                cursor = connection.cursor()
            case["validation_seconds"] = round(time.monotonic() - started, 3)
            case["validated_at_utc"] = datetime.now(timezone.utc).isoformat()
            case["requires_review"] = bool(case["review_reasons"])
            cases.append(case)
            print(json.dumps({k: case[k] for k in ("id", "execution_valid", "result_columns", "row_count", "is_empty", "review_reasons")}), flush=True)
    finally:
        connection.close()
    if before != protected_hashes():
        raise RuntimeError("Protected source or retrieval artifacts changed during validation")
    summary = {
        "question_count": len(cases),
        "executable_count": sum(c["execution_valid"] for c in cases),
        "nonempty_count": sum(c["execution_valid"] and c["is_empty"] is False for c in cases),
        "review_ids": [c["id"] for c in cases if c["requires_review"]],
        "protected_artifacts_unchanged": True,
        "benchmark_sha256": hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_samples_saved": False,
        "comparison_policy": "Unordered multiset: preserve duplicates and NULLs; compare column values, not alias spellings. Empty results need separate treatment.",
        "snapshot_limitation": "Live read-only execution, not a database snapshot. Counts describe the validation run and may change later.",
    }
    evidence["summary"] = summary
    evidence["case_validation"] = cases
    # These are NEW generated evaluation artifacts, never business-row dumps.
    with GOLD.open("x", encoding="utf-8") as output:
        output.write('"""Validated gold SQL; generated by validate_text2sql_gold.py. No database access on import."""\n\n')
        output.write("validation_summary = " + pprint.pformat(summary, sort_dicts=False, width=110) + "\n\n")
        output.write("tests = " + pprint.pformat(cases, sort_dicts=False, width=110) + "\n")
    with EVIDENCE.open("x", encoding="utf-8") as output:
        json.dump(evidence, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print("SUMMARY " + json.dumps(summary), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Validation stopped: " + json.dumps(safe_error(error)), file=sys.stderr)
        sys.exit(1)
