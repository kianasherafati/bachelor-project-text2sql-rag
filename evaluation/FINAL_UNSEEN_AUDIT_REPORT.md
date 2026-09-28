> Historical stage report — superseded by [current pre-freeze reconciliation](FINAL_UNSEEN_RECONCILIATION.md). Its earlier counts and pending decisions are not current. There are now eight implemented replacements, including U38/U49; their new wording awaits review.

> Historical pre-decision audit. Its pending counts and findings are superseded by [current reconciliation](FINAL_UNSEEN_RECONCILIATION.md); retained for audit history.

# Current stage: HUMAN DECISION PACKAGE READY — BENCHMARK NOT YET FROZEN

The audit below is retained as historical evidence. Its 36-stop classification and 93/95 table counts are superseded by the [human decision sheet](FINAL_UNSEEN_HUMAN_DECISIONS.md) and [per-query dependency audit](FINAL_UNSEEN_DEPENDENCY_AUDIT.md). U46/U50 have since been corrected and revalidated. Current triage: 7 simple decisions, 22 complex decisions, 5 replacement requirements, 2 automatically resolved defects. Overall expected-table count remains unfinalized.

---

# Final unseen semantic and Gold-SQL audit

**SEMANTIC AUDIT COMPLETE — PENDING FINAL HUMAN APPROVAL**

This means the audit findings are complete, including explicit evidence stops. **The benchmark is not ready for evaluation.** Executable queries are not necessarily valid reference answers. No human approval or final-approved freeze was created.

## Summary

- Detailed targeted cases: 19. Additional flagged cases: 22. All 50 received a source-fidelity record and structural scan.
- Targeted verdicts: GOLD_SQL_FIX: 1, INSUFFICIENT_EVIDENCE_STOP: 15, QUESTION_AND_GOLD_FIX: 3.
- Targeted plus additional verdicts: GOLD_SQL_FIX: 1, INSUFFICIENT_EVIDENCE_STOP: 36, QUESTION_AND_GOLD_FIX: 4.
- Remaining lightweight-scan cases approved as-is for the audited scope: FINAL-U01, FINAL-U02, FINAL-U13, FINAL-U19, FINAL-U20, FINAL-U23, FINAL-U28, FINAL-U30, FINAL-U47. Human approval remains pending.
- Gold corrected and bounded revalidated: FINAL-U04, FINAL-U06, FINAL-U32, FINAL-U41, FINAL-U42.
- Questions corrected: FINAL-U06, FINAL-U32, FINAL-U41, FINAL-U42.
- Expected-table sets changed as a consequence of corrected SQL: FINAL-U06, FINAL-U32, FINAL-U42.
- Annotation-only/question-only verdicts: none. Replacements: none. No sampling order was consumed.
- Execution: **50/50**, **42 nonempty**, **8 empty**, **0 execution failures**. Only the five changed queries were re-executed in this audit; other execution evidence was preserved and bound to exact SQL hashes.
- Declared expected tables: **93**, all indexed. Known computed dependencies increase the union to **at least 95**; dependency closure is not final. The stopped U05/U50 sets were not silently changed independently of a validated Gold correction.

## Targeted decisions

