"""Read-only historical-registry gate and private source snapshot.

No retrieval, model, benchmark-result, or SQL-generation imports.
Raw support text is stored only in the Git-ignored private directory.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pyodbc
from dotenv import dotenv_values
from minimize_final_unseen_source import minimize

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'evaluation' / 'final_unseen_private'
REGISTRY = PRIVATE / 'exclusion_registry.json'
SUPPORT_DATABASE = 'GD4_07_001_GreenGALEX_Central'


def historical_gate():
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    records = registry['tickets']
    ids = {row['ticket_id'] for row in records}
    if len(ids) != 105 or len(records) != 105:
        raise ValueError('Historical 105-ticket registry is incomplete')
    if sum(row['belongs_to_13_observed_requirements'] for row in records) != 13:
        raise ValueError('Observed requirement provenance is incomplete')
    if not all(row['directly_inspected'] for row in records):
        raise ValueError('Historical inspection evidence is incomplete')
    return registry, ids


def connect_support_read_only():
    config = dotenv_values(ROOT / 'schema_extraction' / '.env')
    required = ['SUPPORT_DB_SERVER', 'SUPPORT_DB_DATABASE',
                'SUPPORT_DB_USERNAME', 'SUPPORT_DB_PASSWORD']
    if not all(config.get(key) for key in required):
        raise ValueError('Approved support connection configuration is incomplete')
    if config['SUPPORT_DB_DATABASE'] != SUPPORT_DATABASE:
        raise ValueError('Configured support database does not match the approved source')
    escape = lambda value: '{' + str(value).replace('}', '}}') + '}'
    parts = [
        'DRIVER=' + escape(config.get('SUPPORT_DB_DRIVER', 'ODBC Driver 17 for SQL Server')),
        'SERVER=' + escape(config['SUPPORT_DB_SERVER']),
        'DATABASE=' + escape(SUPPORT_DATABASE),
        'UID=' + escape(config['SUPPORT_DB_USERNAME']),
        'PWD=' + escape(config['SUPPORT_DB_PASSWORD']),
        'TrustServerCertificate=yes', 'ApplicationIntent=ReadOnly',
    ]
    return pyodbc.connect(';'.join(parts), timeout=10, autocommit=True,
                          attrs_before={pyodbc.SQL_ATTR_ACCESS_MODE: 1})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inspect-metadata', action='store_true')
    parser.add_argument('--snapshot', action='store_true')
    args = parser.parse_args()
    registry, excluded = historical_gate()
    customer_id = int(registry['customer_id'])
    if not args.inspect_metadata and not args.snapshot:
        raise ValueError('Source extraction requires reviewed metadata; no extraction mode enabled yet')
    with connect_support_read_only() as connection:
        cursor = connection.cursor()
        if args.snapshot:
            output = PRIVATE / 'source_snapshot.json'
            if output.exists():
                raise ValueError('Source snapshot already exists; refusing overwrite')
            cursor.execute('''SELECT ID,RequestDate,Title,Description,SystemName,
FormTypeName,ReportName,SchemaName,Response,IDofFormType,IDofReport
FROM gnd_grsup.tblServiceRequest WHERE RequesterCustomerID=? ORDER BY ID''', customer_id)
            fields = [item[0] for item in cursor.description]
            rows = []
            while True:
                batch = cursor.fetchmany(100)
                if not batch:
                    break
                rows.extend(dict(zip(fields, row)) for row in batch)
            for row in rows:
                for field in ['Title','Description','Response']:
                    row[field] = minimize(row[field])
            cursor.close()
            available = {row['ID'] for row in rows}
            missing = sorted(excluded - available)
            if missing:
                raise ValueError('Historical tickets are missing from the customer-scoped snapshot')
            payload = {
                'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                'source_database': SUPPORT_DATABASE,
                'customer_id': customer_id,
                'exclusion_registry_sha256': hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
                'total_source_tickets': len(rows),
                'historical_exclusions': len(excluded),
                'provisional_untouched_count': len(available - excluded),
                'unseen_status': 'provisional_pending_duplicate_and_followup_review',
                'records': rows,
            }
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
            print(json.dumps({key: value for key, value in payload.items() if key != 'records'}, indent=2))
            return
        cursor.execute("""SELECT c.name, TYPE_NAME(c.user_type_id) AS data_type
FROM sys.columns c
JOIN sys.tables t ON t.object_id=c.object_id
JOIN sys.schemas s ON s.schema_id=t.schema_id
WHERE s.name='gnd_grsup' AND t.name='tblServiceRequest'
ORDER BY c.column_id""")
        columns = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
        cursor.execute("""SELECT COUNT_BIG(*) FROM gnd_grsup.tblServiceRequest
WHERE RequesterCustomerID=?""", customer_id)
        count = int(cursor.fetchone()[0])
        cursor.close()
    print(json.dumps({'historical_exclusions_verified': len(excluded),
                      'total_source_tickets': count, 'column_metadata': columns}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except pyodbc.Error as error:
        # Driver diagnostics may include connection details; do not render them.
        state = error.args[0] if error.args else None
        print(json.dumps({'status': 'blocked', 'error_type': 'database_connection_or_query',
                          'sqlstate': state if isinstance(state, str) and len(state) == 5 else None}))
        raise SystemExit(1)
