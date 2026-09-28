"""Gold T-SQL definitions for the proposed final unseen benchmark."""
from final_unseen_benchmark import FINAL_UNSEEN_CASES


SQL = {
"FINAL-U01": """SELECT i.ID AS InvoiceID,i.Code AS InvoiceNumber,i.DoneDate AS InvoiceDate,
       i.AnnualSalesOrderNumber
FROM [gnd_crsls].[tblSalesAndServicesInvoice] AS i;""",
"FINAL-U02": """SELECT o.ID AS PurchaseOrderID,o.Code AS PurchaseOrderCode,
       r.ID AS PurchaseRequestID,r.Code AS PurchaseRequestCode,
       d.IG AS RequestLineID,g.ID AS GoodID,g.Farsi AS GoodName,
       d.RequestedQty,d.Description
FROM [gnd_scpch].[tblPurchaseOrder] AS o
INNER JOIN [gnd_scpch].[tblPurchaseRequest] AS r
  ON o.FormTypeID=1451914 AND o.FormID=r.ID
INNER JOIN [gnd_scpch].[tblPurchaseRequestDetail] AS d ON d.PurchaseRequestID=r.ID
INNER JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID;""",
"FINAL-U03": """SELECT r.ID AS RequestID,r.Code AS RequestCode,r.RequestedDate,
       e.ID AS EmployeeID,e.EmployeeCode,d.IG AS RequestLineID,
       g.ID AS GoodID,g.Farsi AS GoodName,d.RequestQty,d.QtyInQueue,d.RemainedQty
FROM [gnd_scpch].[tblGoodServiceRequest] AS r
INNER JOIN [gnd_scpch].[tblGoodServiceRequestDetail] AS d ON d.GoodServiceRequestID=r.ID
LEFT JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=r.RequestedEmployeeID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE ISNULL(r.Code,-1)<>99;""",
"FINAL-U04": """SELECT
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
  AND l.DoneDate<DATEADD(day,1,@ReportDate);""",
"FINAL-U05": """SELECT o.ID AS SalesOrderID,o.Code,o.OrderDate,o.AnnualSalesOrderNumber,
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
              WHERE d.SalesOrderID=o.ID AND ISNULL(d.HasShipped,0)=0);""",
"FINAL-U06": """SELECT i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,
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
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID;""",
"FINAL-U07": """SELECT e.ID AS EmployeeID,e.EmployeeCode,y.ID AS YearMonthID,y.[Year],y.MonthID,
       COUNT_BIG(*) AS AdditionalOffDateCount
FROM [gnd_hrcio].[tblEmployeeShiftAdditionalOffDates] AS o
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=o.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON o.[Date]>=y.FromDate AND o.[Date]<=y.ToDate
GROUP BY e.ID,e.EmployeeCode,y.ID,y.[Year],y.MonthID;""",
"FINAL-U08": """WITH RankedWork AS (
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
GROUP BY p.DepartmentID,d.Name,p.ExitReason,s.ID,s.Description;""",
"FINAL-U09": """SELECT m.ID AS ModificationID,m.EmployeeID,e.EmployeeCode,m.[Date] AS ModificationDate,
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
LEFT JOIN gnd_hrcio.tblShiftTemplate ns ON ns.ID=m.ShiftID;""",
"FINAL-U10": """SELECT w.ID AS WorkTimeID,w.EmployeeID,e.EmployeeCode,w.YearMonthID,
       w.SaatKarkardcdur/60.0 AS WorkHours,w.SaatKasrKarcdur/60.0 AS NonWorkHours,
       w.SaatEzafeKarcdur/60.0 AS RegularOvertimeHours,
       w.AnnualLeave AS LeaveDays,w.SaatMorakhasicdur/60.0 AS LeaveHours,
       w.TedadRuzMamuriat AS MissionDays,w.SaatMamuriatcdur/60.0 AS MissionHours
FROM gnd_hrpyr.tblWorkTime w
JOIN gnd_hrprs.tblEmployee e ON e.ID=w.EmployeeID
JOIN gnd_egbse.tblYearMonth y ON y.ID=w.YearMonthID
JOIN gnd_egbse.tblYearMonth f ON f.ID=@FromPayrollMonthID AND f.MonthID IS NOT NULL
JOIN gnd_egbse.tblYearMonth t ON t.ID=@ThroughPayrollMonthID AND t.MonthID IS NOT NULL
WHERE y.MonthID IS NOT NULL AND y.FromDate>=f.FromDate AND y.ToDate<=t.ToDate;""",
"FINAL-U11": """WITH Credits AS (
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
LEFT JOIN Deliveries d ON d.EmployeeID=a.EmployeeID AND d.YearMonthID=a.YearMonthID;""",
"FINAL-U12": """SELECT r.ID AS LoanRequestID,r.EmployeeID,e.EmployeeCode,r.RequestDate,
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
) AS m;""",
"FINAL-U13": """SELECT i.ID AS InterweavingID,i.InterweavingCode,
       yt.Farsi AS YarnType,ss.Farsi AS SpinningSystem,q.Farsi AS Quality,
       sc.Farsi AS SpinningCount,SUM(p.NetWeight) AS TotalPackedNetWeight
FROM [gnd_scprd].[tblPacking] AS p
INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=p.InterWeavingID
LEFT JOIN [gnd_spgod].[tblYarnType] AS yt ON yt.ID=i.YarnTypeID
LEFT JOIN [gnd_spgod].[tblSpinningSystemType] AS ss ON ss.ID=i.SpinningSystemTypeID
LEFT JOIN [gnd_spgod].[tblQualityType] AS q ON q.ID=i.QualityTypeID
LEFT JOIN [gnd_spgod].[tblSpinningCountType] AS sc ON sc.ID=i.SpinningCountTypeID
GROUP BY i.ID,i.InterweavingCode,yt.Farsi,ss.Farsi,q.Farsi,sc.Farsi;""",
"FINAL-U14": """SELECT l.ID AS BobbinLabelID,i.ID AS InterweavingID,i.InterweavingCode,
       s.Farsi AS SpinningSystemName
FROM [gnd_scprd].[tblSpindleLable] AS l
INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=l.InterweavingID
INNER JOIN [gnd_spgod].[tblSpinningSystemType] AS s ON s.ID=i.SpinningSystemTypeID;""",
"FINAL-U15": """SELECT q.ID AS QualityControlID,q.Code,q.DoneDate,d.IG AS QualityControlLineID,
       g.ID AS GoodID,g.GoodCode,g.Farsi AS GoodName,d.Qty,d.NotifiQTY,d.CQty
FROM [gnd_scpch].[tblQualityControl] AS q
INNER JOIN [gnd_scpch].[tblQualityControlDetail] AS d ON d.QualityControlID=q.ID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE q.DoneDate>=@StartDate
  AND g.GoodGroupID IN (1487,1488,1489,1490)
  AND NOT EXISTS (
    SELECT 1 FROM [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
    WHERE i.FormTypeID=1684173 AND i.FormID=q.ID
  );""",
"FINAL-U16": """SELECT w.ID AS WorkOrderID,w.Code,w.WorkOrderTitle,w.SuggestedExecutionDate,
       w.EquipmentID,e.NameInEnglish AS EquipmentName,
       w.RoutineID,r.English AS RoutineName
FROM [gnd_amspt].[tblWorkOrder] AS w
LEFT JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=w.EquipmentID
LEFT JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=w.RoutineID
WHERE w.ResponsibleEmployeeID IS NULL;""",
"FINAL-U17": """SELECT r.ID AS RoutineID,r.Farsi AS RoutineName,c.IG AS CoverageLineID,
       covered.ID AS CoveredRoutineID,covered.Farsi AS CoveredRoutineName
FROM [gnd_amspt].[tblRoutineCovered] AS c
INNER JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=c.RoutineID
INNER JOIN [gnd_amspt].[tblRoutine] AS covered ON covered.ID=c.CoveredRoutineID
WHERE c.RoutineID=@RoutineID;""",
"FINAL-U18": """SELECT r.ID AS PayRequestID,r.Code,r.PayRequestDate,r.ExecuteDate AS RequestedExecutionDate,
       d.ID AS PayRequestLineID,d.Sequence,d.Amount,d.Description AS LineDescription,d.PayDate
FROM [gnd_firpd].[tblPayRequest] AS r
INNER JOIN [gnd_firpd].[tblPayRequestDetail] AS d ON d.PayRequestID=r.ID
WHERE r.PayRequestDate>=@FromDate AND r.PayRequestDate<DATEADD(day,1,@ThroughDate);""",
"FINAL-U19": """SELECT b.ID AS BankReceiptID,b.Code,b.DoneDate,b.AccValue AS ReceiptAmount,
       d.IG AS AccountingLineID,d.Sequence,d.AccountID,a.AccountCode,a.Farsi AS AccountName,
       d.AccValue AS LineAmount,d.Description AS LineDescription,d.TransDetail
FROM [gnd_firpd].[tblBankInput] AS b
INNER JOIN [gnd_firpd].[tblBankInputDetail] AS d ON d.BankInputID=b.ID
LEFT JOIN [gnd_fiaci].[tblAccount] AS a ON a.ID=d.AccountID;""",
"FINAL-U20": """SELECT t.ID AS TransactionID,t.Code AS TransactionCode,t.DocDate,
       d.IG AS JournalLineID,d.RowNumber,d.AccountID,a.AccountCode,a.Farsi AS AccountName,
       d.Description,d.Debit,d.Credit
FROM [gnd_fiaci].[tblTransDetailDetail] AS x
INNER JOIN [gnd_fiaci].[tblTransDetail] AS d ON d.IG=x.TransDetailIG
INNER JOIN [gnd_fiaci].[tblTrans] AS t ON t.ID=d.TransID
LEFT JOIN [gnd_fiaci].[tblAccount] AS a ON a.ID=d.AccountID
WHERE x.FormTypeID=@DetailFormTypeID AND x.FormID=@DetailFormID
ORDER BY t.DocDate,t.ID,d.RowNumber;""",
"FINAL-U21": """SELECT p.ID AS ProjectID,p.Farsi AS ProjectName,
       i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,i.DoneDate AS InvoiceDate,
       i.CredbSupplierID AS SupplierID,i.SumPayable AS TotalPayable
FROM [gnd_pjprj].[tblProject] AS p
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
  ON i.CredbProjectID=p.ID;""",
"FINAL-U22": """SELECT c.UserID,MAX(c.LastSeenDate) AS LastSeenAt
FROM [gnd_egbse].[tblChatLastSeen] AS c
GROUP BY c.UserID;""",
"FINAL-U23": """SELECT r.ID AS RoleID,r.Description AS RoleName,s.ID AS SystemID,s.Description AS SystemName,
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
LEFT JOIN [gnd_egsys].[tblCaption] AS c ON c.ID=p.CaptionID;""",
"FINAL-U24": """WITH CurrentWork AS (
 SELECT w.*,ROW_NUMBER() OVER(PARTITION BY w.FormID ORDER BY w.ID DESC) AS rn
 FROM [gnd_egwfm].[tblWork] AS w WHERE w.FormTypeID=501
)
SELECT l.ID AS InternalLetterID,l.Code,l.[Date],l.Subject,
       w.CurrentProcessStepID,ps.Name AS CurrentWorkflowStep,
       w.RunStatusTypeID,rs.Description AS WorkflowRunStatus
FROM [gnd_ofsct].[tblInternalLetter] AS l
LEFT JOIN CurrentWork AS w ON w.FormID=l.ID AND w.rn=1
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID
LEFT JOIN [gnd_egwfm].[tblRunStatusTypeL] AS rs ON rs.ID=w.RunStatusTypeID;""",
}

