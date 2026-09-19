# Real-world gold SQL validation

Target: GD4_60_SPN. Validated with a read-only account.
Executable: **13/13**; non-empty: **13**; empty: **0**.

Each reference SELECT is unbounded; only the client fetch is capped at 10 rows.
Fewer than 10 rows proves exhaustion for that execution. A 10-row sample is recorded as not fully counted.
Parameter-dependent outcomes apply to documented diagnostic example bindings, not every possible parameter value.
Example business identifiers and result rows are not persisted. Parameter selector SQL is included in the JSON for reproducibility.

| Case | Executes | Empty | Rows | Exact | Columns |
|---|---|---|---|---|---|
| REAL-C01 | True | False | 2 | True | TransactionID, TransactionCode, DocDate, PeriodSpecID, AccountingLineID, AccountID, Description, Debit, Credit |
| REAL-C02 | True | False | 1 | True | ServiceInvoiceID, InvoiceVAT, AccountingTransactionID, PostedVAT, VATPostingLineCount, VATDifference |
| REAL-C03 | True | False | not fully counted | False | PurchaseRequestID, PurchaseRequestLineID, Sequence, RequestReason, ConsumptionPurpose |
| REAL-C04 | True | False | not fully counted | False | DocumentStage, ProformaID, CommercialInvoiceID, WaybillID, ReceiptID, DocumentID, DocumentLineID, Sequence, GoodID, RecordedQuantity, UnitTypeID, UnitLabel, UnitEnglish, OrderRegistrationNumber, CustomsDeclarationNumber |
| REAL-C05 | True | False | not fully counted | False | ExitID, WarehouseIssueLineID, Sequence, GoodID, GoodCode, Qty |
| REAL-C06 | True | False | 2 | True | AssignmentID, ShiftID, FromDate, EndDateStatus |
| REAL-C07 | True | False | not fully counted | False | SettlementID, ComponentSource, ComponentKey, ComponentLabel, ParameterLineID, RecordedAmount, DebitAmount, CreditAmount |
| REAL-C08 | True | False | not fully counted | False | InterweavingID, InterweavingCode, PackagingTypeID, PackagingLabel, TotalRecordedNetWeight |
| REAL-C09 | True | False | 1 | True | EquipmentID, EquipmentName, EquipmentKind, RoutineID, RoutineName, SensorID, SensorDescription, FeedbackID, ReadingID, GrindingCompletionDate, CotDiameter |
| REAL-C10 | True | False | 2 | True | WorkOrderID, Code, WorkOrderTitle, SuggestedExecutionDate |
| REAL-C11 | True | False | not fully counted | False | BankGuaranteeID, GuaranteeAmount, DepositAmount, NetAmount |
| REAL-C14 | True | False | 1 | True | InterweavingID, InterweavingCode |
| REAL-C15 | True | False | 1 | True | YearMonthID, PayrollMonthStart, PayrollMonthEnd, RecordedLeaveBalanceDays |

## Interpretation and sample limitations

### REAL-C01

Show account activity for a specified financial period, account, and project, including only entries for that project.

Expected/referenced tables: gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail, gnd_fiaci.tblTransDetailDetail.

- Identifiers are supplied parameters. Project form type 12261 is verified schema configuration. EXISTS preserves one result per accounting line.
- Typed project dimension: FormTypeID=12261 and FormID=@ProjectID; no direct project-table FK.
- Blank-string counts in the same sample: {'Description': 1}.

### REAL-C02

For a selected service-purchase invoice, compare its tax amount with the tax amount in its associated accounting entry.

Expected/referenced tables: gnd_scpch.tblServiceInvoice, gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail.

- VAT account 348 and source form type 1208179 are verified configuration, not sampled row IDs. Posted VAT is net debit minus credit on VAT lines only, reported per associated journal. Missing VAT postings remain NULL, not zero.
- tblTrans.FormID=tblServiceInvoice.ID when tblTrans.FormTypeID=1208179.

### REAL-C03

Show purchase-request lines with their recorded request reason and intended use.

Expected/referenced tables: gnd_scpch.tblPurchaseRequestDetail.

- Blank-string counts in the same sample: {'RequestReason': 10, 'ConsumptionPurpose': 10}.

### REAL-C04

Show imports by pro forma invoice, commercial invoice, domestic waybill, and goods receipt, with each stage's item-line quantity in the item's recorded unit, the order-registration number, and the customs-declaration number where applicable. Keep quantities separate between stages.

Expected/referenced tables: gnd_scimp.tblProformaInvoice, gnd_scimp.tblProformaInvoiceDetail, gnd_scimp.tblCurrencyPurchaseInvoice, gnd_scimp.tblCurrencyPurchaseInvoiceDetail, gnd_scimp.tblOrderRegistration, gnd_scimp.tblCottage, gnd_sclog.tblInternalBillOfLading, gnd_sclog.tblInternalBillOfLadingGoodDetail, gnd_scimp.tblForeignReceiveGoods, gnd_scimp.tblForeignReceiveGoodsDetail, gnd_spgod.tblGood, gnd_spgod.tblGoodUnitTypeL.