| Case | Verdict | Question changed | Gold changed | Tables changed | Execution | Concern / rationale |
|---|---|---|---|---|---|---|
| FINAL-U04 | GOLD_SQL_FIX | no | yes | no | Executable; nonempty; bounded <=10 | The exact source weight caption maps to CargoTotalNetWeight. Return that stored text unchanged, preserving NULL; remove the unsupported decimal computed-weight fallback. |
| FINAL-U05 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | HasShipped is nullable, has no default, and actual NULL values exist. Neither source nor inspected metadata defines NULL as unshipped. DeliveryDate also hides a dependency on SalesOrderWasteDetail. Need the dispatch-report NULL rule and dependency closure before approval. |
| FINAL-U06 | QUESTION_AND_GOLD_FIX | yes | yes | yes | Executable; nonempty; bounded <=10 | Source-linked report definition proves invoice -> separated receipt (FormTypeID 1513618) -> warehouse receipt (27887). Invoice.FormID alone is not a receipt ID. Preserve the report grain: invoice goods line alongside each linked receipt, not an asserted receipt-detail allocation. |
| FINAL-U08 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source explicitly requires approval/rejection and elapsed time TO APPROVAL. RunStatusType describes workflow progress, not approval outcome. Latest Work.CreateDate to LastPlaceChangeDate does not prove an approval interval. Need outcome/event mapping, process-instance grain and start/end rule. |
| FINAL-U11 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Actual duplicate EmployeeFood employee/date rows exist; only IG is unique. fnGetEmployeeFoodCount sums ACTIVE FoodCount over YearMonth. Current Gold includes inactive rows, reports daily rather than monthly, and repeats delivery/request totals for duplicates. Need confirmation that FoodCount is credit and the debit/consumption rule; summing or selecting a latest row without that rule would be an assumption. |
| FINAL-U17 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | WorkOrder has target, suggested, minimum and maximum dates and source-form fields. Source describes scheduling context in an unavailable attachment. The anti-join tests whether ANY order ever existed for equipment/routine, not whether the scheduled instance was generated. Need the intended schedule period/instance mapping. |
| FINAL-U18 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Request details and payments are independent children. No direct request-line/payment FK was found; PaymentDetail links only to Payment. Present data has no request with multiple children on BOTH sides, but schema permits it. Source filters completed payments by payment date; Gold filters request date and emits all statuses. Need intended row grain and completion definition. |
| FINAL-U26 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Feedback.ID -> WorkOrder.ID is an explicit FK and is valid. WorkRoute existence alone does not identify a Continue action, success, or relevant transition. Need workflow action/state semantics for the continuation flag; keep the verified FK, do not certify the flag. |
| FINAL-U29 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source response explicitly rejects fixed hierarchy levels because accounts may be defined at arbitrary depths. MotherID confirms ancestry only. AccountDetail.FormTypeID identifies permitted analytic TYPES, not actual analytic entities. Need role/depth metadata and intended analytic level; current labels are not justified. |
| FINAL-U31 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source asks for an item ledger, not movements since the request. Gold drops opening history, so RunningBalance is only net movement since the request. GoodID is a valid item filter, not proof of request fulfillment; optional warehouse/date matching has no source support. Need stock/opening/period and transaction inclusion policy before correcting the balance. |
| FINAL-U32 | QUESTION_AND_GOLD_FIX | yes | yes | yes | Executable; nonempty; bounded <=10 | The source resolution names the same invoice/receipt report as U06. Supplier comes from PurchaseInvoice.CredbSupplierID -> Supplier -> Person -> Contact identity inheritance, not Enter.RelatedPerson. Use invoice date/quantity/amount explicitly and the proven receipt header chain. |
| FINAL-U34 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Work permits parallel tasks and actual multiple active rows per form exist. WorkRoute is related history; choosing the latest form row would discard parallel tasks. Current predicates do not test waiting for a circulation response. Need the response/parallel-work lifecycle rule, not merely a latest-row filter. |
| FINAL-U38 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source genuinely says predominant, not latest. Latest EmployeeShift is therefore not a valid substitute. Inspected shift-work functions calculate interval coverage with different status filters and do not establish a dominant-shift/tie rule; one function has inconsistent comments and predicates. Need the production rule for dominance and attribution of count. |
| FINAL-U39 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Actual multiple Contract matches per WorkTime/month exist, so SUM duplicates values. fnLastActiveContractBaseDate uses a single date, Code=99 and non-leavers, not the monthly report rule. It cannot justify a month-end or latest-contract policy here. Need the approved-position attribution rule for monthly totals. |
| FINAL-U40 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Gold applies arbitrary-day overlap to complete monthly totals and also multiplies them through overlapping contracts. Source requests personnel-group reporting, not that overlap policy. Need month selection, personnel-group meaning, and effective group attribution; no invented partial-month allocation. |
| FINAL-U41 | QUESTION_AND_GOLD_FIX | yes | yes | no | Executable; empty; bounded <=10 | Source explicitly requires the current month. Replace server clock with @AsOfDate and freeze the validation date; select an existing employee privately rather than invalid sentinel 0. Daily values repeat per attendance event intentionally and are not aggregated. |
| FINAL-U45 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Packing.DoneDate is SQL date; no day truncation is necessary. However the source report is SENSOR production, whereas Gold sums packing weights. Source-linked report definition was not available. Need sensor-report lineage and metric before accepting this substitution. |
| FINAL-U48 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Ranking all rows before testing completion correctly differs from selecting latest active. Existing fnPurchaseInquiry_LastStepName selects latest ID and a process-step label, not necessarily a person; Gold uses CreateDate then ID. Parallel workflow/role assignment can exist. Need current approval-person semantics, completion and ordering policy. The old note is demonstrably inaccurate. |
| FINAL-U49 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | Actual overlapping EmployeeShift rows exist; no employee/date uniqueness constraint prevents fanout. Holiday dates lack a unique constraint even though no duplicates were found. Weekday arithmetic correctly maps Thursday=3 and Friday=4 after the Monday anchor, but source does not define holiday-over-weekday precedence. LeaveHours omits daily-leave conversion; Unit-as-hall and Department-as-subgroup also need evidence. Need attribution, holiday precedence, subgroup and duration conversion rules. |

