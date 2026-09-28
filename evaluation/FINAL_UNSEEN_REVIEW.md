# Final unseen benchmark - current human review package

**HUMAN DECISIONS RECONCILED — SEE FORMAL FREEZE MANIFEST FOR IMMUTABLE IDENTITY**

Authoritative reviewer answers remain in [the decision sheet](FINAL_UNSEEN_HUMAN_DECISIONS.md). Unresolved SQL remains provisional even when executable.

50 executable queries; 42 nonempty; 8 empty. Validation fetches at most 10 rows per query; unchanged exact-SQL-hash results are reused. Only U04/U32/U42 were boundedly revalidated after the latest approved corrections; the other 47 execution results were reused. The human decision gives approved daily leave precedence over hourly leave at employee/date grain; SELECT-only Gold inlines the source calculation.

Resolved reviewed decisions: 50, including U33 replacement. Pending original human decisions: 0; approval/implementation blockers: 0. Replacement decisions: 8; 8 implemented and validated; 0 pending.

Completed replacements: 8; awaiting review: None. Execution blockers: None. Closed-decision local SQL discrepancies: None. No model evaluation was performed. Formal freeze status is recorded separately in FINAL_UNSEEN_FREEZE.md.

## Remaining human approval or implementation blockers

None: human semantics are closed; execution/implementation readiness is reported separately.

## FINAL-U01

Show each sales and services invoice with its invoice date, invoice number, and annual sales order number.

- Domain: sales; difficulty: Easy.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_crsls.tblSalesAndServicesInvoice.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: Single-table invoice projection; no join is required.
- Result columns: InvoiceID, InvoiceNumber, InvoiceDate, AnnualSalesOrderNumber.

```sql
SELECT i.ID AS InvoiceID,i.Code AS InvoiceNumber,i.DoneDate AS InvoiceDate,
       i.AnnualSalesOrderNumber
FROM [gnd_crsls].[tblSalesAndServicesInvoice] AS i;
```

## FINAL-U02

Show each purchase order with its originating purchase request and the requested item's name, quantity, and description.

- Domain: purchasing; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_scpch.tblPurchaseOrder, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: PurchaseOrder.FormTypeID/FormID logically identifies PurchaseRequest.ID; PurchaseRequestDetail.PurchaseRequestID joins the request; PurchaseRequestDetail.GoodID joins Good.ID.
- Result columns: PurchaseOrderID, PurchaseOrderCode, PurchaseRequestID, PurchaseRequestCode, RequestLineID, GoodID, GoodName, RequestedQty, Description.

```sql
SELECT o.ID AS PurchaseOrderID,o.Code AS PurchaseOrderCode,
       r.ID AS PurchaseRequestID,r.Code AS PurchaseRequestCode,
       d.IG AS RequestLineID,g.ID AS GoodID,g.Farsi AS GoodName,
       d.RequestedQty,d.Description
FROM [gnd_scpch].[tblPurchaseOrder] AS o
INNER JOIN [gnd_scpch].[tblPurchaseRequest] AS r
  ON o.FormTypeID=1451914 AND o.FormID=r.ID
INNER JOIN [gnd_scpch].[tblPurchaseRequestDetail] AS d ON d.PurchaseRequestID=r.ID
INNER JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID;
```

## FINAL-U03

Show warehouse item requests whose process is not fully completed, with requester, item, requested quantity, quantity currently in the purchasing queue, and remaining quantity.

- Domain: purchasing; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_hrprs.tblEmployee, gnd_scpch.tblGoodServiceRequest, gnd_scpch.tblGoodServiceRequestDetail, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: Human rule: completion is Code=99 on GoodServiceRequest itself. Code is nullable and NULL rows exist. The existing fnGoodRequestInQueueFromGoodID explicitly uses ISNULL(gsr.Code,-1)<>99; that same NULL-inclusive non-completion rule is used without downstream status inference.
- Relationships: GoodServiceRequestDetail.GoodServiceRequestID joins the request; RequestedEmployeeID joins Employee.ID; detail GoodID joins Good.ID.
- Result columns: RequestID, RequestCode, RequestedDate, EmployeeID, EmployeeCode, RequestLineID, GoodID, GoodName, RequestQty, QtyInQueue, RemainedQty.

```sql
SELECT r.ID AS RequestID,r.Code AS RequestCode,r.RequestedDate,
       e.ID AS EmployeeID,e.EmployeeCode,d.IG AS RequestLineID,
       g.ID AS GoodID,g.Farsi AS GoodName,d.RequestQty,d.QtyInQueue,d.RemainedQty
FROM [gnd_scpch].[tblGoodServiceRequest] AS r
INNER JOIN [gnd_scpch].[tblGoodServiceRequestDetail] AS d ON d.GoodServiceRequestID=r.ID
LEFT JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=r.RequestedEmployeeID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE ISNULL(r.Code,-1)<>99;
```

## FINAL-U04

List the loading records for @ReportDate by driver, including the total net cargo weight.

- Domain: imports/logistics; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_crsls.tblLoading, gnd_crsls.tblLoadingDetail, gnd_crsls.tblLoadingSerialDetail, gnd_scinv.tblSerial, gnd_scinv.tblTransportationCompanyDriverDetail, gnd_scprd.tblPacking, gnd_scprd.tblRawMaterialPacking, gnd_scprd.tblWastePacking.
- Execution: successful; nonempty bounded result.
- Semantics: Use COALESCE(CargoTotalNetWeight,TotalNetWeight): stored cargo weight when present, computed total net weight when NULL. Same-day @ReportDate range; driver via TransportationCompanyDriverIG. Explicit latest human decision supersedes the former no-fallback interpretation.
- Relationships: Loading.TransportationCompanyDriverIG joins TransportationCompanyDriverDetail.IG.
- Result columns: LoadingID, Code, DoneDate, DriverRecordID, DriverName, TotalNetCargoWeight.

```sql
SELECT
    l.ID AS LoadingID,
    l.Code,
    l.DoneDate,
    d.IG AS DriverRecordID,
    d.DriverName,
    COALESCE(l.CargoTotalNetWeight,l.TotalNetWeight) AS TotalNetCargoWeight
FROM gnd_crsls.tblLoading AS l
LEFT JOIN gnd_scinv.tblTransportationCompanyDriverDetail AS d
    ON d.IG=l.TransportationCompanyDriverIG
WHERE l.DoneDate>=@ReportDate
  AND l.DoneDate<DATEADD(day,1,@ReportDate);
```

## FINAL-U05

List sales orders with at least one unshipped line and an annual sales order number greater than or equal to @MinAnnualSalesOrderNumber.

- Domain: imports/logistics; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_crsls.tblSalesOrder, gnd_crsls.tblSalesOrderDetail, gnd_crsls.tblSalesOrderWasteDetail.
- Execution: successful; nonempty bounded result.
- Semantics: Human rule: NULL HasShipped means unshipped. DeliveryDate reproduces the existing helper branch (OrderTypeID=1267: maximum detail delivery date; otherwise maximum waste-detail delivery date) but omits its GETDATE fallback. Missing delivery dates remain NULL.
- Relationships: SalesOrderDetail.SalesOrderID joins SalesOrder.ID inside the unshipped-line existence test.
- Result columns: SalesOrderID, Code, OrderDate, AnnualSalesOrderNumber, DeliveryDate, DeliveryToCustomerID.

```sql
SELECT o.ID AS SalesOrderID,o.Code,o.OrderDate,o.AnnualSalesOrderNumber,
       CASE WHEN o.OrderTypeID=1267 THEN
         (SELECT MAX(dd.DeliveryDate) FROM [gnd_crsls].[tblSalesOrderDetail] AS dd
          WHERE dd.SalesOrderID=o.ID)
       ELSE
         (SELECT MAX(wd.DeliveryDate) FROM [gnd_crsls].[tblSalesOrderWasteDetail] AS wd
          WHERE wd.SalesOrderID=o.ID)
       END AS DeliveryDate,o.DeliveryToCustomerID
FROM [gnd_crsls].[tblSalesOrder] AS o
WHERE o.AnnualSalesOrderNumber>=@MinAnnualSalesOrderNumber
  AND EXISTS (SELECT 1 FROM [gnd_crsls].[tblSalesOrderDetail] AS d
              WHERE d.SalesOrderID=o.ID AND ISNULL(d.HasShipped,0)=0);
```

## FINAL-U06

Show purchase-invoice goods lines alongside each linked warehouse receipt, including the receipt identifier, warehouse, item code and description, invoiced quantity, and invoiced amount.

- Domain: inventory; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_scinv.tblEnter, gnd_scinv.tblInventory, gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblPurchaseInvoiceGoodDetailEnter, gnd_scpch.tblPurchaseInvoiceSeparatedEnter, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: Source-linked report definition proves invoice -> separated receipt (FormTypeID 1513618) -> warehouse receipt (27887). Invoice.FormID alone is not a receipt ID. Preserve the report grain: invoice goods line alongside each linked receipt, not an asserted receipt-detail allocation.
- Relationships: PurchaseInvoiceGoodDetailEnter.PurchaseInvoiceGoodAndServiceID -> PurchaseInvoiceGoodAndService.ID (FK). PurchaseInvoiceSeparatedEnter.FormTypeID=1513618/FormID -> invoice.ID; Enter.FormTypeID=27887/FormID -> separated receipt.ID (explicit report metadata, polymorphic). Enter.CredbInventoryID -> Inventory.ID; invoice detail.GoodID -> Good.ID (FK). 
- Result columns: PurchaseInvoiceID, PurchaseInvoiceCode, ReceiptID, InvoiceLineID, InventoryID, InventoryName, GoodID, GoodCode, GoodName, Qty, AccValue.

```sql
SELECT i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,
       h.ID AS ReceiptID,
       d.IG AS InvoiceLineID,v.ID AS InventoryID,v.Farsi AS InventoryName,
       g.ID AS GoodID,g.GoodCode,g.Farsi AS GoodName,d.Qty,d.AccValue
FROM [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceGoodDetailEnter] AS d
  ON d.PurchaseInvoiceGoodAndServiceID=i.ID
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceSeparatedEnter] AS se
  ON se.FormTypeID=1513618 AND se.FormID=i.ID
INNER JOIN [gnd_scinv].[tblEnter] AS h
  ON h.FormTypeID=27887 AND h.FormID=se.ID
LEFT JOIN [gnd_scinv].[tblInventory] AS v ON v.ID=h.CredbInventoryID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID;
```

## FINAL-U07

For each employee and payroll month, show the number of recorded additional off dates.

- Domain: personnel/attendance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrcio.tblEmployeeShiftAdditionalOffDates, gnd_hrprs.tblEmployee.
- Execution: successful; empty bounded result.
- Semantics: Human decision confirms explicitly recorded additional off dates only; ordinary roster off days are excluded. Existing SQL is unchanged. An empty source table is retained as a valid empty result.
- Relationships: EmployeeID joins Employee.ID; an off date is assigned to YearMonth by the inclusive FromDate/ToDate interval (a logical date-range join).
- Result columns: EmployeeID, EmployeeCode, YearMonthID, Year, MonthID, AdditionalOffDateCount.

```sql
SELECT e.ID AS EmployeeID,e.EmployeeCode,y.ID AS YearMonthID,y.[Year],y.MonthID,
       COUNT_BIG(*) AS AdditionalOffDateCount
FROM [gnd_hrcio].[tblEmployeeShiftAdditionalOffDates] AS o
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=o.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON o.[Date]>=y.FromDate AND o.[Date]<=y.ToDate
GROUP BY e.ID,e.EmployeeCode,y.ID,y.[Year],y.MonthID;
```

## FINAL-U08

For exit-permission requests in the selected date range, show counts by department, exit reason and workflow status, and average minutes from initial request registration to final approval, excluding never-approved requests from the average even when retained in counts.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbpm.tblProcessStep, gnd_egbse.tblDepartment, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork, gnd_egwfm.tblWorkRoute, gnd_hrcio.tblEmployeeExitPermission, gnu_hrcio.xblEmployeeExitPermission.
- Execution: successful; nonempty bounded result.
- Semantics: CLOSED authoritative rule implemented: initial registration is xblEmployeeExitPermission.CreateDate. Final approval is MAX WorkRoute.LastPlaceChangeDate at a ProcessStep named End, across every matching permit-form route and process. Status grouping retains the previous latest-task convention only for the status label; it never determines approval. Never-approved permits remain in counts and contribute NULL to AVG. RunStatusTypeID=3 alone is not approval.
- Relationships: Permit.ID -> xblEmployeeExitPermission.ID; Work/WorkRoute FormTypeID=39754 and FormID -> permit.ID; WorkRoute.CurrentProcessStepID -> ProcessStep.ID. Approval aggregation has one row per permit across all matching routes.
- Result columns: DepartmentID, DepartmentName, ExitReason, WorkflowStatusID, WorkflowStatus, PermitCount, AverageElapsedMinutes.

```sql
WITH RankedWork AS (
 SELECT w.FormID,w.RunStatusTypeID,
        ROW_NUMBER() OVER(PARTITION BY w.FormID ORDER BY w.CreateDate DESC,w.ID DESC) AS rn
 FROM gnd_egwfm.tblWork w WHERE w.FormTypeID=39754
), ApprovalEvents AS (
 SELECT r.FormID,MAX(r.LastPlaceChangeDate) AS FinalApprovalTime
 FROM gnd_egwfm.tblWorkRoute r
 INNER JOIN gnd_egbpm.tblProcessStep ps ON ps.ID=r.CurrentProcessStepID
 WHERE r.FormTypeID=39754 AND ps.Name=N'End'
 GROUP BY r.FormID
)
SELECT p.DepartmentID,d.Name AS DepartmentName,p.ExitReason,
       s.ID AS WorkflowStatusID,s.Description AS WorkflowStatus,
       COUNT_BIG(*) AS PermitCount,
       AVG(CASE WHEN a.FinalApprovalTime IS NOT NULL
           THEN CONVERT(decimal(18,2),DATEDIFF(minute,x.CreateDate,a.FinalApprovalTime))
           END) AS AverageElapsedMinutes
FROM gnd_hrcio.tblEmployeeExitPermission p
LEFT JOIN gnu_hrcio.xblEmployeeExitPermission x ON x.ID=p.ID
LEFT JOIN RankedWork w ON w.FormID=p.ID AND w.rn=1
LEFT JOIN ApprovalEvents a ON a.FormID=p.ID
LEFT JOIN gnd_egwfm.tblRunStatusTypeL s ON s.ID=w.RunStatusTypeID
LEFT JOIN gnd_egbse.tblDepartment d ON d.ID=p.DepartmentID
WHERE p.ExitDate>=@FromDate AND p.ExitDate<DATEADD(day,1,@ThroughDate)
GROUP BY p.DepartmentID,d.Name,p.ExitReason,s.ID,s.Description;
```

## FINAL-U09

Show the history of employee shift modifications, including the modification date, previous shift, new shift, and recorded change description.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShiftTemplate, gnd_hrprs.tblEmployee.
- Execution: successful; nonempty bounded result.
- Semantics: CLOSED authoritative rule implemented: modification.ShiftID is the new daily override. Previous effective shift comes from the greatest eligible base-assignment FromDate on that same date, with EndDateStatus eligibility and CurrentStatusTypeID NOT IN (4,6). DISTINCT collapses identical ShiftIDs tied at that date; the authoritative diagnostic found no different ShiftIDs among such ties. No LAG, prior-day substitution, or ID ordering is used.
- Relationships: Modification.EmployeeID -> Employee.ID. Base EmployeeShift joins the same employee/date using the approved interval/status predicates and maximum eligible FromDate; identical tied ShiftIDs are deduplicated. Both ShiftIDs -> ShiftTemplate.ID.
- Result columns: ModificationID, EmployeeID, EmployeeCode, ModificationDate, PreviousShiftID, PreviousShift, NewShiftID, NewShift, DescriptionUpdated.

