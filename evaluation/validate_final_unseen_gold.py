"""Bounded read-only validation for the proposed final unseen Gold SQL."""
import argparse
from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import hashlib
import sqlglot
from sqlglot import exp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from validate_text2sql_gold import connect_read_only, safe_error
from final_unseen_gold_benchmark import FINAL_UNSEEN_GOLD_CASES

OUTPUT = ROOT / "evaluation" / "final_unseen_gold_validation.json"
SAMPLE_LIMIT = 10

PARAMETERS = {
    "FINAL-U04": {"ReportDate": date(2025, 1, 1)},
    "FINAL-U05": {"MinAnnualSalesOrderNumber": 0},
    "FINAL-U08": {"FromDate": date(2000, 1, 1), "ThroughDate": date(2100, 1, 1)},
    "FINAL-U10": {},
    "FINAL-U12": {"AsOfDate": date(2026, 9, 23)},
    "FINAL-U15": {"StartDate": date(2000, 1, 1)},
    "FINAL-U17": {"RoutineID": 0},
    "FINAL-U45": {"InterweavingID": 0, "FromDate": date(2000, 1, 1), "ThroughDate": date(2100, 1, 1)},
    "FINAL-U18": {"FromDate": date(2000, 1, 1), "ThroughDate": date(2100, 1, 1)},
    "FINAL-U20": {"DetailFormTypeID": 0, "DetailFormID": 0},
    "FINAL-U33": {"ReportDate": date(2026, 9, 24)},
    "FINAL-U37": {"AsOfDate": date(2026, 9, 23)},
    "FINAL-U38": {"EvaluationID": 0},
    "FINAL-U40": {},
    "FINAL-U41": {"AsOfDate": date(2026, 9, 23)},
    "FINAL-U49": {"FromDate": date(2000, 1, 1), "ThroughDate": date(2100, 1, 1)},
}

SELECTORS = {
    "FINAL-U38": "SELECT TOP (1) m.ID AS EvaluationID FROM gnd_hrapr.tblManagerHRFeedback m JOIN gnd_egbse.tblYearMonth f ON f.ID=m.FromYearMonthID JOIN gnd_egbse.tblYearMonth t ON t.ID=m.ToYearMonthID WHERE (SELECT COUNT(*) FROM gnd_egbse.tblYearMonth y WHERE y.MonthID IS NOT NULL AND y.FromDate BETWEEN f.FromDate AND t.FromDate)=3 ORDER BY m.ID",
    "FINAL-U10": "SELECT TOP (1) y.ID AS FromPayrollMonthID,y.ID AS ThroughPayrollMonthID FROM gnd_egbse.tblYearMonth y WHERE y.MonthID IS NOT NULL AND EXISTS(SELECT 1 FROM gnd_hrpyr.tblWorkTime w WHERE w.YearMonthID=y.ID) ORDER BY y.FromDate DESC,y.ID DESC",
    "FINAL-U40": "SELECT TOP (1) y.ID AS FromPayrollMonthID,y.ID AS ThroughPayrollMonthID FROM gnd_egbse.tblYearMonth y WHERE y.MonthID IS NOT NULL AND EXISTS(SELECT 1 FROM gnd_hrpyr.tblWorkTime w WHERE w.YearMonthID=y.ID) ORDER BY y.FromDate DESC,y.ID DESC",
    "FINAL-U31": "SELECT TOP (1) r.ID AS PurchaseRequestID,p.ID AS PeriodSpecID,p.EndDate AS EndDate,x.CreatorCompanyID AS CompanyID FROM gnd_scpch.tblPurchaseRequest r JOIN gnd_scpch.tblPurchaseRequestDetail d ON d.PurchaseRequestID=r.ID JOIN gnd_scinv.tblEnterDetail ed ON ed.CredbGoodID=d.GoodID JOIN gnd_scinv.tblEnter e ON e.ID=ed.EnterID JOIN gnu_scinv.xblEnter x ON x.ID=e.ID JOIN gnd_fiaci.tblPeriodSpec p ON e.DoneDate BETWEEN p.BeginDate AND p.EndDate WHERE e.Code IS NOT NULL ORDER BY r.ID,ed.IG,p.ID",

    # Deterministic bounded validation date only; Gold retains @ReportDate.
    "FINAL-U33": "SELECT TOP (1) CONVERT(date,CreateDate) AS ReportDate FROM gnd_egwfm.tblWorkEnd WHERE DoneStatusTypeID=1 ORDER BY ID",
    "FINAL-U41": "SELECT TOP (1) ID AS EmployeeID FROM gnd_hrprs.tblEmployee ORDER BY ID",
    "FINAL-U04": "SELECT TOP (1) CONVERT(date,DoneDate) ReportDate FROM gnd_crsls.tblLoading WHERE DoneDate IS NOT NULL ORDER BY ID",
    "FINAL-U17": "SELECT TOP (1) RoutineID FROM gnd_amspt.tblRoutineCovered ORDER BY IG",
    "FINAL-U45": "SELECT TOP (1) p.InterWeavingID AS InterweavingID FROM gnd_scprd.tblPacking p INNER JOIN gnd_pjprj.evInterweaving i ON i.ID=p.InterWeavingID WHERE p.Serial IS NOT NULL ORDER BY p.ID",
    "FINAL-U20": "SELECT TOP (1) FormTypeID DetailFormTypeID,FormID DetailFormID FROM gnd_fiaci.tblTransDetailDetail ORDER BY IG",
}