## Additional issues from the 50-case scan

| Case | Verdict | Question changed | Gold changed | Tables changed | Execution | Concern / rationale |
|---|---|---|---|---|---|---|
| FINAL-U03 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source stage filtering is absent; purchasing-queue and remaining quantities were introduced as a substitute without proof. |
| FINAL-U07 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | Empty additional-off-date table explains the result but does not prove it represents ALL off days requested by the source. |
| FINAL-U09 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | LAG over modification records may not give the prior effective shift and does not cover all changed attributes requested by the source. |
| FINAL-U10 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | Normalization drops off-day counts, attendance time bands and required workdays; non-work duration is not automatically an absence count. |
| FINAL-U12 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Gold displays stored loan ceilings beside a balance; source asks for a ceiling based on current balance. Recalculation/current-balance semantics need evidence. |
| FINAL-U14 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | A packaging-weight total does not by itself reconcile inventory incoming quantity with net production. |
| FINAL-U15 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Specified material categories were removed rather than parameterized; header-only source linkage may miss alternative invoice paths. |
| FINAL-U16 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | No NULL responsible employee is a data-state result, but team assignment and recurring scheduling requirements were not preserved. |
| FINAL-U21 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Project grouping is preserved only for invoices; source purchases may include other document types. Scope needs confirmation. |
| FINAL-U22 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source process attachment is unavailable; verify all branches and polymorphic links rather than inferring the entire business process from one header chain. |
| FINAL-U24 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Selecting one latest Work per form may discard parallel workflow branches; full lifecycle definition is not established. |
| FINAL-U25 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source uses equipment type OR asset, whereas grouping on both columns requires a rule for mutually populated/null identifiers and consumption-event grain. |
| FINAL-U27 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Source concerns cheque-collection bank analytics. UNION with ALL journal lines lacking ANY analytic is an invented scope and yields unrelated exceptions. |
| FINAL-U33 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | Gold has no web-application predicate. Empty login history does not make the missing application restriction correct. |
| FINAL-U35 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | InternalLetter.Date is date-only, not sending time. Source resolution points to workflow-send history, which Gold never reads. |
| FINAL-U36 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Required legacy code and hour/minute representation were lost. Integer cdur fields cannot be labeled hours without confirming their encoding. |
| FINAL-U37 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Latest closed-month WorkTime.RemainedLeave is not established as current leave at request time; source distinguishes annual and monthly leave. |
| FINAL-U42 | QUESTION_AND_GOLD_FIX | yes | yes | yes | Executable; nonempty; bounded <=10 | Source resolution identifies an existing DISABLED attendance event, not an absent event or approval failure. Include CardLog.IsDisable=1 through FormTypeID=1389122/FormID -> ForgottenEnterExit.ID, verified by explicit form metadata. One row per disabled linked event; no invented approval restriction or claim to detect every possible worktime discrepancy. |
| FINAL-U43 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; empty; bounded <=10 | EXISTS effective shift counts all daily rows, not proven qualifying shift-work days. Inspected ERP functions apply status/interval rules not present in Gold. |
| FINAL-U44 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Metadata labels SystemSaatEzafeKarcdur and SystemSaatEzafekarTatilicdur as actual overtime; Gold uses payroll overtime fields and labels them unrounded. Unit conversion still requires evidence. |
| FINAL-U46 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Amount/quantity calculation is plausible, but the source names warehouse amount while Gold uses AccValue; InvValue also exists and the intended amount requires confirmation. |
| FINAL-U50 | INSUFFICIENT_EVIDENCE_STOP | no | no | no | Executable; nonempty; bounded <=10 | Gold reads only goods lines despite complete sales/services scope. Computed VAT hides tblVatPercentage; direct FROM/JOIN extraction is incomplete. Need services and computed dependency closure. |