```sql
SELECT m.ID AS ModificationID,m.EmployeeID,e.EmployeeCode,m.[Date] AS ModificationDate,
       prev.ShiftID AS PreviousShiftID,ps.NameInEnglish AS PreviousShift,
       m.ShiftID AS NewShiftID,ns.NameInEnglish AS NewShift,m.DescriptionUpdated
FROM gnd_hrcio.tblEmployeeShiftModifications m
OUTER APPLY (
 SELECT DISTINCT es.ShiftID
 FROM gnd_hrcio.tblEmployeeShift es
 WHERE es.EmployeeID=m.EmployeeID AND es.FromDate<=m.[Date]
   AND ISNULL(es.EndDateStatus,m.[Date])>=m.[Date]
   AND es.CurrentStatusTypeID NOT IN (4,6)
   AND es.FromDate=(
       SELECT MAX(s.FromDate) FROM gnd_hrcio.tblEmployeeShift s
       WHERE s.EmployeeID=m.EmployeeID AND s.FromDate<=m.[Date]
         AND ISNULL(s.EndDateStatus,m.[Date])>=m.[Date]
         AND s.CurrentStatusTypeID NOT IN (4,6)
   )
) prev
LEFT JOIN gnd_hrprs.tblEmployee e ON e.ID=m.EmployeeID
LEFT JOIN gnd_hrcio.tblShiftTemplate ps ON ps.ID=prev.ShiftID
LEFT JOIN gnd_hrcio.tblShiftTemplate ns ON ns.ID=m.ShiftID;
```

## FINAL-U10

For each employee and complete payroll month between @FromPayrollMonthID and @ThroughPayrollMonthID, show stored work hours, non-work hours, regular overtime hours, leave days and hours, and mission days and hours.

- Domain: personnel/attendance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime.
- Execution: successful; nonempty bounded result.
- Semantics: Monthly WorkTime facts are authoritative. Non-work is stored shortfall (SaatKasrKarcdur); overtime is the stored regular overtime component. Duration fields are minutes, divided by 60.0; AnnualLeave and TedadRuzMamuriat are days. Month parameters are monthly YearMonth IDs, ordered by calendar dates, not numeric IDs. No event recomputation or proration.
- Relationships: WorkTime.EmployeeID -> Employee.ID and WorkTime.YearMonthID -> YearMonth.ID. Parameter month rows bound complete calendar periods.
- Result columns: WorkTimeID, EmployeeID, EmployeeCode, YearMonthID, WorkHours, NonWorkHours, RegularOvertimeHours, LeaveDays, LeaveHours, MissionDays, MissionHours.

```sql
SELECT w.ID AS WorkTimeID,w.EmployeeID,e.EmployeeCode,w.YearMonthID,
       w.SaatKarkardcdur/60.0 AS WorkHours,w.SaatKasrKarcdur/60.0 AS NonWorkHours,
       w.SaatEzafeKarcdur/60.0 AS RegularOvertimeHours,
       w.AnnualLeave AS LeaveDays,w.SaatMorakhasicdur/60.0 AS LeaveHours,
       w.TedadRuzMamuriat AS MissionDays,w.SaatMamuriatcdur/60.0 AS MissionHours
FROM gnd_hrpyr.tblWorkTime w
JOIN gnd_hrprs.tblEmployee e ON e.ID=w.EmployeeID
JOIN gnd_egbse.tblYearMonth y ON y.ID=w.YearMonthID
JOIN gnd_egbse.tblYearMonth f ON f.ID=@FromPayrollMonthID AND f.MonthID IS NOT NULL
JOIN gnd_egbse.tblYearMonth t ON t.ID=@ThroughPayrollMonthID AND t.MonthID IS NOT NULL
WHERE y.MonthID IS NOT NULL AND y.FromDate>=f.FromDate AND y.ToDate<=t.ToDate;
```

## FINAL-U11

For each employee and payroll month with active meal credits, show total recorded meal entitlement, requested meal quantity, delivered meal count, and remaining entitlement after delivery.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrfod.tblEmployeeFood, gnd_hrfod.tblEmployeeFoodDelivery, gnd_hrfod.tblEmployeeFoodRequest, gnd_hrfod.tblEmployeeFoodRequestDetail, gnd_hrprs.tblEmployee.
- Execution: successful; nonempty bounded result.
- Semantics: Active FoodCount credits are additive per employee/payroll month. Requests and delivered meals are independently aggregated over the same nonoverlapping monthly YearMonth dates; each total joins once. Remaining = credits minus delivered rows. Months without credits are outside the entitlement-led report.
- Relationships: Employee identity links independent credit/request/delivery aggregates. RequestDetail.EmployeeFoodRequestID -> Request.ID. Date-range joins to monthly YearMonth are logical calendar joins; no FK is claimed.
- Result columns: EmployeeID, EmployeeCode, YearMonthID, RecordedMealEntitlement, RequestedMealQuantity, DeliveredMealCount, RemainingEntitlement.

```sql
WITH Credits AS (
 SELECT a.EmployeeID,y.ID AS YearMonthID,SUM(a.FoodCount) AS Entitlement
 FROM gnd_hrfod.tblEmployeeFood a JOIN gnd_egbse.tblYearMonth y
 ON a.Date BETWEEN y.FromDate AND y.ToDate AND y.MonthID IS NOT NULL
 WHERE a.IsActive=1 GROUP BY a.EmployeeID,y.ID
), Requests AS (
 SELECT h.EmployeeID,y.ID AS YearMonthID,SUM(d.Qty) AS Qty
 FROM gnd_hrfod.tblEmployeeFoodRequest h
 JOIN gnd_hrfod.tblEmployeeFoodRequestDetail d ON d.EmployeeFoodRequestID=h.ID
 JOIN gnd_egbse.tblYearMonth y ON d.Date BETWEEN y.FromDate AND y.ToDate AND y.MonthID IS NOT NULL
 GROUP BY h.EmployeeID,y.ID
), Deliveries AS (
 SELECT d.EmployeeID,y.ID AS YearMonthID,COUNT_BIG(*) AS Qty
 FROM gnd_hrfod.tblEmployeeFoodDelivery d
 JOIN gnd_egbse.tblYearMonth y ON d.Date BETWEEN y.FromDate AND y.ToDate AND y.MonthID IS NOT NULL
 WHERE d.IsDelivered=1 GROUP BY d.EmployeeID,y.ID
)
SELECT a.EmployeeID,e.EmployeeCode,a.YearMonthID,a.Entitlement AS RecordedMealEntitlement,
 ISNULL(r.Qty,0) AS RequestedMealQuantity,ISNULL(d.Qty,0) AS DeliveredMealCount,
 a.Entitlement-ISNULL(d.Qty,0) AS RemainingEntitlement
FROM Credits a LEFT JOIN gnd_hrprs.tblEmployee e ON e.ID=a.EmployeeID
LEFT JOIN Requests r ON r.EmployeeID=a.EmployeeID AND r.YearMonthID=a.YearMonthID
LEFT JOIN Deliveries d ON d.EmployeeID=a.EmployeeID AND d.YearMonthID=a.YearMonthID;
```

## FINAL-U12

For each employee loan request, show the request date, stored portion value, stored maximum loan amount, and the employee's latest recorded fund balance as of @AsOfDate.

- Domain: payroll; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_hrprs.tblEmployee, gnd_hrpyr.tblCofferMembership, gnd_hrpyr.tblEmployeeLoanRequest.
- Execution: successful; nonempty bounded result.
- Semantics: Stored UpperLoanAmount is the authoritative maximum; PortionValue remains stored. Additional balance is latest dated CofferMembership row valid at @AsOfDate, ordered FromDate DESC, ID DESC; it never recalculates the ceiling.
- Relationships: LoanRequest.EmployeeID joins Employee.ID; fund membership is selected logically by EmployeeID and the effective date interval.
- Result columns: LoanRequestID, EmployeeID, EmployeeCode, RequestDate, StoredPortionValue, StoredMaximumLoanAmount, MembershipID, LatestRecordedFundBalance, BalanceEffectiveFrom.

```sql
SELECT r.ID AS LoanRequestID,r.EmployeeID,e.EmployeeCode,r.RequestDate,
       r.PortionValue AS StoredPortionValue,r.UpperLoanAmount AS StoredMaximumLoanAmount,
       m.ID AS MembershipID,m.SavedUpAmount AS LatestRecordedFundBalance,m.FromDate AS BalanceEffectiveFrom
FROM [gnd_hrpyr].[tblEmployeeLoanRequest] AS r
LEFT JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=r.EmployeeID
OUTER APPLY (
 SELECT TOP (1) c.ID,c.SavedUpAmount,c.FromDate
 FROM [gnd_hrpyr].[tblCofferMembership] AS c
 WHERE c.EmployeeID=r.EmployeeID AND c.FromDate<=@AsOfDate
   AND (c.ToDate IS NULL OR c.ToDate>=@AsOfDate)
 ORDER BY c.FromDate DESC,c.ID DESC
) AS m;
```

## FINAL-U13

Show total packed net production by interweaving, including yarn type, spinning system, quality, and spinning count for filtering.

- Domain: production; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_pjprj.tblInterweaving, gnd_scprd.tblPacking, gnd_spgod.tblQualityType, gnd_spgod.tblSpinningCountType, gnd_spgod.tblSpinningSystemType, gnd_spgod.tblYarnType.
- Execution: successful; nonempty bounded result.
- Semantics: Production quantity is the sum of stored Packing.NetWeight.
- Relationships: Packing.InterWeavingID joins Interweaving.ID; Interweaving's yarn, spinning-system, quality, and spinning-count IDs join their lookup tables.
- Result columns: InterweavingID, InterweavingCode, YarnType, SpinningSystem, Quality, SpinningCount, TotalPackedNetWeight.

```sql
SELECT i.ID AS InterweavingID,i.InterweavingCode,
       yt.Farsi AS YarnType,ss.Farsi AS SpinningSystem,q.Farsi AS Quality,
       sc.Farsi AS SpinningCount,SUM(p.NetWeight) AS TotalPackedNetWeight
FROM [gnd_scprd].[tblPacking] AS p
INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=p.InterWeavingID
LEFT JOIN [gnd_spgod].[tblYarnType] AS yt ON yt.ID=i.YarnTypeID
LEFT JOIN [gnd_spgod].[tblSpinningSystemType] AS ss ON ss.ID=i.SpinningSystemTypeID
LEFT JOIN [gnd_spgod].[tblQualityType] AS q ON q.ID=i.QualityTypeID
LEFT JOIN [gnd_spgod].[tblSpinningCountType] AS sc ON sc.ID=i.SpinningCountTypeID
GROUP BY i.ID,i.InterweavingCode,yt.Farsi,ss.Farsi,q.Farsi,sc.Farsi;
```

## FINAL-U14

For each bobbin-label record, show its yarn-group code and the spinning-system name defined for that yarn group.

- Domain: production; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_pjprj.tblInterweaving, gnd_scprd.tblSpindleLable, gnd_spgod.tblSpinningSystemType.
- Execution: successful; nonempty bounded result.
- Semantics: One row per stored bobbin-label record, not per generated printed label. The spinning-system name is its stored Persian display name; no translation or machine-name substitution. UI editability and mandatory-entry changes are outside the extracted reporting need.
- Relationships: SpindleLable.InterweavingID -> Interweaving.ID; Interweaving.SpinningSystemTypeID -> SpinningSystemType.ID are explicit FKs.
- Result columns: BobbinLabelID, InterweavingID, InterweavingCode, SpinningSystemName.

```sql
SELECT l.ID AS BobbinLabelID,i.ID AS InterweavingID,i.InterweavingCode,
       s.Farsi AS SpinningSystemName
FROM [gnd_scprd].[tblSpindleLable] AS l
INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=l.InterweavingID
INNER JOIN [gnd_spgod].[tblSpinningSystemType] AS s ON s.ID=i.SpinningSystemTypeID;
```

## FINAL-U15

List quality-control records since @StartDate for cotton fibers, viscose fibers, paper bobbins, and plastic bobbins that have no directly associated purchase invoice, including the item and recorded quantities.

- Domain: quality; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblQualityControl, gnd_scpch.tblQualityControlDetail, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: Authoritative non-asset scope: GoodGroupID 1487/1488/1489/1490. Direct invoice FormTypeID=1684173/FormID=QualityControl.ID is sufficient. No broad GoodType or packaging-supply category is substituted.
- Relationships: QualityControlDetail.QualityControlID joins QualityControl.ID and GoodID joins Good.ID; invoice absence uses the logical FormTypeID/FormID source-document link.
- Result columns: QualityControlID, Code, DoneDate, QualityControlLineID, GoodID, GoodCode, GoodName, Qty, NotifiQTY, CQty.

```sql
SELECT q.ID AS QualityControlID,q.Code,q.DoneDate,d.IG AS QualityControlLineID,
       g.ID AS GoodID,g.GoodCode,g.Farsi AS GoodName,d.Qty,d.NotifiQTY,d.CQty
FROM [gnd_scpch].[tblQualityControl] AS q
INNER JOIN [gnd_scpch].[tblQualityControlDetail] AS d ON d.QualityControlID=q.ID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE q.DoneDate>=@StartDate
  AND g.GoodGroupID IN (1487,1488,1489,1490)
  AND NOT EXISTS (
    SELECT 1 FROM [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
    WHERE i.FormTypeID=1684173 AND i.FormID=q.ID
  );
```

## FINAL-U16

List generated maintenance work orders that have no assigned responsible employee, including equipment, routine, and suggested execution date.

- Domain: assets/maintenance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_amast.tblEquipment, gnd_amspt.tblRoutine, gnd_amspt.tblWorkOrder.
- Execution: successful; empty bounded result.
- Semantics: Human-approved unassigned criterion is solely ResponsibleEmployeeID IS NULL; no scheduling, recurrence, team, contractor or due-date condition.
- Relationships: WorkOrder.EquipmentID joins Equipment.ID and RoutineID joins Routine.ID.
- Result columns: WorkOrderID, Code, WorkOrderTitle, SuggestedExecutionDate, EquipmentID, EquipmentName, RoutineID, RoutineName.

```sql
SELECT w.ID AS WorkOrderID,w.Code,w.WorkOrderTitle,w.SuggestedExecutionDate,
       w.EquipmentID,e.NameInEnglish AS EquipmentName,
       w.RoutineID,r.English AS RoutineName
FROM [gnd_amspt].[tblWorkOrder] AS w
LEFT JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=w.EquipmentID
LEFT JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=w.RoutineID
WHERE w.ResponsibleEmployeeID IS NULL;
```

## FINAL-U17

For @RoutineID, list the recorded overlapping maintenance activities, showing the activity-card name and each covered activity identifier and name.

- Domain: assets/maintenance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_amspt.tblRoutine, gnd_amspt.tblRoutineCovered.
- Execution: successful; nonempty bounded result.
- Semantics: Overlapping means the explicitly stored coverage relation labelled Covered Routine in ERP metadata. It does not mean calculated time overlap or simultaneous/prerequisite routines. One row per coverage-detail IG. @RoutineID replaces source-specific activity identifiers.
- Relationships: RoutineCovered.RoutineID -> Routine.ID and RoutineCovered.CoveredRoutineID -> Routine.ID are explicit FKs; Routine is joined twice in different roles.
- Result columns: RoutineID, RoutineName, CoverageLineID, CoveredRoutineID, CoveredRoutineName.