def bind(sql, values):
    parameters = []
    def replace(match):
        name = match.group(1)
        if name not in values:
            raise ValueError(f"Missing validation parameter: {name}")
        parameters.append(values[name])
        return "?"
    return re.sub(r"@([A-Za-z][A-Za-z0-9_]*)", replace, sql), parameters


def check_sql(sql):
    text = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.S).strip()
    if not re.match(r"^(?:WITH\b|SELECT\b)", text, re.I):
        raise ValueError("Gold SQL must begin with SELECT or WITH")
    if re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|DBCC|INTO|OPENROWSET|OPENQUERY|OPENDATASOURCE)\b", text, re.I):
        raise ValueError("Unsafe SQL keyword")
    if text.removesuffix(";").find(";") >= 0:
        raise ValueError("Multiple statements are not allowed")
    statements = sqlglot.parse(sql, read="tsql")
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union)):
        raise ValueError("Exactly one SELECT/CTE query is required")
    if any(isinstance(node, (exp.DDL, exp.DML, exp.Into, exp.Command)) for node in statements[0].walk()):
        raise ValueError("Non-read-only syntax is not allowed")


def expected_tables(sql):
    dependency_path = ROOT / "evaluation" / "final_unseen_dependency_audit.json"
    if dependency_path.exists():
        audit = json.loads(dependency_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(sql.encode()).hexdigest()
        matches = [r for r in audit["records"] if r["reference_sql_sha256"] == digest]
        if not matches:
            raise ValueError("SQL changed: refresh the physical dependency audit before validation")
        sets = {tuple(r["final_expected_tables"]) for r in matches}
        if len(sets) != 1:
            raise ValueError("Conflicting dependency records for identical SQL")
        return list(next(iter(sets)))
    raise ValueError("Physical dependency audit required; FROM/JOIN alone omits computed dependencies")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--retry-case", action="append", default=[])
    args = parser.parse_args()
    prior = None
    if OUTPUT.exists():
        if not args.retry_failed and not args.retry_case:
            raise ValueError("Validation output already exists; refusing overwrite")
        prior = json.loads(OUTPUT.read_text(encoding="utf-8"))
    ids = [case["id"] for case in FINAL_UNSEEN_GOLD_CASES]
    if len(ids) != 50 or len(set(ids)) != 50:
        raise ValueError("Exactly 50 unique cases are required")
    for case in FINAL_UNSEEN_GOLD_CASES:
        check_sql(case["reference_sql"])
    if prior:
        old = {r['id']: r for r in prior['results']}
        for case in FINAL_UNSEEN_GOLD_CASES:
            saved_hash = old.get(case['id'], {}).get('reference_sql_sha256')
            current_hash = hashlib.sha256(case['reference_sql'].encode()).hexdigest()
            if saved_hash and saved_hash != current_hash and case['id'] not in args.retry_case:
                raise ValueError('Changed SQL requires explicit --retry-case: ' + case['id'])

    for case in FINAL_UNSEEN_GOLD_CASES:
        if (case['id'] in args.retry_case or (args.retry_failed and prior and not old[case['id']]['execution_valid'])) and case.get('reference_sql_status')=='NONFINAL_FUNCTION_BASED_CANDIDATE_DO_NOT_USE_FOR_EVALUATION':
            raise ValueError('Nonfinal Gold is halted pending its documented source-branch rule: '+case['id'])

    connection = connect_read_only()
    retry_ids = set(args.retry_case)
    preserved = {r["id"]: r for r in prior["results"]
                 if r["id"] not in retry_ids} if prior else {}
    results = []
    try:
        for case in FINAL_UNSEEN_GOLD_CASES:
            if case["id"] in preserved:
                results.append(preserved[case["id"]])
                continue
            cursor = connection.cursor()
            started = time.perf_counter()
            values = dict(PARAMETERS.get(case["id"], {}))
            try:
                selector = SELECTORS.get(case["id"])
                if selector:
                    cursor.execute(selector)
                    row = cursor.fetchone()
                    if row:
                        values.update(dict(zip([d[0] for d in cursor.description], row)))
                sql, params = bind(case["reference_sql"], values)
                cursor.execute(sql, *params)
                columns = [item[0] for item in cursor.description]
                rows = cursor.fetchmany(SAMPLE_LIMIT)
                results.append({
                    "id": case["id"], "execution_valid": True,
                    "reference_sql_sha256": hashlib.sha256(case['reference_sql'].encode()).hexdigest(),
                    "result_columns": columns, "empty": not bool(rows),
                    "bounded_rows_fetched": len(rows), "fully_counted": False,
                    "expected_tables": expected_tables(case["reference_sql"]),
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                })
                private_path = ROOT / 'evaluation' / 'final_unseen_private' / 'audit_validation_parameters.json'
                private_parameters = json.loads(private_path.read_text()) if private_path.exists() else {}
                private_parameters[case['id']] = values
                private_path.write_text(json.dumps(private_parameters, indent=2, default=str)+'\n')
            except Exception as error:
                results.append({
                    "id": case["id"], "execution_valid": False,
                    "reference_sql_sha256": hashlib.sha256(case["reference_sql"].encode()).hexdigest(),
                    "result_columns": [], "empty": None, "bounded_rows_fetched": 0,
                    "fully_counted": False, "expected_tables": expected_tables(case["reference_sql"]),
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                    "error": safe_error(error),
                })
            finally:
                try:
                    cursor.cancel()
                except Exception:
                    pass
                cursor.close()
    finally:
        connection.close()
    payload = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_limit": SAMPLE_LIMIT,
        "exact_counts_not_computed": True,
        "case_count": len(results),
        "executable_count": sum(r["execution_valid"] for r in results),
        "nonempty_count": sum(r["execution_valid"] and not r["empty"] for r in results),
        "empty_count": sum(r["execution_valid"] and r["empty"] for r in results),
        "failed_count": sum(not r["execution_valid"] for r in results),
        "results": results,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ["case_count", "executable_count", "nonempty_count", "empty_count", "failed_count"]}, indent=2))
    for result in results:
        if not result["execution_valid"]:
            print(result["id"], result["error"])


if __name__ == "__main__":
    main()