## Empty-result audit

| Case | Immediate cause | Semantic qualification |
|---|---|---|
| FINAL-U07 | Empty source table | EmployeeShiftAdditionalOffDates has no rows. Employee and payroll-date joins are structurally valid, but additional off dates have not been proved to represent every off day requested. |
| FINAL-U10 | Empty source table | WorkTimeAllDays has no rows, independently of filters/joins. Source omissions and duration/count semantics remain unresolved. |
| FINAL-U16 | No rows meet the explicit filter | WorkOrder is populated, but no row has ResponsibleEmployeeID IS NULL. LEFT master joins cannot remove orders. Team assignment and recurrence meaning remain unresolved. |
| FINAL-U17 | Selected pair excluded by anti-join | The selected scheduled assignment exists; its Equipment/Routine joins succeed; that same pair already has a WorkOrder. The lifetime anti-join explains emptiness, but its schedule-instance semantics are not established. |
| FINAL-U33 | Empty source table | UserLoginHistory has no rows. Application is the candidate discriminator, but no web-application value or enumeration was established; do not invent Application = Web. |
| FINAL-U41 | Empty source table; valid parameters | WorkTimeAllDays has no rows. Existing employee selection and the payroll month containing frozen AsOfDate both exist. Removed the former invalid EmployeeID=0 sentinel. This does not prove all column-unit semantics. |
| FINAL-U43 | Empty source table | WorkTimeAllDays has no rows. EXISTS avoids multiplying rows, but counting daily rows is not proven equivalent to qualifying shift-work entitlement. |
| FINAL-U49 | Empty source table masks unsafe aggregation | WorkTimeAllDays has no rows. Independent checks found overlapping EmployeeShift rows; multiplication would be possible once daily data exists. Holiday and leave conversion rules remain unresolved. |

## Important interpretation limits

- U06/U32 return each invoice goods line alongside each header-linked receipt, following explicit source-report lineage. Invoiced quantity/amount can repeat across receipts; these are not allocated receipt quantities and must not be summed across repeated header associations. Receipt identity uses the separated-receipt path, not Invoice.FormID.
- U04 returns the original stored CargoTotalNetWeight value, which is text. It does not coerce it into another numeric measure or substitute a value when NULL.
- U41 uses a frozen validation AsOfDate of 2026-09-23. The employee validation value is private. One daily-worktime row may repeat for its attendance events; the Gold does not sum those repeated measures.
- U42 now reports the disabled-event exception identified by the source resolution. It does not claim to detect every reason attendance may be absent from calculated worktime.
- U29 fixed business levels remain explicitly REJECTED as a reference interpretation. Its old executable SQL is retained only as a stopped candidate for audit traceability. It must not be evaluated or treated as correct; an arbitrary-tree rewrite would itself need approved source-faithful wording.
- U48 old note was corrected to describe ranking ALL rows before completion filtering. This annotation correction does not certify the unresolved current-approver logic. Earlier non-completed tasks are not automatically resurrected.
- U45 DoneDate already has date granularity, but that does not establish packing weights as the requested sensor-production metric.