```sql
SELECT r.ID AS RoutineID,r.Farsi AS RoutineName,c.IG AS CoverageLineID,
       covered.ID AS CoveredRoutineID,covered.Farsi AS CoveredRoutineName
FROM [gnd_amspt].[tblRoutineCovered] AS c
INNER JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=c.RoutineID
INNER JOIN [gnd_amspt].[tblRoutine] AS covered ON covered.ID=c.CoveredRoutineID
WHERE c.RoutineID=@RoutineID;
```

## FINAL-U18

List payment requests dated from @FromDate through @ThroughDate, including each request-detail row.

- Domain: finance/treasury; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_firpd.tblPayRequest, gnd_firpd.tblPayRequestDetail.
- Execution: successful; nonempty bounded result.
- Semantics: Human decision limits the report to request plus request-detail grain, one result row per request detail. The date range filters PayRequestDate. RequestedExecutionDate is the requested header date, not an executed payment. No PayRequestPayment dependency or payment execution fields remain.
- Relationships: PayRequestDetail.PayRequestID -> PayRequest.ID. One row per request detail; no payment-execution join.
- Result columns: PayRequestID, Code, PayRequestDate, RequestedExecutionDate, PayRequestLineID, Sequence, Amount, LineDescription, PayDate.

```sql
SELECT r.ID AS PayRequestID,r.Code,r.PayRequestDate,r.ExecuteDate AS RequestedExecutionDate,
       d.ID AS PayRequestLineID,d.Sequence,d.Amount,d.Description AS LineDescription,d.PayDate
FROM [gnd_firpd].[tblPayRequest] AS r
INNER JOIN [gnd_firpd].[tblPayRequestDetail] AS d ON d.PayRequestID=r.ID
WHERE r.PayRequestDate>=@FromDate AND r.PayRequestDate<DATEADD(day,1,@ThroughDate);
```

## FINAL-U19

Show each bank receipt with its accounting detail lines, including account, amount, and descriptions.

- Domain: finance/treasury; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_fiaci.tblAccount, gnd_firpd.tblBankInput, gnd_firpd.tblBankInputDetail.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: BankInputDetail.BankInputID joins BankInput.ID and AccountID joins Account.ID.
- Result columns: BankReceiptID, Code, DoneDate, ReceiptAmount, AccountingLineID, Sequence, AccountID, AccountCode, AccountName, LineAmount, LineDescription, TransDetail.

```sql
SELECT b.ID AS BankReceiptID,b.Code,b.DoneDate,b.AccValue AS ReceiptAmount,
       d.IG AS AccountingLineID,d.Sequence,d.AccountID,a.AccountCode,a.Farsi AS AccountName,
       d.AccValue AS LineAmount,d.Description AS LineDescription,d.TransDetail
FROM [gnd_firpd].[tblBankInput] AS b
INNER JOIN [gnd_firpd].[tblBankInputDetail] AS d ON d.BankInputID=b.ID
LEFT JOIN [gnd_fiaci].[tblAccount] AS a ON a.ID=d.AccountID;
```

## FINAL-U20

For the selected accounting detail entity, show every journal line and the account through which it moved.

- Domain: finance/treasury; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_fiaci.tblAccount, gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail, gnd_fiaci.tblTransDetailDetail.
- Execution: successful; nonempty bounded result.
- Semantics: The selected accounting detail entity is supplied by FormTypeID and FormID parameters.
- Relationships: TransDetailDetail.TransDetailIG joins TransDetail.IG; TransDetail.TransID joins Trans.ID and AccountID joins Account.ID; FormTypeID/FormID selects the polymorphic source entity.
- Result columns: TransactionID, TransactionCode, DocDate, JournalLineID, RowNumber, AccountID, AccountCode, AccountName, Description, Debit, Credit.

```sql
SELECT t.ID AS TransactionID,t.Code AS TransactionCode,t.DocDate,
       d.IG AS JournalLineID,d.RowNumber,d.AccountID,a.AccountCode,a.Farsi AS AccountName,
       d.Description,d.Debit,d.Credit
FROM [gnd_fiaci].[tblTransDetailDetail] AS x
INNER JOIN [gnd_fiaci].[tblTransDetail] AS d ON d.IG=x.TransDetailIG
INNER JOIN [gnd_fiaci].[tblTrans] AS t ON t.ID=d.TransID
LEFT JOIN [gnd_fiaci].[tblAccount] AS a ON a.ID=d.AccountID
WHERE x.FormTypeID=@DetailFormTypeID AND x.FormID=@DetailFormID
ORDER BY t.DocDate,t.ID,d.RowNumber;
```

## FINAL-U21

List each project with its related goods-and-services purchase invoices, including invoice date, supplier identifier, and total payable.

- Domain: projects; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_pjprj.tblProject, gnd_scpch.tblPurchaseInvoiceGoodAndService.
- Execution: successful; nonempty bounded result.
- Semantics: Human decision confirms goods/services purchase invoices only, using their explicit CredbProjectID relationship. Existing SQL is unchanged.
- Relationships: PurchaseInvoiceGoodAndService.CredbProjectID joins Project.ID.
- Result columns: ProjectID, ProjectName, PurchaseInvoiceID, PurchaseInvoiceCode, InvoiceDate, SupplierID, TotalPayable.

```sql
SELECT p.ID AS ProjectID,p.Farsi AS ProjectName,
       i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,i.DoneDate AS InvoiceDate,
       i.CredbSupplierID AS SupplierID,i.SumPayable AS TotalPayable
FROM [gnd_pjprj].[tblProject] AS p
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
  ON i.CredbProjectID=p.ID;
```

## FINAL-U22

For each user with a recorded chat visit, show the latest recorded visit date and time.

- Domain: other/unclear; difficulty: Easy.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblChatLastSeen.
- Execution: successful; nonempty bounded result.
- Semantics: UserID identifies the user without outputting a username or personal name. MAX(LastSeenDate) gives the latest stored chat timestamp if more than one row exists. This is not a claim of current online presence, room-specific attendance, or message reading.
- Relationships: Single-table aggregation by UserID; no user-profile or message-content join is required.
- Result columns: UserID, LastSeenAt.

```sql
SELECT c.UserID,MAX(c.LastSeenDate) AS LastSeenAt
FROM [gnd_egbse].[tblChatLastSeen] AS c
GROUP BY c.UserID;
```

## FINAL-U23

List each role with the systems, forms, and reports assigned to it, including display and edit permissions.

- Domain: other/unclear; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblRole, gnd_egbse.tblRoleDomain, gnd_egbse.tblRoleSystem, gnd_egbse.tblRoleSystemForm, gnd_egbse.tblRoleSystemReport, gnd_egfrm.tblFormType, gnd_egrpt.tblReport, gnd_egsys.tblCaption, gnd_egsys.tblSystem.
- Execution: successful; nonempty bounded result.
- Semantics: Forms and reports are combined into one permission-shaped result with UNION ALL.
- Relationships: RoleDomain joins Role; RoleSystem joins RoleDomain; form/report permission rows join RoleSystem and then their form/report metadata and caption.
- Result columns: RoleID, RoleName, SystemID, SystemName, ContentType, ContentID, ContentName, GrantDisplay, GrantEdit.

```sql
SELECT r.ID AS RoleID,r.Description AS RoleName,s.ID AS SystemID,s.Description AS SystemName,
       N'Form' AS ContentType,f.ID AS ContentID,c.Farsi AS ContentName,
       rf.GrantDisplay,rf.GrantEdit
FROM [gnd_egbse].[tblRole] AS r
INNER JOIN [gnd_egbse].[tblRoleDomain] AS rd ON rd.RoleID=r.ID
INNER JOIN [gnd_egbse].[tblRoleSystem] AS rs ON rs.RoleDomainIG=rd.IG
INNER JOIN [gnd_egsys].[tblSystem] AS s ON s.ID=rs.SystemID
INNER JOIN [gnd_egbse].[tblRoleSystemForm] AS rf ON rf.RoleSystemIG=rs.IG
INNER JOIN [gnd_egfrm].[tblFormType] AS f ON f.ID=rf.FormTypeID
LEFT JOIN [gnd_egsys].[tblCaption] AS c ON c.ID=f.CaptionID
UNION ALL
SELECT r.ID,r.Description,s.ID,s.Description,N'Report',p.ID,c.Farsi,
       rr.GrantDisplay,rr.GrantEdit
FROM [gnd_egbse].[tblRole] AS r
INNER JOIN [gnd_egbse].[tblRoleDomain] AS rd ON rd.RoleID=r.ID
INNER JOIN [gnd_egbse].[tblRoleSystem] AS rs ON rs.RoleDomainIG=rd.IG
INNER JOIN [gnd_egsys].[tblSystem] AS s ON s.ID=rs.SystemID
INNER JOIN [gnd_egbse].[tblRoleSystemReport] AS rr ON rr.RoleSystemIG=rs.IG
INNER JOIN [gnd_egrpt].[tblReport] AS p ON p.ID=rr.ReportID
LEFT JOIN [gnd_egsys].[tblCaption] AS c ON c.ID=p.CaptionID;
```

## FINAL-U24

Show internal letters with their current workflow step and run status so completed and in-progress letters can be filtered.

- Domain: other/unclear; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbpm.tblProcessStep, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork, gnd_ofsct.tblInternalLetter.
- Execution: successful; nonempty bounded result.
- Semantics: Sequential workflow is human-authorized. Latest task is greatest Work.ID, consistent with ERP task ordering and the last-step helper, without timestamp ranking. FormTypeID=501 identifies InternalLetter.
- Relationships: Work.FormTypeID/FormID is the polymorphic logical link to InternalLetter.ID; CurrentProcessStepID and RunStatusTypeID join their workflow lookups.
- Result columns: InternalLetterID, Code, Date, Subject, CurrentProcessStepID, CurrentWorkflowStep, RunStatusTypeID, WorkflowRunStatus.

```sql
WITH CurrentWork AS (
 SELECT w.*,ROW_NUMBER() OVER(PARTITION BY w.FormID ORDER BY w.ID DESC) AS rn
 FROM [gnd_egwfm].[tblWork] AS w WHERE w.FormTypeID=501
)
SELECT l.ID AS InternalLetterID,l.Code,l.[Date],l.Subject,
       w.CurrentProcessStepID,ps.Name AS CurrentWorkflowStep,
       w.RunStatusTypeID,rs.Description AS WorkflowRunStatus
FROM [gnd_ofsct].[tblInternalLetter] AS l
LEFT JOIN CurrentWork AS w ON w.FormID=l.ID AND w.rn=1
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID
LEFT JOIN [gnd_egwfm].[tblRunStatusTypeL] AS rs ON rs.ID=w.RunStatusTypeID;
```

## FINAL-U25

List goods consumed more than once by the same requester, with the good identifier and description, requester, occurrence count, and total consumed quantity.

- Domain: assets/maintenance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_scinv.tblGoodConsume, gnd_scinv.tblGoodConsumeDetail, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: Duplicate key is GoodID plus RequesterEmployeeID, not description or asset. Each GoodConsumeDetail row is one occurrence. COUNT_BIG(*) counts occurrences; SUM(Qty) preserves recorded quantities.
- Relationships: GoodConsumeDetail.GoodConsumeID -> GoodConsume.ID; GoodConsumeDetail.GoodID -> Good.ID. Equipment and asset joins are not required.
- Result columns: GoodID, ItemDescription, RequesterEmployeeID, OccurrenceCount, TotalConsumedQuantity.

```sql
SELECT d.GoodID,g.Farsi AS ItemDescription,h.RequesterEmployeeID,
       COUNT_BIG(*) AS OccurrenceCount,SUM(d.Qty) AS TotalConsumedQuantity
FROM gnd_scinv.tblGoodConsume h
JOIN gnd_scinv.tblGoodConsumeDetail d ON d.GoodConsumeID=h.ID
JOIN gnd_spgod.tblGood g ON g.ID=d.GoodID
GROUP BY d.GoodID,g.Farsi,h.RequesterEmployeeID HAVING COUNT_BIG(*)>1;
```

## FINAL-U26

List maintenance work-order feedback records with a negative recorded work amount, including the work order, equipment, feedback date, and continuation flag.

- Domain: assets/maintenance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_amast.tblEquipment, gnd_amspt.tblFeedback, gnd_amspt.tblWorkOrder, gnd_egwfm.tblWorkRoute.
- Execution: successful; nonempty bounded result.
- Semantics: Human-approved continuation proof is EXISTS WorkRoute with feedback FormTypeID=1136748 and FormID=feedback.ID. Any current status is permitted; route existence proves Continue at least once.
- Relationships: Feedback.ID is also WorkOrder.ID by an explicit FK; EquipmentID joins Equipment.ID, and workflow continuation is inferred from a WorkRoute with the feedback form type and ID.
- Result columns: FeedbackID, WorkOrderID, WorkOrderCode, EquipmentID, EquipmentName, FeedbackDate, AmountOfWork, HasContinued.

```sql
SELECT f.ID AS FeedbackID,w.ID AS WorkOrderID,w.Code AS WorkOrderCode,
       f.EquipmentID,e.NameInEnglish AS EquipmentName,f.ReportDate AS FeedbackDate,
       f.AmountOfWork,
       CONVERT(bit,CASE WHEN EXISTS (
         SELECT 1 FROM [gnd_egwfm].[tblWorkRoute] AS wr
         WHERE wr.FormTypeID=1136748 AND wr.FormID=f.ID
       ) THEN 1 ELSE 0 END) AS HasContinued
FROM [gnd_amspt].[tblFeedback] AS f
INNER JOIN [gnd_amspt].[tblWorkOrder] AS w ON w.ID=f.ID
LEFT JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=f.EquipmentID
WHERE f.AmountOfWork<0;
```

## FINAL-U27

List cheque-collection accounting lines missing an analytic required by their account, including the collection document, journal line, account, and missing analytic form type.

- Domain: finance/treasury; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egfrm.tblFormEquivalency, gnd_fiaci.tblAccountDetail, gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail, gnd_fiaci.tblTransDetailDetail, gnd_firpd.tblInputChequeBankReceive.
- Execution: successful; empty bounded result.
- Semantics: Required analytic types come from AccountDetail. Supplied types are matched through FormEquivalency using the ERP spMonitorMissingDetailDetail NOT EXISTS pattern. Cheque-collection form type 12413 is explicitly mapped in ERP metadata and used by the auto-accounting caller. Source-document identity uses either the journal header or explicit journal-line reference. Each output row is one missing required type on one accounting line; no bank-account NULL shortcut.
- Relationships: TransDetail.TransID -> Trans.ID; TransDetailDetail.TransDetailIG -> TransDetail.IG. Required AccountDetail shares AccountID. Trans.FormTypeID/FormID or TransDetail.ReferenceFormTypeID/ReferenceFormID resolves polymorphically to InputChequeBankReceive at metadata form type 12413. FormEquivalency supplies analytic equivalence; no direct collection FK is claimed.
- Result columns: CollectionID, CollectionCode, CollectionDate, TransID, TransDetailIG, AccountID, MissingAnalyticFormTypeID.

