> Historical stage report — superseded by [current pre-freeze reconciliation](FINAL_UNSEEN_RECONCILIATION.md). Its earlier counts and pending decisions are not current. There are now eight implemented replacements, including U38/U49; their new wording awaits review.

# Final-unseen deterministic replacement completion

**All six replacements human-approved on 2026-09-27; question and SQL text unchanged. Not frozen.**

Five selections were made in the frozen domain order, with 107 candidates considered and 102 preceding exclusions. Each selected cluster was in the frozen uncontaminated set, had the expected ordering digest, and was absent from the prior selection ledger. No retrieval or model results were used. Domain-order positions below are not source ticket identifiers. Private evidence is retained only in the ignored area.

| Case | Frozen domain positions | Excluded before selection | Selected position | Validation |
|---|---|---:|---:|---|
| FINAL-U14 | production: 12–16 | 4 | 16 | Executable; nonempty; 10 fetched |
| FINAL-U17 | assets/maintenance: 16–25 | 9 | 25 | Executable; nonempty; 1 fetched |
| FINAL-U22 | other/unclear: 109–137 | 28 | 137 | Executable; nonempty; 10 fetched |
| FINAL-U29 | finance/treasury: 26–39 | 13 | 39 | Executable; empty; 0 fetched |
| FINAL-U45 | production: 17–65 | 48 | 65 | Executable; empty; 0 fetched |

## FINAL-U14

For each bobbin-label record, show its yarn-group code and the spinning-system name defined for that yarn group.

- Domain: production; secondary: projects; difficulty: Hard.
- Physical tables: gnd_pjprj.tblInterweaving, gnd_scprd.tblSpindleLable, gnd_spgod.tblSpinningSystemType.
- Result columns: BobbinLabelID, InterweavingID, InterweavingCode, SpinningSystemName.
- Relationships: SpindleLable.InterweavingID -> Interweaving.ID; Interweaving.SpinningSystemTypeID -> SpinningSystemType.ID are explicit FKs.
- Semantic contract: One row per stored bobbin-label record, not per generated printed label. The spinning-system name is its stored Persian display name; no translation or machine-name substitution. UI editability and mandatory-entry changes are outside the extracted reporting need.
- Execution: successful; nonempty, 10 rows fetched, not fully counted.

## FINAL-U17

For @RoutineID, list the recorded overlapping maintenance activities, showing the activity-card name and each covered activity identifier and name.

- Domain: assets/maintenance; secondary: none; difficulty: Medium.
- Physical tables: gnd_amspt.tblRoutine, gnd_amspt.tblRoutineCovered.
- Result columns: RoutineID, RoutineName, CoverageLineID, CoveredRoutineID, CoveredRoutineName.
- Relationships: RoutineCovered.RoutineID -> Routine.ID and RoutineCovered.CoveredRoutineID -> Routine.ID are explicit FKs; Routine is joined twice in different roles.
- Semantic contract: Overlapping means the explicitly stored coverage relation labelled Covered Routine in ERP metadata. It does not mean calculated time overlap or simultaneous/prerequisite routines. One row per coverage-detail IG. @RoutineID replaces source-specific activity identifiers.
- Execution: successful; nonempty, 1 rows fetched, not fully counted.

## FINAL-U22

For each user with a recorded chat visit, show the latest recorded visit date and time.

- Domain: other/unclear; secondary: none; difficulty: Easy.
- Physical tables: gnd_egbse.tblChatLastSeen.
- Result columns: UserID, LastSeenAt.
- Relationships: Single-table aggregation by UserID; no user-profile or message-content join is required.
- Semantic contract: UserID identifies the user without outputting a username or personal name. MAX(LastSeenDate) gives the latest stored chat timestamp if more than one row exists. This is not a claim of current online presence, room-specific attendance, or message reading.
- Execution: successful; nonempty, 10 rows fetched, not fully counted.

## FINAL-U29

List received-cheque records whose cheque number occurs more than once on the same receipt date, including each record identifier, cheque number, receipt date, and duplicate count.

- Domain: finance/treasury; secondary: none; difficulty: Medium.
- Physical tables: gnd_firpd.tblInputCheque.
- Result columns: InputChequeID, ChequeNumber, ReceiptDate, DuplicateCount.
- Relationships: Single-table window count partitioned by ChequeNumber and DoneDate; no counterparty join is needed.
- Semantic contract: DoneDate is the receipt date, as confirmed by the ERP cheque report; ExecuteDate is the due date. Duplicate equality follows stored ChequeNumber and database collation, with no invented bank/account key or string normalization. Empty results are valid after data correction.
- Execution: successful; empty, 0 rows fetched, not fully counted.

## FINAL-U33

List workflow tasks recorded as Done on @ReportDate, showing their task identifiers and completion timestamps.