- UNION ALL preserves one row per recorded stage detail. No sibling detail joins or cross-stage sums. Pro forma rows have no downstream customs number attached: one pro forma can have multiple subsequent invoices. Optional ancestry and lookup joins preserve lines with missing metadata. Units are current item-master units; no conversion or invented historical unit is applied.
- tblCottage.ID=tblCurrencyPurchaseInvoice.ID via verified FK inheritance chain Cottage -> WareHouseBill -> BillOfLading -> PackingList -> CurrencyPurchaseInvoice; intermediate business tables are not queried.
- NULL counts in the bounded sample (10 rows): {'CommercialInvoiceID': 10, 'WaybillID': 10, 'ReceiptID': 10, 'OrderRegistrationNumber': 2, 'CustomsDeclarationNumber': 10}. These are not whole-table completeness measurements.

### REAL-C05

List warehouse issue lines and include the item code for each line.

Expected/referenced tables: gnd_scinv.tblExitDetail, gnd_spgod.tblGood.

- NULL counts in the bounded sample (10 rows): {'Sequence': 10}. These are not whole-table completeness measurements.

### REAL-C06

Show the dated shift-assignment history of a selected former employee, including earlier assignments.

Expected/referenced tables: gnd_hrprs.tblEmployee, gnd_hrcio.tblEmployeeShift.

- Return every dated assignment for the supplied former employee, without filtering to current assignments. IsLeaved defines former status; NULL EndDateStatus remains unknown.
- NULL counts in the bounded sample (2 rows): {'EndDateStatus': 1}. These are not whole-table completeness measurements.

### REAL-C07

Show all recorded monetary components of a selected employee settlement statement, including components with zero amounts.

Expected/referenced tables: gnd_hrpyr.tblBonusBill, gnd_hrpyr.tblBonusBillParameter, gnd_hrpyr.tblMonthlyParameterType.

- Includes all stored monetary fields, including totals as separately labeled stored fields, plus actual parameter rows. Do not add these output amounts together: stored totals can overlap component amounts. NULL and zero remain distinct. RuzeKarkard is a worked-days measure despite its SQL money type and is excluded. Printed application-only lines are not generated.
- NULL counts in the bounded sample (10 rows): {'ParameterLineID': 10, 'DebitAmount': 10, 'CreditAmount': 10}. These are not whole-table completeness measurements.

### REAL-C08

Show total recorded net packaging weight for each yarn group, separately for cartons, pallets, and bags.

Expected/referenced tables: gnd_scprd.tblPacking, gnd_pjprj.tblInterweaving, gnd_spgod.tblPackagingType.

- Verified packaging IDs: 1=pallet, 2=carton, 3=bag. Sum recorded NetWeight only. All-NULL groups remain NULL; NULL readings do not become invented zeros.

### REAL-C09

Show recorded cot-diameter readings and grinding completion dates for SAURER FLYER machines, filtered by machine, completion-date range, and diameter range. Include every recorded reading in the period.

Expected/referenced tables: gnd_amspt.tblFeedbackCheckList, gnd_amspt.tblFeedback, gnd_amspt.tblRoutine, gnd_amast.tblSensor, gnd_amast.tblEquipment, gnd_amast.tblEquipmentKind.

- Equipment kind 56, routine 403 and sensor 30 are verified domain configuration. Date range is inclusive of both calendar dates; diameter endpoints inclusive. Individual readings are retained, without latest-only selection.

### REAL-C10

List maintenance work orders whose proposed dates fall within a specified date range.

Expected/referenced tables: gnd_amspt.tblWorkOrder.

- Inclusive calendar-date range; use SuggestedExecutionDate, not TargetDate.
- NULL counts in the bounded sample (2 rows): {'Code': 1}. These are not whole-table completeness measurements.

### REAL-C11

Show each bank guarantee's amount, its deposit amount, and the net amount after deducting the deposit.

Expected/referenced tables: gnd_firpd.tblBankGuaranty.


### REAL-C14

Which yarn groups have at least one numbered lot with positive posted warehouse stock in the current financial period, without deducting reservations or allocations?

Expected/referenced tables: gnd_spgod.tblGood, gnd_pjprj.tblInterweaving, gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblExit, gnd_scinv.tblExitDetail, gnd_fiaci.tblPeriodSpec.

- Current period is evaluated using SQL Server GETDATE(). Posted means non-NULL movement Code; quantity NULL handling follows the inspected stock logic. Balance is per item, warehouse and current period. Do not subtract demand, reservations or allocations, or add undocumented warehouse restrictions. Results are date-dependent.
- Movement DoneDate lies within PeriodSpec.BeginDate/EndDate (date-range relationship).
- Good.InterweavingID=Interweaving.ID uses their common Project key and verified subtype semantics; no direct FK between these two tables.

### REAL-C15

For a selected employee and payroll month, show the leave balance in days recorded in that month's payroll work record.

Expected/referenced tables: gnd_hrpyr.tblWorkTime, gnd_egbse.tblYearMonth.

- Return physically stored days for the selected employee/month. NULL is not recorded and remains NULL. Do not recalculate leave or claim correctness of the original accrual calculation.
- NULL counts in the bounded sample (1 rows): {'RecordedLeaveBalanceDays': 1}. These are not whole-table completeness measurements.

## Scope and integrity

All reference SQL table sets exactly match the frozen expected sets (40 unique tables).
REAL-C04 remains a 12-table query; its frozen Top-10 ceiling remains 10/12.
The frozen definition, prior gold benchmark, retrieval code and artifacts were hash-checked and left unchanged.
No retrieval or model generation ran. No business writes, DDL, business stored procedures, commit or push were performed.
Live metadata and verification hashes are stored in the JSON. Computed DepositValue retains its existing function dependency.