```sql
WITH SourceLines AS (
 SELECT r.ID AS CollectionID,td.IG AS TransDetailIG
 FROM gnd_firpd.tblInputChequeBankReceive r
 JOIN gnd_fiaci.tblTransDetail td ON td.ReferenceFormTypeID=12413 AND td.ReferenceFormID=r.ID
 UNION
 SELECT r.ID,td.IG FROM gnd_firpd.tblInputChequeBankReceive r
 JOIN gnd_fiaci.tblTrans t ON t.FormTypeID=12413 AND t.FormID=r.ID
 JOIN gnd_fiaci.tblTransDetail td ON td.TransID=t.ID
)
SELECT r.ID AS CollectionID,r.Code AS CollectionCode,r.DoneDate AS CollectionDate,
 t.ID AS TransID,td.IG AS TransDetailIG,td.AccountID,ad.FormTypeID AS MissingAnalyticFormTypeID
FROM SourceLines s JOIN gnd_firpd.tblInputChequeBankReceive r ON r.ID=s.CollectionID
JOIN gnd_fiaci.tblTransDetail td ON td.IG=s.TransDetailIG
JOIN gnd_fiaci.tblTrans t ON t.ID=td.TransID
JOIN gnd_fiaci.tblAccountDetail ad ON ad.AccountID=td.AccountID
WHERE NOT EXISTS (
 SELECT 1 FROM gnd_fiaci.tblTransDetailDetail tdd
 JOIN gnd_egfrm.tblFormEquivalency fe ON fe.FormTypeID=tdd.FormTypeID
 WHERE fe.EquivalentFormTypeID=ad.FormTypeID AND tdd.TransDetailIG=td.IG
);
```

## FINAL-U28

List payment requests with their counterparty, destination description, and line descriptions.

- Domain: finance/treasury; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblContact, gnd_firpd.tblPayRequest, gnd_firpd.tblPayRequestDetail.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: PayRequestDetail.PayRequestID joins PayRequest.ID and PayRequest.PayContactID joins Contact.ID.
- Result columns: PayRequestID, Code, PayRequestDate, PayContactID, Counterparty, DestinationDescription, PayRequestLineID, Sequence, LineDescription, Amount.

```sql
SELECT r.ID AS PayRequestID,r.Code,r.PayRequestDate,
       r.PayContactID,c.Farsi AS Counterparty,r.DestinationDescription,
       d.ID AS PayRequestLineID,d.Sequence,d.Description AS LineDescription,d.Amount
FROM [gnd_firpd].[tblPayRequest] AS r
INNER JOIN [gnd_firpd].[tblPayRequestDetail] AS d ON d.PayRequestID=r.ID
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=r.PayContactID;
```

## FINAL-U29

List received-cheque records whose cheque number occurs more than once on the same receipt date, including each record identifier, cheque number, receipt date, and duplicate count.

- Domain: finance/treasury; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_firpd.tblInputCheque.
- Execution: successful; empty bounded result.
- Semantics: DoneDate is the receipt date, as confirmed by the ERP cheque report; ExecuteDate is the due date. Duplicate equality follows stored ChequeNumber and database collation, with no invented bank/account key or string normalization. Empty results are valid after data correction.
- Relationships: Single-table window count partitioned by ChequeNumber and DoneDate; no counterparty join is needed.
- Result columns: InputChequeID, ChequeNumber, ReceiptDate, DuplicateCount.

```sql
WITH Cheques AS (
    SELECT c.ID AS InputChequeID,c.ChequeNumber,c.DoneDate AS ReceiptDate,
           COUNT_BIG(*) OVER (PARTITION BY c.ChequeNumber,c.DoneDate) AS DuplicateCount
    FROM [gnd_firpd].[tblInputCheque] AS c
)
SELECT InputChequeID,ChequeNumber,ReceiptDate,DuplicateCount
FROM Cheques
WHERE DuplicateCount>1;
```

## FINAL-U30

For each loading record, show every scanned barcode's weight and the total scanned weight grouped by interweaving.

- Domain: imports/logistics; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_crsls.tblLoading, gnd_crsls.tblLoadingScannedBarcode, gnd_pjprj.tblInterweaving.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: LoadingScannedBarcode.LoadingID joins Loading.ID and InterweavingID joins Interweaving.ID; a window sum calculates the loading/interweaving total weight.
- Result columns: LoadingID, LoadingCode, DoneDate, ScannedBarcodeID, Barcode, Serial, InterweavingID, InterweavingCode, NetWeight, InterweavingTotalScannedWeight.

```sql
SELECT l.ID AS LoadingID,l.Code AS LoadingCode,l.DoneDate,
       b.IG AS ScannedBarcodeID,b.Barcode,b.Serial,b.InterweavingID,
       i.InterweavingCode,b.NetWeight,
       SUM(b.NetWeight) OVER(PARTITION BY l.ID,b.InterweavingID) AS InterweavingTotalScannedWeight
FROM [gnd_crsls].[tblLoading] AS l
INNER JOIN [gnd_crsls].[tblLoadingScannedBarcode] AS b ON b.LoadingID=l.ID
LEFT JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=b.InterweavingID;
```

## FINAL-U31

For the goods on @PurchaseRequestID, show stock by inventory in @PeriodSpecID and @CompanyID from the fiscal-period beginning through @EndDate: entered quantity, exited quantity, and remaining quantity. Include zero balances when recorded movements net to zero.

- Domain: inventory; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_fiaci.tblPeriodSpec, gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblExit, gnd_scinv.tblExitDetail, gnd_scinv.tblInventory, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail, gnd_spgod.tblGood, gnu_scinv.xblEnter, gnu_scinv.xblExit.
- Execution: successful; nonempty bounded result.
- Semantics: Stock/existence, not kardex. Purchase request selects distinct goods; its date is not a stock boundary. Mirrors spGoodExistance: Code IS NOT NULL, movement-date fiscal period, creator company, EnterQty minus ExitQty. An out-of-period or NULL end date uses the selected period end, as in the ERP procedure. Includes all inventories with eligible movements for the selected goods; no user-access predicate is copied. CreatorCompanyID requires physical gnu_scinv.xblEnter/xblExit dependencies outside the frozen retrieval corpus; they are retained honestly.
- Relationships: PurchaseRequestDetail.PurchaseRequestID -> PurchaseRequest.ID and GoodID -> Good.ID. vwEnter/vwExit explicitly join header/detail, fiscal period by DoneDate, and xbl header identity for company. Aggregation grain is GoodID + CredbInventoryID, not request detail.
- Result columns: GoodID, GoodCode, GoodName, InventoryID, InventoryName, EnteredQuantity, ExitedQuantity, RemainingQuantity.

```sql
WITH Period AS (
 SELECT p.ID,p.BeginDate,CASE WHEN @EndDate BETWEEN p.BeginDate AND p.EndDate
 THEN @EndDate ELSE p.EndDate END AS ThroughDate FROM gnd_fiaci.tblPeriodSpec p WHERE p.ID=@PeriodSpecID
), Requested AS (
 SELECT DISTINCT d.GoodID FROM gnd_scpch.tblPurchaseRequest r
 JOIN gnd_scpch.tblPurchaseRequestDetail d ON d.PurchaseRequestID=r.ID WHERE r.ID=@PurchaseRequestID
), Movements AS (
 SELECT e.CredbGoodID AS GoodID,e.CredbInventoryID AS InventoryID,
 ISNULL(e.Qty,0) AS EnterQty,CONVERT(decimal(38,6),0) AS ExitQty
 FROM gnd_scinv.vwEnter e JOIN Period p ON p.ID=e.PeriodSpecID
 WHERE e.Code IS NOT NULL AND e.CreatorCompanyID=@CompanyID AND e.DoneDate BETWEEN p.BeginDate AND p.ThroughDate
 UNION ALL
 SELECT e.CredbGoodID,e.CredbInventoryID,CONVERT(decimal(38,6),0),ISNULL(e.Qty,0)
 FROM gnd_scinv.vwExit e JOIN Period p ON p.ID=e.PeriodSpecID
 WHERE e.Code IS NOT NULL AND e.CreatorCompanyID=@CompanyID AND e.DoneDate BETWEEN p.BeginDate AND p.ThroughDate
)
SELECT m.GoodID,g.GoodCode,g.Farsi AS GoodName,m.InventoryID,i.Farsi AS InventoryName,
 SUM(m.EnterQty) AS EnteredQuantity,SUM(m.ExitQty) AS ExitedQuantity,
 SUM(m.EnterQty)-SUM(m.ExitQty) AS RemainingQuantity
FROM Movements m JOIN Requested r ON r.GoodID=m.GoodID
JOIN gnd_spgod.tblGood g ON g.ID=m.GoodID
LEFT JOIN gnd_scinv.tblInventory i ON i.ID=m.InventoryID
GROUP BY m.GoodID,g.GoodCode,g.Farsi,m.InventoryID,i.Farsi;
```

## FINAL-U32

List warehouse receipt lines with receipt date, warehouse, item code and description, quantity, amount, and supplier.

- Domain: inventory; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblContact, gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblInventory, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: One row per warehouse receipt line. Receipt date from Enter.DoneDate; quantity and amount from EnterDetail.Qty/AccValue; supplier from Enter.CredbRelatedToPersonID -> Contact.ID. Latest human decision supersedes invoice-line interpretation.
- Relationships: EnterDetail.EnterID -> Enter.ID; Enter.CredbInventoryID -> Inventory.ID; EnterDetail.CredbGoodID -> Good.ID; Enter.CredbRelatedToPersonID -> Contact.ID. Explicit human-approved receipt-line interpretation.
- Result columns: WarehouseReceiptID, ReceiptCode, ReceiptDate, InventoryID, InventoryName, ReceiptLineID, GoodID, GoodCode, GoodDescription, Qty, AccValue, SupplierID, SupplierName.

```sql
SELECT
    h.ID AS WarehouseReceiptID,
    h.Code AS ReceiptCode,
    h.DoneDate AS ReceiptDate,
    h.CredbInventoryID AS InventoryID,
    v.Farsi AS InventoryName,
    d.IG AS ReceiptLineID,
    g.ID AS GoodID,
    g.GoodCode,
    g.Farsi AS GoodDescription,
    d.Qty,
    d.AccValue,
    h.CredbRelatedToPersonID AS SupplierID,
    c.Farsi AS SupplierName
FROM gnd_scinv.tblEnter AS h
INNER JOIN gnd_scinv.tblEnterDetail AS d
    ON d.EnterID=h.ID
LEFT JOIN gnd_scinv.tblInventory AS v
    ON v.ID=h.CredbInventoryID
LEFT JOIN gnd_spgod.tblGood AS g
    ON g.ID=d.CredbGoodID
LEFT JOIN gnd_egbse.tblContact AS c
    ON c.ID=h.CredbRelatedToPersonID;
```

## FINAL-U33

List workflow tasks recorded as Done on @ReportDate, showing their task identifiers and completion timestamps.

- Domain: other/unclear; difficulty: Easy.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egwfm.tblWorkEnd.
- Execution: successful; nonempty bounded result.
- Semantics: DoneStatusTypeL ID=1 explicitly means Done. WorkEnd.CreateDate is written at the end action, and the ID primary key gives one stored end row per task. A half-open calendar-day filter includes every time on @ReportDate; the relative source date is parameterized. Unrequested originating-form identifiers and completion comments were removed during wording review. This is the normalized stored-Done information need, not a claim to reproduce every undocumented column or status of the original application report. Final human approval of the normalized case remains pending.
- Relationships: WorkEnd.ID is the task identifier and is both the primary key and an FK to Work.ID. No Work join is required when only the identifier and recorded completion time are requested.
- Result columns: WorkID, CompletedAt.

```sql
SELECT e.ID AS WorkID,e.CreateDate AS CompletedAt
FROM [gnd_egwfm].[tblWorkEnd] AS e
WHERE e.DoneStatusTypeID=1
  AND e.CreateDate>=@ReportDate
  AND e.CreateDate<DATEADD(day,1,@ReportDate);
```

## FINAL-U34

List all currently active workflow tasks still waiting for Continue or a response on the current assignment, with their assigned person and current step.

- Domain: other/unclear; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbpm.tblProcessStep, gnd_egbse.tblContact, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork.
- Execution: successful; nonempty bounded result.
- Semantics: Every stored Work with RunStatusTypeID IN (0,1) is a current running assignment, matching vwRunningWorks. Parallel rows are preserved. LastPlaceChangeDate is the current assignment arrival timestamp; CurrentUserID joins Contact directly and may remain NULL for role/position/team assignments.
- Relationships: Work's current user, process-step, and run-status IDs join Contact, ProcessStep, and RunStatusType; active assigned work excludes completed and information-only rows.
- Result columns: WorkID, FormTypeID, FormID, AssignedDate, CurrentUserID, CurrentAssignee, CurrentProcessStepID, CurrentStep, RunStatusTypeID, RunStatus.

```sql
SELECT w.ID AS WorkID,w.FormTypeID,w.FormID,w.LastPlaceChangeDate AS AssignedDate,
       w.CurrentUserID,c.Farsi AS CurrentAssignee,w.CurrentProcessStepID,
       ps.Name AS CurrentStep,w.RunStatusTypeID,rs.Description AS RunStatus
FROM [gnd_egwfm].[tblWork] AS w
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=w.CurrentUserID
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID
LEFT JOIN [gnd_egwfm].[tblRunStatusTypeL] AS rs ON rs.ID=w.RunStatusTypeID
WHERE w.RunStatusTypeID IN (0,1);
```

## FINAL-U35

List internal letters with their sent date, sender, recipients, and subject.

- Domain: other/unclear; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblContact, gnd_ofsct.tblInternalLetter, gnd_ofsct.tblRecEmpInternalLetter.
- Execution: successful; nonempty bounded result.
- Semantics: Human decision requests sent date only. InternalLetter.Date supplies SentDate; no time-of-day or workflow timestamp is inferred.
- Relationships: InternalLetter.SenderID joins Contact; RecEmpInternalLetter joins the letter and its PersonID joins Contact for recipients.
- Result columns: InternalLetterID, Code, SentDate, Subject, SenderID, Sender, RecipientID, Recipient, IsMainRecipient.

```sql
SELECT l.ID AS InternalLetterID,l.Code,l.[Date] AS SentDate,l.Subject,
       l.SenderID,s.Farsi AS Sender,r.PersonID AS RecipientID,rc.Farsi AS Recipient,
       r.IsMain AS IsMainRecipient
FROM [gnd_ofsct].[tblInternalLetter] AS l
LEFT JOIN [gnd_egbse].[tblContact] AS s ON s.ID=l.SenderID
LEFT JOIN [gnd_ofsct].[tblRecEmpInternalLetter] AS r ON r.InternalLetterID=l.ID
LEFT JOIN [gnd_egbse].[tblContact] AS rc ON rc.ID=r.PersonID;
```

## FINAL-U36

For each employee and payroll month, show employee code, holiday-day count, regular overtime hours, and Friday overtime hours.

- Domain: payroll; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime.
- Execution: successful; nonempty bounded result.
- Semantics: Human decision confirms Employee.EmployeeCode. SaatEzafeKarcdur and SaatJomehKaricdur store minutes; divide by 60.0 for Hours outputs. HolidayDayCount remains the stored day count.
- Relationships: WorkTime.EmployeeID and YearMonthID join Employee and YearMonth.
- Result columns: WorkTimeID, EmployeeID, EmployeeCode, YearMonthID, Year, MonthID, HolidayDayCount, RegularOvertimeHours, FridayOvertimeHours.

```sql
SELECT w.ID AS WorkTimeID,w.EmployeeID,e.EmployeeCode,w.YearMonthID,
       y.[Year],y.MonthID,w.TedadRuzTatilKariShift AS HolidayDayCount,
       w.SaatEzafeKarcdur / 60.0 AS RegularOvertimeHours,w.SaatJomehKaricdur / 60.0 AS FridayOvertimeHours
FROM [gnd_hrpyr].[tblWorkTime] AS w
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=w.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID;
```

