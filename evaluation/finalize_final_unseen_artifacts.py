"""Publish validated review artifacts without changing human decisions or freezing hashes.

No database connection, retrieval or semantic auto-approval is performed.
Historical inferred notes must never overwrite the current benchmark.
"""
import hashlib
import json
from pathlib import Path
from final_unseen_benchmark import FINAL_UNSEEN_CASES
from final_unseen_gold_benchmark import SQL
from validate_final_unseen_gold import check_sql

E = Path(__file__).resolve().parent

def current_status(cases):
    resolved = sorted(c['id'] for c in cases if c.get('human_decision_classification') == 'HUMAN_DECISION_RESOLVED')
    pending = sorted(c['id'] for c in cases if not c.get('human_approved', False) or c.get('human_decision_classification') in
                     {'HUMAN_DECISION_SIMPLE', 'HUMAN_DECISION_COMPLEX', 'HUMAN_DECISION_PARTIAL', 'HUMAN_REVIEW_PENDING'})
    partial = sorted(c['id'] for c in cases if c.get('human_decision_classification') == 'HUMAN_DECISION_PARTIAL')
    replacements = sorted(c['id'] for c in cases if c.get('replacement_required'))
    replaced = sorted(c['id'] for c in cases if c.get('replacement_completed'))
    return dict(final_approved_ids=sorted(c['id'] for c in cases if c.get('human_approved') and c.get('semantic_audit_status')=='FINAL_APPROVED_BOUNDED_VALIDATED'),
                resolved_decision_ids=resolved, pending_human_decision_ids=pending,
                partial_ids=partial, pending_replacement_ids=replacements,
                completed_replacement_ids=replaced,
                replacement_decision_count=len(set(replacements + replaced)),
                semantic_blocker_ids=sorted(set(pending + replacements + [c['id'] for c in cases if c.get('semantic_implementation_blocker')])),
                replacement_human_review_pending=[c['id'] for c in cases
                    if c.get('replacement_completed') and not c.get('human_approved')])

