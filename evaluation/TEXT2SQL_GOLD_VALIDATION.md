# Held-out gold SQL validation

## Outcome

The 20 approved questions and SQL definitions are preserved. All 20 reference
SELECTs have executed successfully: 16 returned rows and four returned empty results.
H09 now succeeds after the DBA's narrowly scoped read-only access change. Only H09
was rerun; the other 19 validation records were reused unchanged. No cases remain
permission-limited.

All 43 expected tables and 25 declared FK paths were verified against the live
schema in the original validation. No column-name/type/nullability or PK changes
were detected against the local metadata. All 25 FK paths were enabled and trusted.

## Saved execution results

Except for H09, exact counts below were obtained in the initial validation and
reused without recomputation; those counts matched their driving-table counts.
H09 was validated using a bounded ten-row fetch, so its total was not counted.
The Python benchmark contains observed column names and the earlier null profiles.
No business-row samples were saved.

| Case | Executed | Rows | Notes |
|---|---|---:|---|
| H01 | Yes | 506 | Four requested credit/term columns are all NULL. |
| H02 | Yes | 76 | PaymentDelayInMonth is all NULL. |
| H03 | Yes | 6,743 | Volume is all NULL. |
| H04 | Yes | 2 | Non-empty. |
| H05 | Yes | 0 | DailyReport driving table is empty. |
| H06 | Yes | 1,721 | Non-empty. |
| H07 | Yes | 0 | SupplierEvaluation driving table is empty. |
| H08 | Yes | 0 | CounterDetail driving table is empty. |
| H09 | Yes | Not fully counted (at least 10) | Error 916 resolved; ten-row bounded fetch succeeded. |
| H10 | Yes | 12 | Non-empty. |
| H11 | Yes | 12,031 | Non-empty. |
| H12 | Yes | 879 | ConeHardness is a bit flag, returned as stored. |
| H13 | Yes | 591,085 | One row per serial; line quantities repeat across serials. |
| H14 | Yes | 176 | Non-empty. |
| H15 | Yes | 149 | TrialPeriod is returned without assuming units. |
| H16 | Yes | 1,249 | One row per defect entry. |
| H17 | Yes | 7 | DetailDescription is blank in all seven rows, not NULL. |
| H18 | Yes | 0 | EquipmentFailure driving table is empty. |
| H19 | Yes | 445,786 | Non-empty. |
| H20 | Yes | 211 | LEFT JOIN preserves steps without a model-step link. |

H01 all-NULL columns: MaxCashCredit, MaxNonCashCredit, AgreedLedgerReceiveDays,
AgreedChequesDuration. H17 has seven blank strings and zero NULLs in DetailDescription.
Empty or unpopulated outputs are data-coverage limitations, not evidence that the
questions are undefinable or that substitute business logic should be invented.

## H09 diagnosis

The full reference SELECT failed twice in the earlier work with SQLSTATE 08004
and SQL Server native error 916 (database access under the current security
context). The underlying tables are visible and their earlier COUNT_BIG checks
succeeded: 85 required-document records and 10 document types.

The later focused diagnosis confirmed the dependency chain:
HasAttachment -> gnd_hrprs.fnEmployeeRequiredDocumentHasAttachmentCall ->
gnd_hrprs.fnEmployeeRequiredDocumentHasAttachment -> gnd_egbse.tblMedia (synonym)
-> GD4_60_SPN_Media.gnd_egbse.tblMedia. The target database was inaccessible to the
account. Earlier connection timeouts and error details are retained as historical
diagnosis in the validation artifacts.

After the DBA reported granting target-database access and SELECT on ID,
FormTypeID and FormID, the unchanged reference query was rerun successfully at
2026-09-18T16:11:02.129550+00:00. Its returned columns exactly matched:
EmployeeID, DocumentTypeEnglish, DocumentSequence, HasAttachment, PictureName.
Ten rows were fetched, then the result was cancelled and the cursor closed.
The result is non-empty; row_count is "not fully counted" and its lower bound
is 10. execution_valid is now True and the permission-related review flag is cleared.
No permission changes were applied by the validator, and neither the SQL nor the
benchmark question was changed.

## Updated validation policy

Future validation executes each unchanged reference SELECT, fetches at most ten
rows, and cancels/closes the cursor. It does not drain large results or issue
business-table COUNT_BIG queries. A full ten-row batch records row_count as
"not fully counted", row_count_lower_bound=10, and row_count_is_exact=False.
Smaller exhausted results can retain an exact count. Sample NULL/blank profiles
are explicitly sample-scoped and are not called full-table profiles.

Successful bounded validation checks execution, output columns and emptiness;
it does not guarantee that evaluating every later row would succeed. Prior
complete-result observations remain unchanged. The validator refuses to overwrite
existing validation artifacts, preventing accidental reruns of this completed set.

## Use in evaluation

H09 is now an executable gold query under the tested account, validated with a
bounded fetch rather than complete-result consumption.
Report the four empty-result cases separately when evaluating result equivalence;
unrelated queries can otherwise receive credit merely by also returning no rows.
NULL/blank fields likewise provide weak evidence for semantic correctness.
Compare unordered multisets, preserving duplicates and NULLs. These observations
describe a live validation run, not a frozen database snapshot.