## FINAL-U37

For each employee, show the monthly and annual remaining-leave balances used by the leave-request form for the Persian month and leave year containing @AsOfDate, using only finally approved leave usage.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblConvertDateTypeL, gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblSecurityConfig, gnd_egbse.tblUnit, gnd_egbse.tblUser, gnd_egbse.tblYearMonth, gnd_egsys.tblSystemConfig, gnd_egsys.tblSystemConfigDetail, gnd_hrcio.tblAttendenceRules, gnd_hrcio.tblCalendarHolidays, gnd_hrcio.tblCardLog, gnd_hrcio.tblEmployeeLeave, gnd_hrcio.tblEmployeeSavedLeave, gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShift, gnd_hrcio.tblShiftDetail, gnd_hrcio.tblShiftTemplate, gnd_hrcio.tblShiftTemplateDetail, gnd_hrcio.tblWorkShiftType, gnd_hrprs.tblContract, gnd_hrprs.tblEmployee, gnd_hrprs.tblEmployeeEmploymentStatus, gnd_hrprs.tblEmployeeIncentive, gnu_hrcio.xblEmployeeShift.
- Execution: successful; nonempty bounded result.
- Semantics: SELECT-only transcription of the authoritative leave-request and annual-cap calculations. Approved daily leave takes precedence at employee/date grain, including zero daily consumption; hourly contribution on that date is suppressed. All otherwise-valid clock events across CardCode values form one employee/day stream. The existing fnLeaveCalc effective-clock ordering and pairing are retained; CardCode neither splits the pivot nor selects a result. Configuration, employment proration, holiday adjustments, carry-forward and annual-cap incentives are retained. Both human clarifications are implemented; bounded execution and private regressions passed.
- Relationships: Calendar employee/day consumption feeds the original request and annual-cap period calculations. Leave, shifts, clocks, employment status, attendance rules, saved leave and configuration follow the inspected source joins; required view dependencies are included explicitly.
- Result columns: EmployeeID, MonthlyRemainingLeaveMinutes, AnnualRemainingLeaveMinutes.