- Domain: other/unclear; secondary: none; difficulty: Easy.
- Physical tables: gnd_egwfm.tblWorkEnd.
- Result columns: WorkID, CompletedAt.
- Relationships: WorkEnd.ID is the task identifier and is both the primary key and an FK to Work.ID. No Work join is required when only the identifier and recorded completion time are requested.
- Semantic contract: DoneStatusTypeL ID=1 explicitly means Done. WorkEnd.CreateDate is written at the end action, and the ID primary key gives one stored end row per task. A half-open calendar-day filter includes every time on @ReportDate; the relative source date is parameterized. Unrequested originating-form identifiers and completion comments were removed during wording review. This is the normalized stored-Done information need, not a claim to reproduce every undocumented column or status of the original application report. Final human approval was supplied on 2026-09-27.
- Execution: successful; nonempty, 10 rows fetched, not fully counted.

## FINAL-U45

For yarn group @InterweavingID selected from the ERP's yarn-group list and packing dates from @FromDate through @ThroughDate, list serial-numbered packs included by the ERP's 'packing without warehouse receipt' report, showing packing identifier, packing date, and serial.

- Domain: production; secondary: inventory; difficulty: Hard.
- Physical tables: gnd_ficac.tblProjectStandardProduction, gnd_ficac.tblProjectStandardProductionScannedBarcode, gnd_scprd.tblPacking.
- Result columns: PackingID, PackingDate, Serial.
- Relationships: Packing.Serial = ProjectStandardProductionScannedBarcode.Serial is a logical join explicitly used by the ERP report, not an FK. ProjectStandardProductionScannedBarcode.ProjectStandardProductionID -> ProjectStandardProduction.ID is an FK. InterWeavingID filtering uses Packing directly.
- Semantic contract: Preserves the named report OnlyWithoutEnter filter: the maximum ISNULL(Code,0) across production records linked by serial is not 99; no linked record also qualifies. This is the report criterion, not an independent proof that no warehouse receipt exists. Non-null serial and inclusive packing dates are preserved. One row per pack; unused display-name and stock-status joins are omitted. No direct inventory anti-join or invented approval rule is added. Parameter contract: @InterweavingID must identify an entry in gnd_pjprj.evInterweaving, matching an ERP-selectable yarn group. Some physical packing references are absent from that entity view; accepting arbitrary IDs would not preserve the report. The production entity-view identity join was separately checked and removes no current production records. These display/audit-view joins are not physical Gold dependencies; the valid input domain and current-data invariant are explicit.
- Execution: successful; empty, 0 rows fetched, not fully counted.

## Ordered selection trace

Each earlier candidate has a reason below. The original source text and identifiers are not reproduced.