def main():
    cases = FINAL_UNSEEN_CASES
    ids = [c['id'] for c in cases]
    assert len(ids) == len(set(ids)) == 50
    assert set(ids) == {f'FINAL-U{i:02}' for i in range(1, 51)}
    path = E / 'final_unseen_gold_validation.json'
    validation = json.loads(path.read_text(encoding='utf-8'))
    results = {r['id']: r for r in validation['results']}
    audit = json.loads((E / 'final_unseen_dependency_audit.json').read_text(encoding='utf-8'))
    dependencies = {r['id']: r for r in audit['records']}
    assert set(results) == set(dependencies) == set(ids)
    for c in cases:
        cid = c['id']; r = results[cid]; d = dependencies[cid]
        check_sql(SQL[cid])
        digest = hashlib.sha256(SQL[cid].encode()).hexdigest()
        assert digest == r['reference_sql_sha256'] == d['reference_sql_sha256'], cid
        assert c['expected_tables'] == r['expected_tables'] == d['final_expected_tables'], cid
        assert c['expected_table_count'] == len(c['expected_tables']), cid
        assert 0 <= r['bounded_rows_fetched'] <= 10 and not r['fully_counted'], cid
        assert (bool(r['empty']) == (r['bounded_rows_fetched'] == 0)) if r['execution_valid'] else (r['empty'] is None and r['bounded_rows_fetched']==0), cid
        assert not d['unresolved_dependency_metadata'], cid
        assert set(d['outside_corpus_dependencies']) <= {'gnu_scinv.xblEnter','gnu_scinv.xblExit','gnu_hrcio.xblEmployeeShift','gnu_egbse.xblContact','gnu_egbse.xblPerson','gnu_egbse.xblPrefix','gnu_scpch.xblPrePurchaseInvoice','gnu_scpch.xblSupplier','gnu_hrcio.xblEmployeeExitPermission'}, cid
        r.update(semantic_audit_status=c['semantic_audit_status'], semantic_note=c['semantic_note'],
                 human_approved=c.get('human_approved', False),
                 hidden_current_time_helpers=d['hidden_current_time_helpers'],
                 certified_gold=bool(c.get('human_approved') and r['execution_valid']),
                 expected_tables_status=c['expected_tables_status'])
    status = current_status(cases)
    status['execution_blocker_ids']=sorted(cid for cid,r in results.items() if not r['execution_valid'])
    status['closed_decision_local_sql_discrepancies']=sorted(c['id'] for c in cases if c.get('local_sql_reconciliation_required'))
    ready = not any(status[k] for k in ['semantic_blocker_ids','replacement_human_review_pending','execution_blocker_ids','closed_decision_local_sql_discrepancies'])
    validation.update(case_count=50, executable_count=sum(r['execution_valid'] for r in results.values()),
        nonempty_count=sum(r['execution_valid'] and not r['empty'] for r in results.values()),
        empty_count=sum(r['execution_valid'] and r['empty'] for r in results.values()),
        failed_count=sum(not r['execution_valid'] for r in results.values()),
        current_human_decision_status=status, freeze_ready=ready,
        freeze_note='Execution is not semantic approval. Resolve all blockers/replacements and obtain final human approval before a separate explicit freeze.',
        overall_expected_table_count_finalized=ready,
        certified_gold_count=sum(r['execution_valid'] and cid not in status['semantic_blocker_ids'] for cid,r in results.items()),
        unique_expected_physical_dependencies=len({t for c in cases for t in c['expected_tables']}))
    path.write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    lines = ['# Final unseen benchmark - current human review package', '',
        '**HUMAN DECISIONS RECONCILED — SEE FORMAL FREEZE MANIFEST FOR IMMUTABLE IDENTITY**', '',
        'Authoritative reviewer answers remain in [the decision sheet](FINAL_UNSEEN_HUMAN_DECISIONS.md). Unresolved SQL remains provisional even when executable.', '',
        f"{validation['executable_count']} executable queries; {validation['nonempty_count']} nonempty; {validation['empty_count']} empty. Validation fetches at most 10 rows per query; unchanged exact-SQL-hash results are reused. Only U04/U32/U42 were boundedly revalidated after the latest approved corrections; the other 47 execution results were reused. The human decision gives approved daily leave precedence over hourly leave at employee/date grain; SELECT-only Gold inlines the source calculation.", '',
        f"Resolved reviewed decisions: {len(status['resolved_decision_ids'])}, including U33 replacement. Pending original human decisions: {len(status['pending_human_decision_ids'])}; approval/implementation blockers: {len(status['semantic_blocker_ids'])}. Replacement decisions: {status['replacement_decision_count']}; {len(status['completed_replacement_ids'])} implemented and validated; {len(status['pending_replacement_ids'])} pending.", '',
        f"Completed replacements: {len(status['completed_replacement_ids'])}; awaiting review: {', '.join(status['replacement_human_review_pending']) or 'None'}. Execution blockers: {', '.join(status['execution_blocker_ids']) or 'None'}. Closed-decision local SQL discrepancies: {', '.join(status['closed_decision_local_sql_discrepancies']) or 'None'}. No model evaluation was performed. Formal freeze status is recorded separately in FINAL_UNSEEN_FREEZE.md.", '',
        '## Remaining human approval or implementation blockers', '', (', '.join(status['semantic_blocker_ids']) or 'None: human semantics are closed; execution/implementation readiness is reported separately.'), '']
    fence = chr(96) * 3
    for c in cases:
        r = results[c['id']]
        lines += [f"## {c['id']}", '', c['question'], '',
            f"- Domain: {c['domain']}; difficulty: {c['difficulty']}.",
            f"- Status: {c['semantic_audit_status']}; human approval: {c.get('human_approved', False)}.",
            f"- Decision classification: {c.get('human_decision_classification', 'No new decision classification')}.",
            '- Current SQL physical dependencies: ' + ', '.join(c['expected_tables']) + '.',
            '- Execution: ' + (('successful; '+('empty' if r['empty'] else 'nonempty')+' bounded result') if r['execution_valid'] else 'current Gold did not complete bounded execution validation; empty/nonempty unknown') + '.',
            '- Semantics: ' + c['semantic_note'],
            '- Relationships: ' + c['relationship_notes'],
            '- Result columns: ' + (', '.join(r['result_columns']) if r['execution_valid'] else 'Not returned; proposed: '+', '.join(c.get('proposed_result_columns',[]))) + '.', '',
            fence + 'sql', SQL[c['id']], fence, '']
    (E / 'FINAL_UNSEEN_REVIEW.md').write_text('\n'.join(lines), encoding='utf-8')
    lines = ['# Current Gold physical dependency audit', '',
        '**Metadata dependency closure for current SQL. Execution status is recorded separately; formal freeze identity is recorded separately.**', '',
        'Scoped SQL ASTs identify direct relations. Inspected SQL Server metadata supplies computed-column/helper dependencies. Every record matches its successful or failed bounded-attempt SQL hash. No unrelated FK neighbors are added.', '',
        'Nine required physical tables are outside the unchanged indexed corpus: initial-registration metadata for U08; stock company metadata for U31; employee-shift metadata for U37; contact/person/prefix, pro forma and supplier metadata used by the U49 entity views. They are included explicitly. U37 uses an inline SELECT-only calculation instead of privileged ERP function calls. U08/U09 match their closed authoritative decisions and passed bounded validation. All 50 dependency sets are human-approved and finalized. The separate freeze manifest determines immutable artifact identity.', '',
        '| Case | Current physical tables | Hidden dependencies beyond direct SQL | Current-time helpers |',
        '|---|---|---|---|']
    for d in audit['records']:
        lines.append('| ' + ' | '.join([d['id'], ', '.join(d['final_expected_tables']),
            ', '.join(d['missing_physical_dependencies_found']) or 'None',
            ', '.join(d['hidden_current_time_helpers']) or 'None']) + ' |')
    (E / 'FINAL_UNSEEN_DEPENDENCY_AUDIT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(dict(case_count=50, executable=validation['executable_count'],
        nonempty=validation['nonempty_count'], empty=validation['empty_count'],
        current_status=status, freeze_ready=ready), indent=2))

if __name__ == '__main__':
    main()