```sql
WITH PeriodContext AS (
 SELECT ar.CalcLeaveStartDate AS LeaveYearStart,ar.CalcLeaveEndDate AS LeaveYearEnd,
 ar.YearID,ym.Year AS LeaveYear,a.ParsDate,
 (SELECT ChrisDate FROM gnd_egbse.tblConvertDateTypeL WHERE ParsDate=LEFT(a.ParsDate,7)+'/01') AS MonthStart,
 (SELECT MAX(ChrisDate) FROM gnd_egbse.tblConvertDateTypeL WHERE [Month]=a.[Month] AND ParsYear=a.ParsYear) AS MonthEnd,
 ISNULL((SELECT scd.ParameterValue FROM gnd_egsys.tblSystemConfig sc
 JOIN gnd_egsys.tblSystemConfigDetail scd ON scd.SystemConfigID=sc.ID
 WHERE sc.SystemID=90 AND sc.ParameterName='PermittedLeaveHourInYear' AND scd.CompanyID=1 AND scd.DepartmentID IS NULL),0) AS ConfigValue
 FROM gnd_hrcio.tblAttendenceRules ar
 JOIN gnd_egbse.tblYearMonth ym ON ym.ID=ar.YearID
 CROSS JOIN gnd_egbse.tblConvertDateTypeL a
 WHERE @AsOfDate BETWEEN ar.CalcLeaveStartDate AND ar.CalcLeaveEndDate AND a.ChrisDate=CONVERT(date,@AsOfDate)
), Periods AS (
 SELECT p.PeriodOption,CASE WHEN p.PeriodOption=2 THEN c.MonthStart ELSE c.LeaveYearStart END AS FromDate,
 CASE WHEN p.PeriodOption=2 THEN c.MonthEnd ELSE c.LeaveYearEnd END AS ToDate,
 c.LeaveYear,c.ParsDate,
 CAST(CASE WHEN p.PeriodOption=3 THEN CASE c.ConfigValue WHEN 0 THEN 8 WHEN 2 THEN 8 ELSE 7.33 END
 ELSE CASE c.ConfigValue WHEN 0 THEN 8 WHEN 3 THEN 7.33 ELSE 8 END END AS float) AS Value,
 CAST(CASE WHEN p.PeriodOption=3 THEN CASE c.ConfigValue WHEN 2 THEN 24 WHEN 3 THEN 26 ELSE 30 END
 ELSE CASE c.ConfigValue WHEN 0 THEN 30 WHEN 3 THEN 26 ELSE 18.3 END END AS int) AS Rouz
 FROM PeriodContext c CROSS JOIN (VALUES(1),(2),(3)) p(PeriodOption)
), EmploymentStart AS (
 SELECT EmployeeID,MAX(FromDate) AS RequestStart,
 MAX(CASE WHEN EmploymentTypeID=1 THEN FromDate END) AS CapStart
 FROM gnd_hrprs.tblEmployeeEmploymentStatus WHERE IsClearing=0 GROUP BY EmployeeID
), EmployeeScope AS (
 SELECT e.ID AS EmployeeID,p.PeriodOption,p.FromDate,p.ToDate,p.Value,p.Rouz,p.LeaveYear,p.ParsDate,
 CASE WHEN p.PeriodOption=3 THEN es.CapStart ELSE es.RequestStart END AS EmploymentFromDate
 FROM gnd_hrprs.tblEmployee e CROSS JOIN Periods p
 LEFT JOIN EmploymentStart es ON es.EmployeeID=e.ID WHERE ISNULL(e.IsLeaved,0)=0
), UsageInputs AS (
 SELECT s.EmployeeID,s.PeriodOption,cd.ChrisDate,
 CAST(MIN(cl.ClockTime) AS time) AS BeginTime,CAST(MAX(cl.ClockTime) AS time) AS EndTime
 FROM EmployeeScope s JOIN gnd_hrcio.tblEmployeeLeave l ON l.EmployeeID=s.EmployeeID AND l.Code=99
 AND l.FromDate BETWEEN CASE WHEN s.EmploymentFromDate>s.FromDate THEN s.EmploymentFromDate ELSE s.FromDate END AND s.ToDate
 JOIN gnd_egbse.tblConvertDateTypeL cd ON cd.ChrisDate BETWEEN l.FromDate AND l.ToDate AND cd.ChrisDate BETWEEN s.FromDate AND s.ToDate
 LEFT JOIN gnd_hrcio.tblCardLog cl ON cl.EmployeeID=s.EmployeeID AND cl.DayDate=cd.ChrisDate
 AND (s.PeriodOption<>3 OR ISNULL(cl.IsDisable,0)=0)
 GROUP BY s.EmployeeID,s.PeriodOption,cd.ChrisDate
),
LeaveConsumptionByDay AS (
 SELECT k.EmployeeID,k.PeriodOption,k.ChrisDate,
 ISNULL(CASE WHEN EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave dl
 WHERE dl.EmployeeID=k.EmployeeID AND dl.DurationTypeID=2 AND dl.Code=99
 AND k.ChrisDate BETWEEN dl.FromDate AND dl.ToDate)
 THEN ISNULL((SELECT DISTINCT ISNULL(CAST(DATEDIFF(MINUTE,'00:00:00',SD.LeaveTime) AS int),0)
 FROM    gnd_hrcio.tblEmployeeLeave el INNER JOIN gnd_hrcio.tblEmployeeShift ES ON ES.EmployeeID=el.EmployeeID
INNER JOIN gnd_hrcio.tblShift S ON s.ID=ES.ShiftID
INNER JOIN gnd_hrcio.vwEmployeeShiftCompleteReport SD ON SD.ShiftID = S.ID AND sd.employeeid=el.EmployeeID AND sd.date=k.ChrisDate
LEFT JOIN gnd_hrcio.tblCalendarHolidays c ON c.HolidayDate=sd.Date
WHERE   el.EmployeeID = k.EmployeeID AND k.ChrisDate=SD.Date AND ISNULL (el.Code,0)=99
AND k.ChrisDate BETWEEN el.FromDate AND el.ToDate AND el.LeaveTypeID=1
AND (sd.IsOff=0 OR (sd.IsOff=1 AND c.HolidayTypeID=1))
AND ES.FromDate=(SELECT MAX(FromDate) FROM gnd_hrcio.tblEmployeeShift WHERE EmployeeID=el.EmployeeID AND FromDate<=k.ChrisDate) AND el.DurationTypeID=2),0)
 WHEN EXISTS(SELECT 1 FROM    gnd_hrcio.tblEmployeeLeave el INNER JOIN gnd_hrcio.tblEmployeeShift ES ON ES.EmployeeID=el.EmployeeID
INNER JOIN gnd_hrcio.tblShift S ON s.ID=ES.ShiftID
INNER JOIN gnd_hrcio.vwEmployeeShiftCompleteReport SD ON SD.ShiftID = S.ID AND sd.employeeid=el.EmployeeID AND sd.date=k.ChrisDate
LEFT JOIN gnd_hrcio.tblCalendarHolidays c ON c.HolidayDate=sd.Date
WHERE   el.EmployeeID = k.EmployeeID AND k.ChrisDate=SD.Date AND ISNULL (el.Code,0)=99
AND k.ChrisDate BETWEEN el.FromDate AND el.ToDate AND el.LeaveTypeID=1
AND (sd.IsOff=0 OR (sd.IsOff=1 AND c.HolidayTypeID=1))
AND ES.FromDate=(SELECT MAX(FromDate) FROM gnd_hrcio.tblEmployeeShift WHERE EmployeeID=el.EmployeeID AND FromDate<=k.ChrisDate) AND el.DurationTypeID=1)
 THEN CASE WHEN cx.ChoiceCount>1 THEN 1/(cx.ChoiceCount-cx.ChoiceCount)
 WHEN ISNULL((SELECT scd.ParameterValue FROM gnd_egsys.tblSystemConfig sc JOIN gnd_egsys.tblSystemConfigDetail scd ON scd.SystemConfigID=sc.ID WHERE sc.SystemID=90 AND sc.ParameterName='CalcReastTimeInLeave' AND scd.CompanyID=1 AND scd.DepartmentID IS NULL),0)=1 AND rx.ChoiceCount>1 THEN 1/(rx.ChoiceCount-rx.ChoiceCount)
 ELSE ISNULL(( select
CASE
WHEN (ha.MaxEnd) > SD.CheckOutTime
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE, SD.CheckOutTime,ha.MaxEnd)))
WHEN ((ha.MaxEnd) = SD.CheckOutTime)
AND ((ha.MaxBegin)< k.EndTime)
AND k.EndTime<SD.CheckOutTime
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,ha.MaxBegin, k.EndTime)))
WHEN ((ha.MinEnd) > k.BeginTime)
AND ((ha.MinBegin)<k.BeginTime)
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))-
((DATEDIFF(MINUTE,k.BeginTime,ha.MinEnd)))
WHEN  MIN(el.BeginTime) BETWEEN t.Exit1 AND t.Enter2 AND MIN(el.EndTime)=t.Enter2
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit1,MIN(el.BeginTime))))
WHEN  MIN(el.BeginTime) BETWEEN t.Exit1 AND t.Enter2 AND MIN(el.EndTime)<t.Enter2
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit1,MIN(el.BeginTime))))+ ((DATEDIFF(MINUTE,MIN(el.EndTime),t.Enter2)))
WHEN  MIN(el.BeginTime) BETWEEN t.Exit1 AND t.Enter2 AND MIN(el.EndTime)>t.Enter2
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit1,MIN(el.BeginTime))))- ((DATEDIFF(MINUTE,t.Enter2,MIN(el.EndTime))))
WHEN  MIN(el.BeginTime) < t.Exit1 AND MIN(el.EndTime)=t.Enter2
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MIN(el.BeginTime),t.Exit1)))
WHEN  MIN(el.BeginTime) < t.Exit1 AND MIN(el.EndTime)<t.Enter2 AND MIN(el.EndTime)>t.Exit1
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MIN(el.BeginTime),t.Exit1)))+ ((DATEDIFF(MINUTE,MIN(el.EndTime),t.Enter2)))
WHEN  MIN(el.BeginTime) < t.Exit1 AND MIN(el.EndTime)>t.Enter2
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MIN(el.BeginTime),t.Exit1)))- ((DATEDIFF(MINUTE,t.Enter2,MIN(el.EndTime))))
WHEN t.Exit1 BETWEEN MIN(el.BeginTime) AND MIN(el.EndTime) AND t.Enter2 BETWEEN MIN(el.BeginTime) AND MIN(el.EndTime)
THEN (DATEDIFF(MINUTE,t.Exit1,t.Enter2))
WHEN  max(el.BeginTime) BETWEEN t.Exit2 AND t.Enter3 AND MAX(el.EndTime)=t.Enter3
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit2,MAX(el.BeginTime))))
WHEN  MAX(el.BeginTime) BETWEEN t.Exit2 AND t.Enter3 AND MAX(el.EndTime)<t.Enter3
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit2,max(el.BeginTime))))+ ((DATEDIFF(MINUTE,max(el.EndTime),t.Enter3)))
WHEN  max(el.BeginTime) BETWEEN t.Exit2 AND t.Enter3 AND max(el.EndTime)>t.Enter3
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))+ ((DATEDIFF(MINUTE,t.Exit2,max(el.BeginTime))))- ((DATEDIFF(MINUTE,t.Enter3,MAX(el.EndTime))))
WHEN  MAX(el.BeginTime) < t.Exit2 AND MAX(el.EndTime)=t.Enter3
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MAX(el.BeginTime),t.Exit2)))
WHEN  MAX(el.BeginTime) < t.Exit2 AND MAX(el.EndTime)<t.Enter3 AND max(el.EndTime)>t.Exit1
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MAX(el.BeginTime),t.Exit2)))+ ((DATEDIFF(MINUTE,MAX(el.EndTime),t.Enter3)))
WHEN  MAX(el.BeginTime) < t.Exit2 AND MAX(el.EndTime)>t.Enter3
THEN  (SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))- ((DATEDIFF(MINUTE,MAX(el.BeginTime),t.Exit2)))- ((DATEDIFF(MINUTE,t.Enter3,max(el.EndTime))))
WHEN t.Exit2 BETWEEN max(el.BeginTime) AND max(el.EndTime) AND t.Enter3 BETWEEN max(el.BeginTime) AND max(el.EndTime)
THEN (DATEDIFF(MINUTE,t.Exit2,t.Enter3))
ELSE
(SUM(DATEDIFF(MINUTE,el.begintime, el.endtime)))
END
FROM    gnd_hrcio.tblEmployeeLeave el
INNER JOIN gnd_hrcio.tblEmployeeShift ES ON ES.EmployeeID=el.EmployeeID
INNER JOIN gnd_hrcio.tblShift S ON s.ID=ES.ShiftID
INNER JOIN gnd_hrcio.tblShiftDetail SD ON SD.ShiftID = S.ID
LEFT JOIN (SELECT EmployeeID,DayDate,
 CONVERT(nvarchar(20),[2]) AS Exit1,CONVERT(nvarchar(20),[3]) AS Enter2,
 CONVERT(nvarchar(20),[4]) AS Exit2,CONVERT(nvarchar(20),[5]) AS Enter3
 FROM (SELECT EmployeeID,DayDate,ISNULL(AlternateClockTime,ClockTime) AS ClockTime,
 ROW_NUMBER() OVER(PARTITION BY EmployeeID,DayDate ORDER BY ISNULL(AlternateClockTime,ClockTime)) AS turn
 FROM gnd_hrcio.tblCardLog WHERE EmployeeID=k.EmployeeID AND DayDate=k.ChrisDate) ccc
 PIVOT(MAX(ClockTime) FOR turn IN ([1],[2],[3],[4],[5],[6],[7],[8],[9],[10])) AS pv
) t ON t.EmployeeID=el.EmployeeID
WHERE   el.EmployeeID = k.EmployeeID AND el.LeaveTypeID=1
AND k.ChrisDate BETWEEN el.FromDate   AND    el.ToDate
AND el.DurationTypeID=1 AND ISNULL (el.Code,0)=99
AND k.ChrisDate=SD.Date AND ES.FromDate=(SELECT MAX(FromDate) FROM gnd_hrcio.tblEmployeeShift WHERE EmployeeID=el.EmployeeID AND FromDate<=k.ChrisDate)
GROUP BY el.FromDate,SD.CheckOutTime,t.Enter2,t.Exit1,t.Exit2,t.Enter3 ),0)
 + (CASE WHEN  cx.DaySueTimeRetrieve=1 AND k.BeginTime<=cx.EntranceFloatingCTime AND k.BeginTime>cx.TBeginTime AND k.EndTime<=cx.TEndTime
AND not EXISTS (SELECT 1 FROM gnd_hrcio.tblEmployeeLeave WHERE EmployeeID=k.EmployeeID AND LeaveTypeID=1 AND DurationTypeID=1 AND Code=99 AND BeginTime=cx.TBeginTime AND EndTime=k.BeginTime AND FromDate=k.ChrisDate)
AND EXISTS (SELECT 1 FROM gnd_hrcio.tblEmployeeLeave WHERE EmployeeID=k.EmployeeID AND LeaveTypeID=1 AND DurationTypeID=1 AND Code=99 AND EndTime>=cx.TEndTime AND FromDate=k.ChrisDate)
THEN CAST((CASE WHEN ISNULL(DATEDIFF(MINUTE,cx.TBeginTime,k.BeginTime),-1)<0 THEN 0 ELSE DATEDIFF(MINUTE,cx.TBeginTime,k.BeginTime) END) AS INT)
ELSE 0 END )
-(CASE
WHEN  (ISNULL ((SELECT scd.ParameterValue FROM gnd_egsys.tblSystemConfig sc JOIN gnd_egsys.tblSystemConfigDetail scd ON scd.SystemConfigID=sc.ID WHERE sc.SystemID=90 AND sc.ParameterName='CalcReastTimeInLeave' AND scd.CompanyID=1 AND scd.DepartmentID IS NULL),0) =1)
then case when
EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave el
WHERE el.EmployeeID=k.EmployeeID AND el.LeaveTypeID=1 AND el.DurationTypeID=1 AND el.Code=99  AND el.FromDate=k.ChrisDate
AND el.BeginTime BETWEEN rx.RestTimeStart AND rx.RestTimeEnd  )
THEN CAST( (DATEDIFF(MINUTE,(SELECT el.BeginTime FROM gnd_hrcio.tblEmployeeLeave el
WHERE el.EmployeeID=k.EmployeeID AND el.LeaveTypeID=1 AND el.DurationTypeID=1 AND el.Code=99  AND el.FromDate=k.ChrisDate
AND el.BeginTime BETWEEN rx.RestTimeStart AND rx.RestTimeEnd  ),rx.RestTimeEnd)) AS INT)
WHEN
EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave el
WHERE el.EmployeeID=k.EmployeeID AND el.LeaveTypeID=1 AND el.DurationTypeID=1 AND el.Code=99  AND el.FromDate=k.ChrisDate
AND el.EndTime BETWEEN rx.RestTimeStart AND rx.RestTimeEnd  )
THEN CAST( (DATEDIFF(MINUTE,rx.RestTimeStart,(SELECT el.EndTime FROM gnd_hrcio.tblEmployeeLeave el
WHERE el.EmployeeID=k.EmployeeID AND el.LeaveTypeID=1 AND el.DurationTypeID=1 AND el.Code=99  AND el.FromDate=k.ChrisDate
AND el.EndTime BETWEEN rx.RestTimeStart AND rx.RestTimeEnd  ))) AS INT)
when
EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave el
WHERE el.EmployeeID=k.EmployeeID AND el.LeaveTypeID=1 AND el.DurationTypeID=1 AND el.Code=99  AND el.FromDate=k.ChrisDate
AND el.EndTime >= rx.RestTimeEnd  and el.BeginTime <= rx.RestTimeStart)
THEN CAST( (DATEDIFF(MINUTE,rx.RestTimeStart,rx.RestTimeEnd)) AS INT)
else 0
END
else 0
END )
 END
 ELSE 0 END,0) AS FinalConsumptionMinutes
 FROM UsageInputs k
OUTER APPLY (SELECT MAX(EndTime) AS MaxEnd,MIN(EndTime) AS MinEnd,MAX(BeginTime) AS MaxBegin,MIN(BeginTime) AS MinBegin
 FROM gnd_hrcio.tblEmployeeLeave WHERE EmployeeID=k.EmployeeID AND k.ChrisDate BETWEEN FromDate AND ToDate
 AND DurationTypeID=1 AND Code=99 AND LeaveTypeID=1) ha

OUTER APPLY (SELECT COUNT(*) AS ChoiceCount,MAX(v.TBeginTime) AS TBeginTime,MAX(v.TEndTime) AS TEndTime,MAX(v.EntranceFloatingCTime) AS EntranceFloatingCTime,MAX(v.DaySueTimeRetrieve) AS DaySueTimeRetrieve FROM (SELECT DISTINCT SD.CheckInTime AS TBeginTime,SD.CheckOutTime AS TEndTime,SD.EntranceFloatingTime AS EntranceFloatingCTime,CAST(SR.DaySueTimeRetrieve AS int) AS DaySueTimeRetrieve FROM gnd_hrprs.tblContract SR
INNER JOIN gnd_hrcio.vwEmployeeShiftCompleteReport  ES ON ES.EmployeeID = SR.EmployeeID AND es.Date=k.ChrisDate
INNER JOIN gnd_hrcio.tblShiftDetail SD ON SD.ShiftID = es.ShiftID
INNER JOIN gnd_hrcio.tblShiftTemplate TS ON TS.ID = es.ShiftID
LEFT JOIN gnd_hrcio.tblCalendarHolidays CH ON SD.Date=CH.HolidayDate AND es.ShiftID=ch.ShiftTemplateID
WHERE SR.EmployeeID=k.EmployeeID
AND k.ChrisDate >= (SELECT FromDate FROM gnd_egbse.tblYearMonth WHERE ID=SR.FromYearMonthID)
AND ES.FromDate=(SELECT MAX(FromDate) FROM gnd_hrcio.tblEmployeeShift WHERE EmployeeID=SR.EmployeeID AND FromDate<=k.ChrisDate)) v) cx
OUTER APPLY (SELECT COUNT(*) AS ChoiceCount,MAX(v.RestTimeStart) AS RestTimeStart,MAX(v.RestTimeEnd) AS RestTimeEnd FROM (SELECT DISTINCT r.RestTimeStart,r.RestTimeEnd FROM gnd_hrcio.tblAttendenceRules r INNER JOIN gnd_egbse.tblYearMonth y ON y.ID=r.YearID WHERE k.ChrisDate BETWEEN y.FromDate AND y.ToDate) v) rx
), LeaveConsumption AS (
 SELECT EmployeeID,PeriodOption,-SUM(FinalConsumptionMinutes) AS Amount
 FROM LeaveConsumptionByDay GROUP BY EmployeeID,PeriodOption
), ShiftSource AS (
 SELECT 0 AS IsCap,EmployeeID,ShiftID,FromDate FROM gnd_hrcio.uvEmployeeShift
 UNION ALL SELECT 1,EmployeeID,ShiftID,FromDate FROM gnd_hrcio.tblEmployeeShift
), HolidayRows AS (
 SELECT s.EmployeeID,s.PeriodOption,sd.Date,sd.LeaveTime,
 SUM(CASE WHEN ch.HolidayTypeID=1 AND ch.HolidayDate BETWEEN l.FromDate AND l.ToDate THEN DATEDIFF(MINUTE,'00:00:00',sd.LeaveTime) ELSE 0 END) AS Type1Minutes,
 SUM(CASE WHEN ch.HolidayTypeID=2 AND ch.HolidayDate BETWEEN l.FromDate AND l.ToDate THEN DATEDIFF(MINUTE,'00:00:00',sd.LeaveTime) ELSE 0 END) AS Type2Minutes,
 MAX(bridge.FourDayCandidate) AS FourDayCandidate
 FROM EmployeeScope s JOIN gnd_hrcio.tblEmployeeLeave l ON l.EmployeeID=s.EmployeeID
 AND l.DurationTypeID=2 AND l.LeaveTypeID=1 AND l.Code=99
 AND l.FromDate BETWEEN CASE WHEN s.EmploymentFromDate>s.FromDate THEN s.EmploymentFromDate ELSE s.FromDate END AND s.ToDate
 JOIN ShiftSource es ON es.EmployeeID=s.EmployeeID AND es.IsCap=CASE WHEN s.PeriodOption=3 THEN 1 ELSE 0 END
 JOIN gnd_hrcio.tblShiftDetail sd ON sd.ShiftID=es.ShiftID AND sd.IsOff=1
 JOIN gnd_hrcio.tblCalendarHolidays ch ON ch.HolidayDate=sd.Date
 AND (s.PeriodOption<>3 OR ch.ShiftTemplateID=sd.ShiftID)
 CROSS APPLY ( SELECT CASE WHEN ch.HolidayTypeID=1 AND ch.HolidayDate BETWEEN s.FromDate AND s.ToDate AND
 (ch.HolidayDate BETWEEN l.FromDate AND l.ToDate OR (
 EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave prev WHERE prev.EmployeeID=s.EmployeeID AND prev.DurationTypeID=2 AND prev.LeaveTypeID=1 AND prev.Code=99
 AND prev.ToDate=DATEADD(DAY,-1,ch.HolidayDate) AND DATEPART(W,prev.ToDate)=5 AND prev.FromDate BETWEEN s.FromDate AND s.ToDate)
 AND EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeLeave nex WHERE nex.EmployeeID=s.EmployeeID AND nex.DurationTypeID=2 AND nex.LeaveTypeID=1 AND nex.Code=99
 AND nex.FromDate=DATEADD(DAY,1,ch.HolidayDate) AND DATEPART(W,nex.FromDate)=7 AND nex.FromDate BETWEEN s.FromDate AND s.ToDate)))
 THEN 1 ELSE 0 END AS FourDayCandidate) bridge
 WHERE es.FromDate=(SELECT MAX(mx.FromDate) FROM ShiftSource mx WHERE mx.EmployeeID=s.EmployeeID AND mx.IsCap=es.IsCap AND mx.FromDate<=sd.Date)
 GROUP BY s.EmployeeID,s.PeriodOption,sd.Date,sd.LeaveTime
), HolidayRanked AS (
 SELECT EmployeeID,PeriodOption,LeaveTime,Type1Minutes,Type2Minutes,FourDayCandidate,
 SUM(FourDayCandidate) OVER(PARTITION BY EmployeeID,PeriodOption ORDER BY EmployeeID ROWS UNBOUNDED PRECEDING) AS CandidateNumber
 FROM HolidayRows
), HolidayAdjustment AS (
 SELECT EmployeeID,PeriodOption,SUM(Type1Minutes+Type2Minutes-
 CASE WHEN FourDayCandidate=1 AND CandidateNumber<=4 THEN ISNULL(DATEDIFF(MINUTE,'00:00:00',LeaveTime),0) ELSE 0 END) AS Amount
 FROM HolidayRanked GROUP BY EmployeeID,PeriodOption
), WeeklySchedule AS (
 SELECT s.EmployeeID,s.PeriodOption,s.FromDate,s.ToDate,s.EmploymentFromDate,s.Value,s.Rouz,s.ParsDate,
 SUM(DATEDIFF(MINUTE,st.CheckInTime,st.CheckOutTime))/60 AS GrossHours,
 SUM(DATEDIFF(MINUTE,st.CheckInTime,st.CheckOutTime)-DATEDIFF(MINUTE,'00:00:00',st.RestTime))/60 AS NetHours
 FROM EmployeeScope s JOIN ShiftSource es ON es.EmployeeID=s.EmployeeID AND es.IsCap=CASE WHEN s.PeriodOption=3 THEN 1 ELSE 0 END
 JOIN gnd_hrcio.tblShiftTemplateDetail st ON st.ShiftTemplateID=es.ShiftID AND ISNULL(st.IsOff,0)=0
 WHERE es.FromDate=(SELECT MAX(mx.FromDate) FROM ShiftSource mx WHERE mx.EmployeeID=s.EmployeeID AND mx.IsCap=es.IsCap AND mx.FromDate<=@AsOfDate)
 GROUP BY s.EmployeeID,s.PeriodOption,s.FromDate,s.ToDate,s.EmploymentFromDate,s.Value,s.Rouz,s.ParsDate
), EmploymentEnd AS (
 SELECT w.EmployeeID,w.PeriodOption,w.FromDate,w.ToDate,w.EmploymentFromDate,w.Value,w.Rouz,w.ParsDate,w.GrossHours,w.NetHours,
 ISNULL((SELECT st.ToDate FROM gnd_hrprs.tblEmployeeEmploymentStatus st
 WHERE st.EmployeeID=w.EmployeeID AND st.IsClearing=0 AND st.FromDate=w.EmploymentFromDate AND (w.PeriodOption<>3 OR st.EmploymentTypeID=1)),
 (SELECT yt.ToDate FROM gnd_hrprs.tblContract c JOIN gnd_egbse.tblYearMonth yf ON yf.ID=c.FromYearMonthID
 JOIN gnd_egbse.tblYearMonth yt ON yt.ID=c.ToYearMonthID
 WHERE c.EmployeeID=w.EmployeeID AND c.ID=(SELECT MAX(mc.ID) FROM gnd_hrprs.tblContract mc WHERE mc.EmployeeID=w.EmployeeID
 AND (w.PeriodOption<>3 OR w.GrossHours<44 OR w.GrossHours IS NULL OR mc.EmploymentTypeID=1))
 AND (yf.FromDate BETWEEN w.FromDate AND w.ToDate OR yt.ToDate BETWEEN w.FromDate AND w.ToDate))) AS EmploymentToDate
 FROM WeeklySchedule w
), Proration AS (
 SELECT EmployeeID,PeriodOption,Value,Rouz,ParsDate,
 CASE WHEN GrossHours>=44 THEN 1 ELSE NetHours END *
 (DATEDIFF(DAY,CASE WHEN EmploymentFromDate>FromDate THEN EmploymentFromDate ELSE FromDate END,
 CASE WHEN EmploymentToDate BETWEEN FromDate AND ToDate THEN EmploymentToDate ELSE ToDate END)+1)
 /CASE WHEN GrossHours>=44 THEN 1 ELSE 44 END AS Days
 FROM EmploymentEnd
), Entitlement AS (
 SELECT EmployeeID,PeriodOption,ISNULL(CEILING(CAST(ROUND(Value*60,0) AS int)*Rouz*
 (CAST(CASE WHEN PeriodOption=2 THEN CASE WHEN Days>30 THEN 30 WHEN SUBSTRING(ParsDate,6,2)='12' AND Days=29 THEN 30 ELSE Days END
 ELSE CASE WHEN Days>365 THEN 365 ELSE Days END END AS decimal(15,4))/CASE WHEN PeriodOption=3 THEN 365 ELSE 360 END)),0) AS Amount
 FROM Proration
), CarryForward AS (
 SELECT s.EmployeeID,s.PeriodOption,ISNULL((SELECT sl.TransferToNextYearcdur FROM gnd_hrcio.tblEmployeeSavedLeave sl
 WHERE sl.EmployeeID=s.EmployeeID AND sl.YearID=(SELECT y.ID FROM gnd_egbse.tblYearMonth y
 WHERE y.Year=s.LeaveYear-1 AND ((s.PeriodOption=1 AND ISNULL(y.MotherID,0)=0)
 OR (s.PeriodOption=3 AND y.MonthID IS NULL AND y.SeasonID IS NULL AND y.FromDate IS NOT NULL)))),0) AS Amount
 FROM EmployeeScope s WHERE s.PeriodOption IN (1,3)
), Incentive AS (
 SELECT s.EmployeeID,s.PeriodOption,ISNULL(SUM(i.Days),0)*CAST(s.Value AS int)*60 AS Amount
 FROM EmployeeScope s JOIN gnd_hrprs.tblEmployeeIncentive i ON i.EmployeeID=s.EmployeeID AND i.GrantedDate BETWEEN s.FromDate AND s.ToDate
 WHERE s.PeriodOption=3 GROUP BY s.EmployeeID,s.PeriodOption,s.Value
), BalanceComponents AS (
 SELECT EmployeeID,PeriodOption,Amount FROM LeaveConsumption
 UNION ALL SELECT EmployeeID,PeriodOption,Amount FROM HolidayAdjustment
 UNION ALL SELECT EmployeeID,PeriodOption,Amount FROM Entitlement
 UNION ALL SELECT EmployeeID,PeriodOption,Amount FROM CarryForward
 UNION ALL SELECT EmployeeID,PeriodOption,Amount FROM Incentive
), EmployeeBalances AS (
 SELECT EmployeeID,
 CAST(SUM(CASE WHEN PeriodOption=1 THEN Amount ELSE 0 END) AS int) AS AnnualBalance,
 CAST(SUM(CASE WHEN PeriodOption=2 THEN Amount ELSE 0 END) AS int) AS MonthlyBalance,
 CAST(SUM(CASE WHEN PeriodOption=3 THEN Amount ELSE 0 END) AS int) AS CapBalance
 FROM BalanceComponents GROUP BY EmployeeID
)
SELECT e.ID AS EmployeeID,
 CASE WHEN ISNULL(b.CapBalance,0)>0 AND b.CapBalance<ISNULL(b.MonthlyBalance,0) THEN b.CapBalance
 WHEN b.CapBalance<0 THEN 0 ELSE ISNULL(b.MonthlyBalance,0) END AS MonthlyRemainingLeaveMinutes,
 ISNULL(b.AnnualBalance,0) AS AnnualRemainingLeaveMinutes
FROM gnd_hrprs.tblEmployee e LEFT JOIN EmployeeBalances b ON b.EmployeeID=e.ID
WHERE ISNULL(e.IsLeaved,0)=0;
```