## Dependencies and consistency

- All 50 pass static SELECT/CTE safety checks. Negative checks reject SELECT INTO, writes, EXEC, multiple statements and external OPENQUERY access. No model-generated query was executed.
- No GETDATE/CURRENT_TIMESTAMP/SYSDATETIME/GETUTCDATE calls remain in the Gold definitions.
- Direct physical FROM/JOIN sets match benchmark and validation records. This is not complete computed-function lineage:
  - FINAL-U05: missing declared dependency gnd_crsls.tblSalesOrderWasteDetail.
  - FINAL-U50: missing declared dependency gnd_fiaci.tblVatPercentage.
- Dates, fanout and source/Gold scope concerns are recorded above. Holiday weekday arithmetic is correct for the intended modern dates, but precedence and leave-duration conversion remain business-rule holds.

## Required human decisions / evidence

1. Review and approve or reject the five evidence-based corrections, especially invoice-line/receipt grain and the source-resolved disabled-event scope.
2. Supply the specific rule or authoritative report lineage identified in each stopped case above. Do not approve those cases merely because they execute. Unresolved IDs: FINAL-U03, FINAL-U05, FINAL-U07, FINAL-U08, FINAL-U09, FINAL-U10, FINAL-U11, FINAL-U12, FINAL-U14, FINAL-U15, FINAL-U16, FINAL-U17, FINAL-U18, FINAL-U21, FINAL-U22, FINAL-U24, FINAL-U25, FINAL-U26, FINAL-U27, FINAL-U29, FINAL-U31, FINAL-U33, FINAL-U34, FINAL-U35, FINAL-U36, FINAL-U37, FINAL-U38, FINAL-U39, FINAL-U40, FINAL-U43, FINAL-U44, FINAL-U45, FINAL-U46, FINAL-U48, FINAL-U49, FINAL-U50.
3. Decide whether unresolved requirements should be retained after clarification or replaced. Any replacements must follow the frozen domain sampling order; none were manually chosen.
4. Resolve hidden computed dependencies and source-scope losses before certifying final expected tables. Confirm any resulting domain/difficulty reassessment only after the semantics are settled.
5. Review the nine lightweight approvals separately; they were not subjected to the same targeted depth as the flagged cases.

## Privacy and integrity

- Public artifacts contain newly written summaries, case IDs and schema identifiers; no raw ticket text, source ticket IDs, business result rows or credentials were copied into them.
- Detailed source mapping, evidence, validation parameters and per-case fidelity records remain in the Git-ignored private directory.
- 53 baseline-hashed retrieval/schema artifacts remained byte-identical. No retrieval, ranking inspection, reranker, Qwen or generation ran. No commit or push was made.
- Database operations were read-only metadata SELECTs, boolean existence diagnostics and bounded Gold SELECTs. A source-linked stored-procedure definition was read as metadata; the procedure was not executed.

## Files changed by the audit

Public files: `final_unseen_benchmark.py`, `final_unseen_gold_benchmark.py`, `validate_final_unseen_gold.py`, `final_unseen_gold_validation.json`, `FINAL_UNSEEN_REVIEW.md`, and new `FINAL_UNSEEN_AUDIT_REPORT.md` (all under `evaluation/`).

Private files: case-specific `source_fidelity_audit.json`; semantic diagnostic, function/report metadata, empty-case, consistency and validation-parameter evidence; preparation/diagnostic/publication helpers; audit baseline snapshots; freeze-manifest audit revision. Original source snapshot and sampling order were preserved.