| Domain | Position | Disposition | Reason |
|---|---:|---|---|
| production | 12 | Excluded | Calculation checkbox behavior; configuration/write behavior, not a report. |
| production | 13 | Excluded | Packing picker/visibility configuration; no independent output/filter contract. |
| production | 14 | Excluded | Request to design a waste-packing form; no report fields or rule specified. |
| production | 15 | Excluded | Correction of a wrongly posted warehouse record; data mutation. |
| production | 16 | FINAL-U14 | Explicit label information need: spinning-system name comes from the selected yarn group. Metadata maps the bobbin-label form to SpindleLable and verifies the two FK joins. |
| assets/maintenance | 16 | Excluded | Create asset-purchase forms; configuration, no reporting need. |
| assets/maintenance | 17 | Excluded | Feedback edit failure; write/application error. |
| assets/maintenance | 18 | Excluded | Configure sensor thresholds; configuration only. |
| assets/maintenance | 19 | Excluded | Prevent batch feedback for measurement work orders; write validation. |
| assets/maintenance | 20 | Excluded | Monthly maintenance performer-filter correction lacks its filter contract. Inspected monitoring variants filter Routine.DefaultResponsibleEmployeeID, not actual FeedbackEmployee partners, and differ on month/date rules. Do not invent a performer/month predicate. |
| assets/maintenance | 21 | Excluded | Workflow approval notification/routing change; not a read-only report. |
| assets/maintenance | 22 | Excluded | Asset-registration training; no report specification. |
| assets/maintenance | 23 | Excluded | Correct test records; data mutation. |
| assets/maintenance | 24 | Excluded | Open report by right-click; UI behavior without report output contract. |
| assets/maintenance | 25 | FINAL-U17 | Existing routine coverage-detail rows should be visible. Explicit Persian captions map overlapping activities to RoutineCovered, not Syncronic or inferred date overlaps; both RoutineID FKs verified. |
| other/unclear | 109 | Excluded | Empty home-page issue. |
| other/unclear | 110 | Excluded | Cheque creation error; write behavior. |
| other/unclear | 111 | Excluded | Proceeding-form creation problem; write behavior. |
| other/unclear | 112 | Excluded | Allow multiple daily exchange-rate entries; entry behavior, no report requested. |
| other/unclear | 113 | Excluded | Generic error with no information need. |
| other/unclear | 114 | Excluded | Support-task dashboard states lack verified target-ERP lineage and status predicates; source support database must not be substituted. |
| other/unclear | 115 | Excluded | Empty request. |
| other/unclear | 116 | Excluded | Generic follow-up. |
| other/unclear | 117 | Excluded | Form title without an information need. |
| other/unclear | 118 | Excluded | Empty request. |
| other/unclear | 119 | Excluded | Item-picker SQL error during opening receipt entry; input failure. |
| other/unclear | 120 | Excluded | Workflow routing/configuration of suggestions; write behavior. |
| other/unclear | 121 | Excluded | Ticket submission/network problem. |
| other/unclear | 122 | Excluded | Daily-report access/training without requested report content. |
| other/unclear | 123 | Excluded | Payment request opening error. |
| other/unclear | 124 | Excluded | Exit-interview report specification only in unavailable attachment. |
| other/unclear | 125 | Excluded | SMS issue. |
| other/unclear | 126 | Excluded | Generic date/report error without an identifiable report or output contract. |
| other/unclear | 127 | Excluded | Checkbox layout. |
| other/unclear | 128 | Excluded | Support-task second-deadline dashboard lacks verified target-ERP lineage and required rule. |
| other/unclear | 129 | Excluded | Validate request completeness before submission; write rule, completeness undefined. |
| other/unclear | 130 | Excluded | Empty request. |
| other/unclear | 131 | Excluded | Enable unspecified daily-report feature; no output specification. |
| other/unclear | 132 | Excluded | Offline/error message. |
| other/unclear | 133 | Excluded | Empty connection issue. |
| other/unclear | 134 | Excluded | Empty person-form request. |
| other/unclear | 135 | Excluded | Service-request form creation training. |
| other/unclear | 136 | Excluded | Cheque action error. |
| other/unclear | 137 | FINAL-U22 | Explicit last chat-visit date/time information need. Target ChatLastSeen stores UserID and LastSeenDate; use latest stored time per user, not online/offline or per-room/message-read inference. |
| finance/treasury | 26 | Excluded | Journal generation failure; write behavior. |
| finance/treasury | 27 | Excluded | Detail-grid rendering defect; no independent reporting contract. |
| finance/treasury | 28 | Excluded | Payment workflow usage/training; no reporting need. |
| finance/treasury | 29 | Excluded | Payment gateway registration; write/configuration. |
| finance/treasury | 30 | Excluded | Analytic-person picker failure; input/UI behavior. |
| finance/treasury | 31 | Excluded | Deleted request recovery requires unavailable historical/back-up data. |
| finance/treasury | 32 | Excluded | Copy descriptions during accounting document creation; mutation, with description reporting already represented by U28. |
| finance/treasury | 33 | Excluded | Keyboard search shortcut failure; UI behavior. |
| finance/treasury | 34 | Excluded | Grid sizing/multiline rendering; presentation only. |
| finance/treasury | 35 | Excluded | Verbal onboarding details unavailable; no report contract. |
| finance/treasury | 36 | Excluded | Create return action; workflow/write behavior. |
| finance/treasury | 37 | Excluded | Error opening payment request; no reporting requirement. |
| finance/treasury | 38 | Excluded | Correct legacy customer codes; explicit data mutation. |
| finance/treasury | 39 | FINAL-U29 | Explicit duplicate-cheque report requested in addition to an entry control. Duplicate means same stored ChequeNumber and receipt day; report code aliases InputCheque.DoneDate as CheckReceiptDate. |
| production | 17 | Excluded | Printer hang/performance; no changed information requirement. |
| production | 18 | Excluded | Field placement, font and selection highlighting; presentation only. |
| production | 19 | Excluded | Label rendering, clipped count/machine/head text and serial-print formatting. No independent report beyond the label/yarn-group information selected above; serial-generation formatting is not a stored reporting predicate. |
| production | 20 | Excluded | Split existing project-production records by date; requested data correction. |
| production | 21 | Excluded | Named yarn-group removal after zero stock. Exact report/dataset binding and zero-balance scope are absent. Target report metadata exposes an SSRS report name, not its dataset; similarly named serial-stock procedure does not prove the requested group-level stock rule. |
| production | 22 | Excluded | Same zero-stock removal ambiguity: no authoritative SSRS dataset binding or group-level balance/visibility contract. Do not substitute a similarly named procedure. |
| production | 23 | Excluded | Enable manual barcode entry; input behavior. |
| production | 24 | Excluded | Missing inbound/outbound quantities in finished-goods report. Source mentions project production and final approval; report is an external SSRS name. No verified dataset binding establishes quantity basis, opening balance and approval predicates. |
| production | 25 | Excluded | Named finished-lot removal from the same SSRS report; completion/visibility rule is not established by the exposed report metadata. |
| production | 26 | Excluded | Error copying a production schedule; write operation. |
| production | 27 | Excluded | Duplicate-key error updating a packing list; write operation. |
| production | 28 | Excluded | Add warning descriptions to specific yarn groups; configuration/data change. |
| production | 29 | Excluded | Printing crash/barcode rendering; no reporting requirement. |
| production | 30 | Excluded | Order generated label series during printing; print-generation sequencing, not retrieval of stored business records. |
| production | 31 | Excluded | Empty issue; no information need. |
| production | 32 | Excluded | Synchronize goods after a yarn-group edit; data mutation. |
| production | 33 | Excluded | Suppress zero machine number in printed label; formatting only. |
| production | 34 | Excluded | Automatically assign packaging type from weight; data-entry behavior. |
| production | 35 | Excluded | Remove leading zeroes in printed counters; formatting only. |
| production | 36 | Excluded | Change packaging selector to radio buttons; UI/configuration. |
| production | 37 | Excluded | Current employee leave-balance report family is already selected as U37 and remains under human review. Do not create a second variant or resolve its pending balance semantics through replacement selection. |
| production | 38 | Excluded | Error updating packing list; mutation/application failure. |
| production | 39 | Excluded | Warning while creating a good; mutation/application failure. |
| production | 40 | Excluded | Module setup/training with missing verbal details; no reporting specification. |
| production | 41 | Excluded | Order required fields in an entry form; UI layout. |
| production | 42 | Excluded | Design return-to-packing form; no report specification. |
| production | 43 | Excluded | Design waste label; report content not specified. |
| production | 44 | Excluded | Printed counter formatting; no information need. |
| production | 45 | Excluded | Reconcile carton counts between two named reports. One resolves only to an SSRS name and the other to SELECT 1 with obsolete commented calls to differing procedure variants. No authoritative common time/quantity/receipt contract; cannot substitute packed net weight or an arbitrary variant. |
| production | 46 | Excluded | Permit same-day return-to-packing entry for a role; permissions/write validation. |
| production | 47 | Excluded | Composite daily staffing chart changes require missing definitions of staffing deficit/surplus, temporary staff and long sick leave. Printing/layout fragments do not define an independent report. |
| production | 48 | Excluded | Printed output versus preview size/order; rendering defect. |
| production | 49 | Excluded | Design ZPL printing; format/implementation only. |
| production | 50 | Excluded | Add a price field visible to one user; configuration/permissions and unavailable attachment, no independent report. |
| production | 51 | Excluded | Merge goods and update downstream records; explicit data mutation. |
| production | 52 | Excluded | Create defect-entry form and unspecified related reports; response requests the missing report format. Do not invent outputs. |
| production | 53 | Excluded | Grant batch serial-entry access; permissions/write behavior. |
| production | 54 | Excluded | Report-cell removal specified only in an unavailable attachment. |
| production | 55 | Excluded | Remove an input field; UI configuration. |
| production | 56 | Excluded | Button selected-row transport/reset behavior; not a reporting need. |
| production | 57 | Excluded | Prevent serial registration outside weight tolerance; write validation. |
| production | 58 | Excluded | Automatically create purchase requests; write automation, no independent report requested. |
| production | 59 | Excluded | General production-system/report activation; no output specification. |
| production | 60 | Excluded | Design batch label print format; no information specification. |
| production | 61 | Excluded | Automatic reorder requests/notifications; write automation, no independent reporting contract. |
| production | 62 | Excluded | PDA serial registration; input integration. |
| production | 63 | Excluded | Scale integration with print layout only in unavailable attachment. |
| production | 64 | Excluded | Requested production reports reside in unavailable attachment; response lists reports but not required measurements or formulas. |
| production | 65 | FINAL-U45 | Add a yarn-group filter to the named packing-without-receipt report. Explicit report expression binds spPackingInventoryEnterStatus; its OnlyWithoutEnter predicate is verified and preserved, rather than inventing a receipt anti-join. |

## Integrity and remaining work

## Historical replacement-stage validation

The remaining completion statistics below describe the earlier replacement stage; current totals and blockers are in FINAL_UNSEEN_RECONCILIATION.md.

The 20 pending human-decision case records, questions, SQL and decision statuses were not changed. Current overall execution is 50/50; 42 nonempty, 8 empty, 0 failed. Six queries changed and were bounded-validated; 44 results were reused.

No retrieval, reranking, Qwen, model generation, final evaluation, architecture tuning, database writes, procedure execution, final hash freeze, commit or push occurred. Existing historical manifest hashes were left unchanged and marked stale.