## FINAL-U38

Show the recorded departed employees for HR evaluation @EvaluationID covering three payroll months, with their hire and termination dates.

- Domain: personnel/attendance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrapr.tblManagerHRFeedback, gnd_hrapr.tblManagerHRFeedbackLeavedEmployeeDetail.
- Execution: successful; empty bounded result.
- Semantics: One row per recorded departed-employee detail in the selected HR evaluation, restricted to its stored payroll-period boundaries. @EvaluationID must identify an evaluation covering three payroll months. Hire and termination dates are the recorded detail fields populated by the ERP HR-evaluation procedure. The independently requested active-employee score recalculation is outside this atomic departed-employee reporting requirement. No live shift attribution is invented.
- Relationships: LeavedEmployeeDetail.ManagerHRFeedbackID -> ManagerHRFeedback.ID; parent FromYearMonthID/ToYearMonthID -> YearMonth.ID. Detail dates filtered to that period.
- Result columns: EvaluationID, UnitID, EmployeeID, HireDate, TerminationDate.

```sql
SELECT m.ID AS EvaluationID,m.UnitID,d.EmployeeID,
       d.EmploymentDate AS HireDate,d.TerminationDate
FROM gnd_hrapr.tblManagerHRFeedback m
INNER JOIN gnd_hrapr.tblManagerHRFeedbackLeavedEmployeeDetail d ON d.ManagerHRFeedbackID=m.ID
INNER JOIN gnd_egbse.tblYearMonth f ON f.ID=m.FromYearMonthID
INNER JOIN gnd_egbse.tblYearMonth t ON t.ID=m.ToYearMonthID
WHERE m.ID=@EvaluationID AND d.TerminationDate BETWEEN f.FromDate AND t.ToDate;
```

## FINAL-U39

Summarize monthly employee work hours and regular overtime hours by each employee's last effective organizational position in that payroll month.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrprs.tblContract, gnd_hrprs.tblLegalPosition, gnd_hrpyr.tblWorkTime.
- Execution: successful; nonempty bounded result.
- Semantics: Uses the exact interval eligibility and FromDate DESC, ID DESC ordering of spEmployeeWorkTimeReportNew contract selection, separately for each payroll month. One contract result per WorkTime row; no splitting or multiplication. Missing assignment is retained as NULL. Stored minutes divided by 60.0.
- Relationships: WorkTime.YearMonthID -> YearMonth.ID. EmployeeID correlates the one effective Contract selected per fact. Contract.LegalPositionID -> LegalPosition.ID; no many-contract aggregation.
- Result columns: YearMonthID, LegalPositionID, ApprovedPosition, EmployeeCount, TotalWorkHours, TotalRegularOvertimeHours.

```sql
SELECT w.YearMonthID,c.LegalPositionID,p.Name AS ApprovedPosition,
 COUNT_BIG(DISTINCT w.EmployeeID) AS EmployeeCount,
 SUM(w.SaatKarkardcdur)/60.0 AS TotalWorkHours,SUM(w.SaatEzafeKarcdur)/60.0 AS TotalRegularOvertimeHours
FROM gnd_hrpyr.tblWorkTime w JOIN gnd_egbse.tblYearMonth y ON y.ID=w.YearMonthID
OUTER APPLY (
 SELECT TOP (1) c.LegalPositionID,c.JobGroupID FROM gnd_hrprs.tblContract c
 WHERE c.EmployeeID=w.EmployeeID
 AND (c.FromDate BETWEEN y.FromDate AND y.ToDate OR (c.FromDate<y.FromDate AND c.ToDate>y.FromDate))
 ORDER BY c.FromDate DESC,c.ID DESC
) c
LEFT JOIN gnd_hrprs.tblLegalPosition p ON p.ID=c.LegalPositionID
GROUP BY w.YearMonthID,c.LegalPositionID,p.Name;
```

## FINAL-U40

Summarize stored work hours, regular overtime hours, and hourly leave by personnel group for complete payroll months from @FromPayrollMonthID through @ThroughPayrollMonthID, attributing each monthly fact to the employee's last effective personnel group that month.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrprs.tblContract, gnd_hrprs.tblJobGroup, gnd_hrpyr.tblWorkTime.
- Execution: successful; nonempty bounded result.
- Semantics: Complete monthly facts only; no daily proration. Effective contract interval/order follows spEmployeeWorkTimeReportNew. OUTER APPLY returns at most one assignment, retaining unmatched facts under NULL group. Duration fields are stored minutes, divided by 60.0.
- Relationships: Monthly WorkTime -> YearMonth; one effective Contract by EmployeeID/month; Contract.JobGroupID -> JobGroup.ID. Personnel group is separate from Unit and Department.
- Result columns: JobGroupID, PersonnelGroup, EmployeeCount, TotalWorkHours, TotalRegularOvertimeHours, TotalLeaveHours.

```sql
SELECT c.JobGroupID,g.Description AS PersonnelGroup,COUNT_BIG(DISTINCT w.EmployeeID) AS EmployeeCount,
 SUM(w.SaatKarkardcdur)/60.0 AS TotalWorkHours,SUM(w.SaatEzafeKarcdur)/60.0 AS TotalRegularOvertimeHours,
 SUM(w.SaatMorakhasicdur)/60.0 AS TotalLeaveHours
FROM gnd_hrpyr.tblWorkTime w JOIN gnd_egbse.tblYearMonth y ON y.ID=w.YearMonthID
JOIN gnd_egbse.tblYearMonth f ON f.ID=@FromPayrollMonthID AND f.MonthID IS NOT NULL
JOIN gnd_egbse.tblYearMonth t ON t.ID=@ThroughPayrollMonthID AND t.MonthID IS NOT NULL
OUTER APPLY (
 SELECT TOP (1) c.LegalPositionID,c.JobGroupID FROM gnd_hrprs.tblContract c
 WHERE c.EmployeeID=w.EmployeeID
 AND (c.FromDate BETWEEN y.FromDate AND y.ToDate OR (c.FromDate<y.FromDate AND c.ToDate>y.FromDate))
 ORDER BY c.FromDate DESC,c.ID DESC
) c
LEFT JOIN gnd_hrprs.tblJobGroup g ON g.ID=c.JobGroupID
WHERE y.MonthID IS NOT NULL AND y.FromDate>=f.FromDate AND y.ToDate<=t.ToDate
GROUP BY c.JobGroupID,g.Description;
```

## FINAL-U41

For @EmployeeID, list daily worktime and attendance events for the payroll month containing @AsOfDate.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrcio.tblCardLog, gnd_hrcio.tblWorkTimeAllDays, gnd_hrprs.tblEmployee.
- Execution: successful; empty bounded result.
- Semantics: Source explicitly requires the current month. Replace server clock with @AsOfDate and freeze the validation date; select an existing employee privately rather than invalid sentinel 0. Daily values repeat per attendance event intentionally and are not aggregated.
- Relationships: Daily worktime joins Employee and YearMonth; attendance CardLog events join logically by employee and calendar date.
- Result columns: EmployeeID, EmployeeCode, Date, WorkTime, NotWorkTime, TotalAdditionalTime, LeaveHours, HourMission, AttendanceEventID, ClockTime, AlternateClockTime, EnterExitTypeID.

```sql
SELECT d.EmployeeID,e.EmployeeCode,d.[Date],d.WorkTime,d.NotWorkTime,
       d.TotalAdditionalTime,d.LeaveHours,d.HourMission,
       c.ID AS AttendanceEventID,c.ClockTime,c.AlternateClockTime,c.EnterExitTypeID
FROM [gnd_hrcio].[tblWorkTimeAllDays] AS d
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=d.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=d.YearMonthID
LEFT JOIN [gnd_hrcio].[tblCardLog] AS c ON c.EmployeeID=d.EmployeeID AND c.DayDate=d.[Date]
WHERE d.EmployeeID=@EmployeeID AND @AsOfDate BETWEEN y.FromDate AND y.ToDate;
```

## FINAL-U42

List approved forgotten-attendance records that are not reflected in daily worktime, including employee, date, and recorded times.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egwfm.tblWork, gnd_hrcio.tblCardLog, gnd_hrcio.tblForgottenEnterExit, gnd_hrprs.tblEmployee.
- Execution: successful; nonempty bounded result.
- Semantics: Authoritative benchmark rule: latest Work for FormTypeID=1389122/FormID by CreateDate DESC, ID DESC must have RunStatusTypeID=3. Not reflected means NOT EXISTS any CardLog with that source FormTypeID/FormID, independent of IsDisable. One row per qualifying forgotten-attendance request.
- Relationships: Latest Work.FormID -> ForgottenEnterExit.ID at FormTypeID=1389122; ForgottenEnterExit.EmployeeID -> Employee.ID; anti-join CardLog.FormTypeID=1389122/FormID -> request.ID.
- Result columns: ForgottenAttendanceID, EmployeeID, EmployeeCode, DayDate, ClockTime, PermissionTypeID.

```sql
WITH LatestWork AS (
    SELECT
        w.FormID,
        w.RunStatusTypeID,
        ROW_NUMBER() OVER (
            PARTITION BY w.FormID
            ORDER BY w.CreateDate DESC,w.ID DESC
        ) AS rn
    FROM gnd_egwfm.tblWork AS w
    WHERE w.FormTypeID=1389122
)
SELECT
    f.ID AS ForgottenAttendanceID,
    f.EmployeeID,
    e.EmployeeCode,
    f.DayDate,
    f.ClockTime,
    f.PermissionTypeID
FROM gnd_hrcio.tblForgottenEnterExit AS f
INNER JOIN LatestWork AS w
    ON w.FormID=f.ID
   AND w.rn=1
   AND w.RunStatusTypeID=3
INNER JOIN gnd_hrprs.tblEmployee AS e
    ON e.ID=f.EmployeeID
WHERE NOT EXISTS (
    SELECT 1
    FROM gnd_hrcio.tblCardLog AS c
    WHERE c.FormTypeID=1389122
      AND c.FormID=f.ID
);
```

## FINAL-U43

For each employee and payroll month, count distinct dates with a valid non-off shift and at least one active attendance event, counting a date with multiple qualifying shifts only once.

- Domain: personnel/attendance; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrcio.tblCardLog, gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShift, gnd_hrcio.tblShiftDetail, gnd_hrcio.tblShiftTemplate, gnd_hrcio.tblWorkShiftType, gnd_hrprs.tblEmployee.
- Execution: successful; nonempty bounded result.
- Semantics: Human-authorized qualification: vwEmployeeShiftCompleteReport row with IsOff=0 plus same EmployeeID/date CardLog.IsDisable=0. COUNT(DISTINCT Date), not roster-only eligibility. Monthly YearMonth date ranges are verified nonoverlapping. The view dependency closure is retained.
- Relationships: Shift-report view supplies roster/modification validity. CardLog is correlated by EmployeeID + DayDate without a physical composite FK. YearMonth is a logical date-range join; EmployeeID -> Employee.ID.
- Result columns: EmployeeID, EmployeeCode, YearMonthID, ShiftWorkDayCount.

```sql
SELECT s.EmployeeID,e.EmployeeCode,y.ID AS YearMonthID,COUNT_BIG(DISTINCT s.Date) AS ShiftWorkDayCount
FROM gnd_hrcio.vwEmployeeShiftCompleteReport s
JOIN gnd_hrprs.tblEmployee e ON e.ID=s.EmployeeID
JOIN gnd_egbse.tblYearMonth y ON s.Date BETWEEN y.FromDate AND y.ToDate AND y.MonthID IS NOT NULL
WHERE s.IsOff=0 AND EXISTS (
 SELECT 1 FROM gnd_hrcio.tblCardLog c WHERE c.EmployeeID=s.EmployeeID AND c.DayDate=s.Date AND c.IsDisable=0
)
GROUP BY s.EmployeeID,e.EmployeeCode,y.ID;
```

## FINAL-U44

For each employee and payroll month, show unrounded regular overtime and holiday overtime hours.

- Domain: personnel/attendance; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime.
- Execution: successful; nonempty bounded result.
- Semantics: Human decision confirms unrounded system overtime fields SystemSaatEzafeKarcdur and SystemSaatEzafekarTatilicdur, stored in minutes. Divide by 60.0 without rounding; payroll overtime fields are not substitutes.
- Relationships: WorkTime.EmployeeID and YearMonthID join Employee and YearMonth.
- Result columns: EmployeeID, EmployeeCode, YearMonthID, Year, MonthID, UnroundedRegularOvertimeHours, UnroundedHolidayOvertimeHours.