SQL.update({
"FINAL-U25": """SELECT d.GoodID,g.Farsi AS ItemDescription,h.RequesterEmployeeID,
       COUNT_BIG(*) AS OccurrenceCount,SUM(d.Qty) AS TotalConsumedQuantity
FROM gnd_scinv.tblGoodConsume h
JOIN gnd_scinv.tblGoodConsumeDetail d ON d.GoodConsumeID=h.ID
JOIN gnd_spgod.tblGood g ON g.ID=d.GoodID
GROUP BY d.GoodID,g.Farsi,h.RequesterEmployeeID HAVING COUNT_BIG(*)>1;""",
"FINAL-U26": """SELECT f.ID AS FeedbackID,w.ID AS WorkOrderID,w.Code AS WorkOrderCode,
       f.EquipmentID,e.NameInEnglish AS EquipmentName,f.ReportDate AS FeedbackDate,
       f.AmountOfWork,
       CONVERT(bit,CASE WHEN EXISTS (
         SELECT 1 FROM [gnd_egwfm].[tblWorkRoute] AS wr
         WHERE wr.FormTypeID=1136748 AND wr.FormID=f.ID
       ) THEN 1 ELSE 0 END) AS HasContinued
FROM [gnd_amspt].[tblFeedback] AS f
INNER JOIN [gnd_amspt].[tblWorkOrder] AS w ON w.ID=f.ID
LEFT JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=f.EquipmentID
WHERE f.AmountOfWork<0;""",
"FINAL-U27": """WITH SourceLines AS (
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
);""",
"FINAL-U28": """SELECT r.ID AS PayRequestID,r.Code,r.PayRequestDate,
       r.PayContactID,c.Farsi AS Counterparty,r.DestinationDescription,
       d.ID AS PayRequestLineID,d.Sequence,d.Description AS LineDescription,d.Amount
FROM [gnd_firpd].[tblPayRequest] AS r
INNER JOIN [gnd_firpd].[tblPayRequestDetail] AS d ON d.PayRequestID=r.ID
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=r.PayContactID;""",
"FINAL-U29": """WITH Cheques AS (
    SELECT c.ID AS InputChequeID,c.ChequeNumber,c.DoneDate AS ReceiptDate,
           COUNT_BIG(*) OVER (PARTITION BY c.ChequeNumber,c.DoneDate) AS DuplicateCount
    FROM [gnd_firpd].[tblInputCheque] AS c
)
SELECT InputChequeID,ChequeNumber,ReceiptDate,DuplicateCount
FROM Cheques
WHERE DuplicateCount>1;""",
"FINAL-U30": """SELECT l.ID AS LoadingID,l.Code AS LoadingCode,l.DoneDate,
       b.IG AS ScannedBarcodeID,b.Barcode,b.Serial,b.InterweavingID,
       i.InterweavingCode,b.NetWeight,
       SUM(b.NetWeight) OVER(PARTITION BY l.ID,b.InterweavingID) AS InterweavingTotalScannedWeight
FROM [gnd_crsls].[tblLoading] AS l
INNER JOIN [gnd_crsls].[tblLoadingScannedBarcode] AS b ON b.LoadingID=l.ID
LEFT JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=b.InterweavingID;""",
"FINAL-U31": """WITH Period AS (
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
GROUP BY m.GoodID,g.GoodCode,g.Farsi,m.InventoryID,i.Farsi;""",
"FINAL-U32": """SELECT
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
    ON c.ID=h.CredbRelatedToPersonID;""",
"FINAL-U33": """SELECT e.ID AS WorkID,e.CreateDate AS CompletedAt
FROM [gnd_egwfm].[tblWorkEnd] AS e
WHERE e.DoneStatusTypeID=1
  AND e.CreateDate>=@ReportDate
  AND e.CreateDate<DATEADD(day,1,@ReportDate);""",
"FINAL-U34": """SELECT w.ID AS WorkID,w.FormTypeID,w.FormID,w.LastPlaceChangeDate AS AssignedDate,
       w.CurrentUserID,c.Farsi AS CurrentAssignee,w.CurrentProcessStepID,
       ps.Name AS CurrentStep,w.RunStatusTypeID,rs.Description AS RunStatus
FROM [gnd_egwfm].[tblWork] AS w
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=w.CurrentUserID
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID
LEFT JOIN [gnd_egwfm].[tblRunStatusTypeL] AS rs ON rs.ID=w.RunStatusTypeID
WHERE w.RunStatusTypeID IN (0,1);""",
"FINAL-U35": """SELECT l.ID AS InternalLetterID,l.Code,l.[Date] AS SentDate,l.Subject,
       l.SenderID,s.Farsi AS Sender,r.PersonID AS RecipientID,rc.Farsi AS Recipient,
       r.IsMain AS IsMainRecipient
FROM [gnd_ofsct].[tblInternalLetter] AS l
LEFT JOIN [gnd_egbse].[tblContact] AS s ON s.ID=l.SenderID
LEFT JOIN [gnd_ofsct].[tblRecEmpInternalLetter] AS r ON r.InternalLetterID=l.ID
LEFT JOIN [gnd_egbse].[tblContact] AS rc ON rc.ID=r.PersonID;""",
"FINAL-U36": """SELECT w.ID AS WorkTimeID,w.EmployeeID,e.EmployeeCode,w.YearMonthID,
       y.[Year],y.MonthID,w.TedadRuzTatilKariShift AS HolidayDayCount,
       w.SaatEzafeKarcdur / 60.0 AS RegularOvertimeHours,w.SaatJomehKaricdur / 60.0 AS FridayOvertimeHours
FROM [gnd_hrpyr].[tblWorkTime] AS w
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=w.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID;""",
"FINAL-U37": """WITH PeriodContext AS (
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
WHERE ISNULL(e.IsLeaved,0)=0;""",
"FINAL-U38": """SELECT m.ID AS EvaluationID,m.UnitID,d.EmployeeID,
       d.EmploymentDate AS HireDate,d.TerminationDate
FROM gnd_hrapr.tblManagerHRFeedback m
INNER JOIN gnd_hrapr.tblManagerHRFeedbackLeavedEmployeeDetail d ON d.ManagerHRFeedbackID=m.ID
INNER JOIN gnd_egbse.tblYearMonth f ON f.ID=m.FromYearMonthID
INNER JOIN gnd_egbse.tblYearMonth t ON t.ID=m.ToYearMonthID
WHERE m.ID=@EvaluationID AND d.TerminationDate BETWEEN f.FromDate AND t.ToDate;""",
"FINAL-U39": """SELECT w.YearMonthID,c.LegalPositionID,p.Name AS ApprovedPosition,
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
GROUP BY w.YearMonthID,c.LegalPositionID,p.Name;""",
"FINAL-U40": """SELECT c.JobGroupID,g.Description AS PersonnelGroup,COUNT_BIG(DISTINCT w.EmployeeID) AS EmployeeCount,
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
GROUP BY c.JobGroupID,g.Description;""",
"FINAL-U41": """SELECT d.EmployeeID,e.EmployeeCode,d.[Date],d.WorkTime,d.NotWorkTime,
       d.TotalAdditionalTime,d.LeaveHours,d.HourMission,
       c.ID AS AttendanceEventID,c.ClockTime,c.AlternateClockTime,c.EnterExitTypeID
FROM [gnd_hrcio].[tblWorkTimeAllDays] AS d
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=d.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=d.YearMonthID
LEFT JOIN [gnd_hrcio].[tblCardLog] AS c ON c.EmployeeID=d.EmployeeID AND c.DayDate=d.[Date]
WHERE d.EmployeeID=@EmployeeID AND @AsOfDate BETWEEN y.FromDate AND y.ToDate;""",
"FINAL-U42": """WITH LatestWork AS (
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
);""",
"FINAL-U43": """SELECT s.EmployeeID,e.EmployeeCode,y.ID AS YearMonthID,COUNT_BIG(DISTINCT s.Date) AS ShiftWorkDayCount
FROM gnd_hrcio.vwEmployeeShiftCompleteReport s
JOIN gnd_hrprs.tblEmployee e ON e.ID=s.EmployeeID
JOIN gnd_egbse.tblYearMonth y ON s.Date BETWEEN y.FromDate AND y.ToDate AND y.MonthID IS NOT NULL
WHERE s.IsOff=0 AND EXISTS (
 SELECT 1 FROM gnd_hrcio.tblCardLog c WHERE c.EmployeeID=s.EmployeeID AND c.DayDate=s.Date AND c.IsDisable=0
)
GROUP BY s.EmployeeID,e.EmployeeCode,y.ID;""",
"FINAL-U44": """SELECT w.EmployeeID,e.EmployeeCode,w.YearMonthID,y.[Year],y.MonthID,
       w.SystemSaatEzafeKarcdur / 60.0 AS UnroundedRegularOvertimeHours,
       w.SystemSaatEzafekarTatilicdur / 60.0 AS UnroundedHolidayOvertimeHours
FROM [gnd_hrpyr].[tblWorkTime] AS w
INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=w.EmployeeID
INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID;""",
"FINAL-U45": """SELECT p.ID AS PackingID,p.DoneDate AS PackingDate,p.Serial
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
  AND ISNULL(production.HighestProductionCode,0)<>99;""",
"FINAL-U46": """SELECT i.ID AS PurchaseInvoiceID,i.Code AS PurchaseInvoiceCode,d.IG AS InvoiceLineID,
       d.GoodID,g.GoodCode,g.Farsi AS GoodName,d.Qty,d.InvValue AS WarehouseAmount,d.UnitPrice,
       d.InvValue/NULLIF(d.Qty,0) AS WarehouseAmountPerUnit
FROM [gnd_scpch].[tblPurchaseInvoiceGoodAndService] AS i
INNER JOIN [gnd_scpch].[tblPurchaseInvoiceGoodDetailEnter] AS d
  ON d.PurchaseInvoiceGoodAndServiceID=i.ID
LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.GoodID
WHERE d.UnitPrice IS NULL OR d.UnitPrice=0;""",
"FINAL-U47": """SELECT i.ID AS PurchaseInquiryID,i.Code AS PurchaseInquiryCode,i.DoneDate,
       r.ID AS PurchaseRequestID,r.RequestEmployeeID,e.EmployeeCode
FROM [gnd_scpch].[tblPurchaseInquiry] AS i
INNER JOIN [gnd_scpch].[tblPurchaseOrder] AS o ON o.ID=i.PurchaseOrderID
INNER JOIN [gnd_scpch].[tblPurchaseOrderDetail] AS od ON od.PurchaseOrderID=o.ID
INNER JOIN [gnd_scpch].[tblPurchaseRequestDetail] AS rd ON rd.IG=od.PurchaseRequestDetailIG
INNER JOIN [gnd_scpch].[tblPurchaseRequest] AS r ON r.ID=rd.PurchaseRequestID
LEFT JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=r.RequestEmployeeID
GROUP BY i.ID,i.Code,i.DoneDate,r.ID,r.RequestEmployeeID,e.EmployeeCode;""",
"FINAL-U48": """WITH CurrentWork AS (
 SELECT w.*,ROW_NUMBER() OVER(PARTITION BY w.FormID ORDER BY w.ID DESC) AS rn
 FROM [gnd_egwfm].[tblWork] AS w WHERE w.FormTypeID=1927645
)
SELECT i.ID AS PurchaseInquiryID,i.Code AS PurchaseInquiryCode,i.DoneDate,
       w.CurrentUserID,c.Farsi AS CurrentApprover,w.CurrentProcessStepID,
       ps.Name AS CurrentApprovalStep,w.RunStatusTypeID
FROM [gnd_scpch].[tblPurchaseInquiry] AS i
LEFT JOIN CurrentWork AS w ON w.FormID=i.ID AND w.rn=1 AND w.RunStatusTypeID IN (0,1)
LEFT JOIN [gnd_egbse].[tblContact] AS c ON c.ID=w.CurrentUserID
LEFT JOIN [gnd_egbpm].[tblProcessStep] AS ps ON ps.ID=w.CurrentProcessStepID;""",
"FINAL-U49": """WITH                                            c
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
ORDER BY p.Farsi;""",
"FINAL-U50": """SELECT i.ID AS SalesInvoiceID,i.Code AS InvoiceNumber,i.DoneDate AS InvoiceDate,
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
LEFT JOIN [gnd_crsls].[tblSellableService] AS s ON s.ID=d.SellableServiceID;""",
})

FINAL_UNSEEN_GOLD_CASES = [dict(case, reference_sql=SQL[case["id"]]) for case in FINAL_UNSEEN_CASES]