```sql
SELECT w.EmployeeID,e.EmployeeCode,w.YearMonthID,y.[Year],y.MonthID,
       w.SystemSaatEzafeKarcdur / 60.0 AS UnroundedRegularOvertimeHours,
       w.SystemSaatEzafekarTatilicdur / 60.0 AS UnroundedHolidayOvertimeHours
FROM [gnd_hrpyr].[tblWorkTime] AS w
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=w.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID;
```

## FINAL-U45

For yarn group @InterweavingID selected from the ERP's yarn-group list and packing dates from @FromDate through @ThroughDate, list serial-numbered packs included by the ERP's 'packing without warehouse receipt' report, showing packing identifier, packing date, and serial.

- Domain: production; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_ficac.tblProjectStandardProduction, gnd_ficac.tblProjectStandardProductionScannedBarcode, gnd_scprd.tblPacking.
- Execution: successful; empty bounded result.
- Semantics: Preserves the named report OnlyWithoutEnter filter: the maximum ISNULL(Code,0) across production records linked by serial is not 99; no linked record also qualifies. This is the report criterion, not an independent proof that no warehouse receipt exists. Non-null serial and inclusive packing dates are preserved. One row per pack; unused display-name and stock-status joins are omitted. No direct inventory anti-join or invented approval rule is added. Parameter contract: @InterweavingID must identify an entry in gnd_pjprj.evInterweaving, matching an ERP-selectable yarn group. Some physical packing references are absent from that entity view; accepting arbitrary IDs would not preserve the report. The production entity-view identity join was separately checked and removes no current production records. These display/audit-view joins are not physical Gold dependencies; the valid input domain and current-data invariant are explicit.
- Relationships: Packing.Serial = ProjectStandardProductionScannedBarcode.Serial is a logical join explicitly used by the ERP report, not an FK. ProjectStandardProductionScannedBarcode.ProjectStandardProductionID -> ProjectStandardProduction.ID is an FK. InterWeavingID filtering uses Packing directly.
- Result columns: PackingID, PackingDate, Serial.

```sql
SELECT p.ID AS PackingID,p.DoneDate AS PackingDate,p.Serial
FROM [gnd_scprd].[tblPacking] AS p
OUTER APPLY (
    SELECT MAX(ISNULL(ps.Code,0)) AS HighestProductionCode
    FROM [gnd_ficac].[tblProjectStandardProductionScannedBarcode] AS b
    INNER JOIN [gnd_ficac].[tblProjectStandardProduction] AS ps
      ON ps.ID=b.ProjectStandardProductionID
    WHERE b.Serial=p.Serial
) AS production
WHERE p.InterWeavingID=@InterweavingID
  AND p.DoneDate BETWEEN @FromDate AND @ThroughDate
  AND p.Serial IS NOT NULL
  AND ISNULL(production.HighestProductionCode,0)<>99;
```

## FINAL-U46

For purchase-invoice lines with a missing or zero unit price, show the warehouse amount, quantity, and warehouse amount per unit.

- Domain: purchasing; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblPurchaseInvoiceGoodDetailEnter, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: The original warehouse-amount phrase exactly matches the explicit InvValue caption. AccValue has the distinct Amount caption. Divide InvValue by Qty, returning NULL for zero or NULL quantity; preserve stored NULL amounts. Missing-or-zero price is explicit in the revised wording. This is a read-only projection, not a price update.
- Relationships: PurchaseInvoiceGoodDetailEnter.PurchaseInvoiceGoodAndServiceID -> invoice.ID and GoodID -> Good.ID are explicit FKs. Only the projected/calculated amount changes to InvValue.
- Result columns: PurchaseInvoiceID, PurchaseInvoiceCode, InvoiceLineID, GoodID, GoodCode, GoodName, Qty, WarehouseAmount, UnitPrice, WarehouseAmountPerUnit.

```sql
SELECT i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,d.IG AS InvoiceLineID,
       d.GoodID,g.GoodCode,g.Farsi AS GoodName,d.Qty,d.InvValue AS WarehouseAmount,d.UnitPrice,
       d.InvValue/NULLIF(d.Qty,0) AS WarehouseAmountPerUnit
FROM [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceGoodDetailEnter] AS d
  ON d.PurchaseInvoiceGoodAndServiceID=i.ID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE d.UnitPrice IS NULL OR d.UnitPrice=0;
```

## FINAL-U47

List purchase inquiries with the employee who requested the purchase.

- Domain: purchasing; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_hrprs.tblEmployee, gnd_scpch.tblPurchaseInquiry, gnd_scpch.tblPurchaseOrder, gnd_scpch.tblPurchaseOrderDetail, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail.
- Execution: successful; nonempty bounded result.
- Semantics: The query uses directly stored fields and explicit Gold joins without an additional business rule.
- Relationships: PurchaseInquiry joins PurchaseOrder, PurchaseOrderDetail, PurchaseRequestDetail, PurchaseRequest, and the requesting Employee through explicit relationships.
- Result columns: PurchaseInquiryID, PurchaseInquiryCode, DoneDate, PurchaseRequestID, RequestEmployeeID, EmployeeCode.

```sql
SELECT i.ID AS PurchaseInquiryID,i.Code AS PurchaseInquiryCode,i.DoneDate,
       r.ID AS PurchaseRequestID,r.RequestEmployeeID,e.EmployeeCode
FROM [gnd_scpch].[tblPurchaseInquiry] AS i
INNER JOIN [gnd_scpch].[tblPurchaseOrder] AS o ON o.ID=i.PurchaseOrderID
INNER JOIN [gnd_scpch].[tblPurchaseOrderDetail] AS od ON od.PurchaseOrderID=o.ID
INNER JOIN [gnd_scpch].[tblPurchaseRequestDetail] AS rd ON rd.IG=od.PurchaseRequestDetailIG
INNER JOIN [gnd_scpch].[tblPurchaseRequest] AS r ON r.ID=rd.PurchaseRequestID
LEFT JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=r.RequestEmployeeID
GROUP BY i.ID,i.Code,i.DoneDate,r.ID,r.RequestEmployeeID,e.EmployeeCode;
```

## FINAL-U48

List purchase inquiries with the person currently responsible for workflow approval.

- Domain: purchasing; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbpm.tblProcessStep, gnd_egbse.tblContact, gnd_egwfm.tblWork, gnd_scpch.tblPurchaseInquiry.
- Execution: successful; nonempty bounded result.
- Semantics: Latest inquiry task uses greatest Work.ID, explicitly used by fnPurchaseInquiry_LastStepName. Only statuses 0/1 are active, exactly as vwRunningWorks. Select latest before testing active status, so no fallback to an older active task. CurrentUserID -> Contact.ID is the declared workflow assignee FK; NULL when the latest task is inactive or unassigned.
- Relationships: Work is keyed to the inquiry by FormTypeID=1927645 and FormID. Existing SQL ranks all Work rows before filtering completion; it does NOT select the latest non-completed row. Lifecycle/order/person semantics remain on hold.
- Result columns: PurchaseInquiryID, PurchaseInquiryCode, DoneDate, CurrentUserID, CurrentApprover, CurrentProcessStepID, CurrentApprovalStep, RunStatusTypeID.

```sql
WITH CurrentWork AS (
 SELECT w.*,ROW_NUMBER() OVER(PARTITION BY w.FormID ORDER BY w.ID DESC) AS rn
 FROM [gnd_egwfm].[tblWork] AS w WHERE w.FormTypeID=1927645
)
SELECT i.ID AS PurchaseInquiryID,i.Code AS PurchaseInquiryCode,i.DoneDate,
       w.CurrentUserID,c.Farsi AS CurrentApprover,w.CurrentProcessStepID,
       ps.Name AS CurrentApprovalStep,w.RunStatusTypeID
FROM [gnd_scpch].[tblPurchaseInquiry] AS i
LEFT JOIN CurrentWork AS w ON w.FormID=i.ID AND w.rn=1 AND w.RunStatusTypeID IN (0,1)
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=w.CurrentUserID
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID;
```

## FINAL-U49

Show the open purchase pro forma report, including each pro forma item line and its remaining quantity after quality control of delivered items.

- Domain: quality; difficulty: Hard.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_egbse.tblContact, gnd_egbse.tblConvertDateTypeL, gnd_egbse.tblPerson, gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblPrefix, gnd_egbse.tblUser, gnd_scpch.tblNotifyEnter, gnd_scpch.tblPrePurchaseInvoice, gnd_scpch.tblPrePurchaseInvoiceDetail, gnd_scpch.tblQualityControl, gnd_scpch.tblQualityControlDetail, gnd_scpch.tblSupplier, gnd_spgod.tblGood, gnu_egbse.xblContact, gnu_egbse.xblPerson, gnu_egbse.xblPrefix, gnu_scpch.xblPrePurchaseInvoice, gnu_scpch.xblSupplier.
- Execution: successful; empty bounded result.
- Semantics: SELECT/CTE transcription of the existing open purchase pro forma report. Its original notification/QC eligibility, join multiplicity, per-item remaining-quantity calculation, positive-balance filter and detail-line grain are retained. This reports ERP-defined remaining quantities; it does not silently repair or reinterpret the report arithmetic. Entity-view display dependencies are included.
- Relationships: NotifyEnter FormTypeID=17889/FormID -> PrePurchaseInvoice.ID; QualityControl FormTypeID=1666058/FormID -> NotifyEnter.ID; QualityControlDetail.QualityControlID -> QualityControl.ID; PrePurchaseInvoiceDetail.PrePurchaseInvoiceID -> invoice and GoodID -> Good.ID. Report aggregates by invoice/item then joins detail lines.
- Result columns: ID, PrePurchaseInvoice, ItemsNotReceived, RemainedQty.

```sql
WITH                                            c
AS (SELECT e.FormID,
ed.GoodID,
-1 * SUM(ISNULL(ed.CQty,0)) AS Qty
FROM gnd_scpch.tblNotifyEnter e
INNER JOIN gnd_scpch.tblQualityControl qc
ON qc.FormTypeID = 1666058
AND qc.FormID = e.ID
LEFT JOIN gnd_scpch.tblQualityControlDetail ed
ON ed.QualityControlID = qc.ID
WHERE e.FormTypeID = 17889
AND ed.GoodID IS NOT NULL
GROUP BY e.FormID,
ed.GoodID
UNION ALL
SELECT p.ID,
pd.GoodID,
SUM(pd.Qty)
FROM gnd_scpch.tblPrePurchaseInvoice p
INNER JOIN gnd_scpch.tblPrePurchaseInvoiceDetail pd
ON pd.PrePurchaseInvoiceID = p.ID
INNER JOIN gnd_scpch.tblNotifyEnter e
ON e.FormTypeID = 17889
AND e.FormID = p.ID
WHERE  EXISTS
(
SELECT 1
FROM gnd_scpch.tblQualityControl qc
WHERE qc.FormTypeID = 1666058
AND qc.FormID = e.ID
)
GROUP BY p.ID,
pd.GoodID), Base AS (
SELECT c.FormID,
c.GoodID,
SUM(c.Qty) RemainedQty
FROM c
GROUP BY c.FormID,
c.GoodID
HAVING SUM(c.Qty) > 0)
SELECT  pd.IG AS ID,
p.Farsi AS PrePurchaseInvoice,
g.Farsi ItemsNotReceived,
SUM(b.RemainedQty) AS RemainedQty
FROM Base b
INNER JOIN gnd_scpch.evPrePurchaseInvoice p
ON b.FormID = p.ID
INNER JOIN gnd_spgod.tblGood g
ON g.ID = b.GoodID
INNER JOIN gnd_scpch.tblPrePurchaseInvoiceDetail pd
ON pd.PrePurchaseInvoiceID = p.ID
AND pd.GoodID = g.ID
GROUP BY  pd.IG,
p.Farsi,
g.Farsi
ORDER BY p.Farsi;
```

## FINAL-U50

List every goods and service line on sales invoices with invoice number and date, customer, line type, item or service, quantity, unit price, discount, VAT, and the ERP-calculated line value before VAT.

- Domain: sales; difficulty: Medium.
- Status: FINAL_APPROVED_BOUNDED_VALIDATED; human approval: True.
- Decision classification: HUMAN_DECISION_RESOLVED.
- Current SQL physical dependencies: gnd_crsls.tblCustomer, gnd_crsls.tblSalesAndServicesInvoice, gnd_crsls.tblSalesAndServicesInvoiceSalesDetail, gnd_crsls.tblSalesAndServicesInvoiceServDetail, gnd_crsls.tblSellableService, gnd_egbse.tblContact, gnd_fiaci.tblVatPercentage, gnd_spgod.tblGood.
- Execution: successful; nonempty bounded result.
- Semantics: UNION ALL preserves goods and service lines. LineType plus InvoiceLineID identifies the line family. Goods use existing RowTotalPayable (Qty times ActualUnitPrice less discount); services use existing SalesValue (Qty times UnitPrice less discount). Both exclude VAT, which is a separate output; neither value is recomputed with a new pricing rule. Displayed goods UnitPrice can differ from ActualUnitPrice used by the ERP calculation.
- Relationships: Both invoice detail tables reference SalesAndServicesInvoice.ID by FK. Goods detail.GoodID -> Good.ID; service detail.SellableServiceID -> SellableService.ID. Invoice.CredbCustomerID -> Customer.ID -> Contact.ID through shared identity. Computed pricing/tax dependencies are separately audited.
- Result columns: SalesInvoiceID, InvoiceNumber, InvoiceDate, CredbCustomerID, CustomerCode, CustomerName, LineType, InvoiceLineID, ItemID, ItemName, Qty, UnitPrice, DiscountValue, Vat, ERPLineValueBeforeVAT.

```sql
SELECT i.ID AS SalesInvoiceID,i.Code AS InvoiceNumber,i.DoneDate AS InvoiceDate,
       i.CredbCustomerID,c.CustomerCode,cc.Farsi AS CustomerName,
       N'Goods' AS LineType,d.IG AS InvoiceLineID,d.GoodID AS ItemID,
       g.Farsi AS ItemName,d.Qty,d.UnitPrice,d.DiscountValue,d.Vat,
       d.RowTotalPayable AS ERPLineValueBeforeVAT
FROM [gnd_crsls].[tblSalesAndServicesInvoice] AS i
INNER JOIN [gnd_crsls].[tblSalesAndServicesInvoiceSalesDetail] AS d
  ON d.SalesAndServicesInvoiceID=i.ID
LEFT JOIN [gnd_crsls].[tblCustomer] AS c ON c.ID=i.CredbCustomerID
LEFT JOIN [gnd_egbse].[tblContact] AS cc ON cc.ID=c.ID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
UNION ALL
SELECT i.ID,i.Code,i.DoneDate,i.CredbCustomerID,c.CustomerCode,cc.Farsi,
       N'Service',d.IG,d.SellableServiceID,s.Name,d.Qty,d.UnitPrice,
       d.DiscountValue,d.Vat,d.SalesValue
FROM [gnd_crsls].[tblSalesAndServicesInvoice] AS i
INNER JOIN [gnd_crsls].[tblSalesAndServicesInvoiceServDetail] AS d
  ON d.SalesAndServicesInvoiceID=i.ID
LEFT JOIN [gnd_crsls].[tblCustomer] AS c ON c.ID=i.CredbCustomerID
LEFT JOIN [gnd_egbse].[tblContact] AS cc ON cc.ID=c.ID
LEFT JOIN [gnd_crsls].[tblSellableService] AS s ON s.ID=d.SellableServiceID;
```
