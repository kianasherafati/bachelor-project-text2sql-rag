"""Bounded SELECT-only validation for the frozen real-world ERP benchmark.

Run with .venv/Scripts/python.exe -B evaluation/validate_real_world_gold.py.
--check-only checks definitions offline. Successful unchanged cases are reused.
No result rows, parameter business identifiers, or credentials are persisted.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation"))
from validate_text2sql_gold import connect_read_only, safe_error

FROZEN = ROOT / "evaluation/real_world_text2sql_benchmark.py"
EVIDENCE = ROOT / "evaluation/real_world_gold_validation.json"
GOLD = ROOT / "evaluation/real_world_gold_benchmark.py"
REPORT = ROOT / "evaluation/REAL_WORLD_GOLD_VALIDATION.md"
SAMPLE_LIMIT = 10

REFERENCES = json.loads(r'''{
  "REAL-C01": {
    "reference_sql": "SELECT t.ID AS TransactionID,t.Code AS TransactionCode,t.DocDate,\n       t.PeriodSpecID,d.IG AS AccountingLineID,d.AccountID,d.Description,\n       d.Debit,d.Credit\nFROM [gnd_fiaci].[tblTrans] AS t\nINNER JOIN [gnd_fiaci].[tblTransDetail] AS d ON d.TransID=t.ID\nWHERE t.PeriodSpecID=@FinancialPeriodID AND d.AccountID=@AccountID\n  AND EXISTS (\n      SELECT 1 FROM [gnd_fiaci].[tblTransDetailDetail] AS x\n      WHERE x.TransDetailIG=d.IG AND x.FormTypeID=12261\n        AND x.FormID=@ProjectID\n  );",
    "parameter_types": {
      "FinancialPeriodID": "int",
      "AccountID": "int",
      "ProjectID": "int"
    },
    "validation_parameter_selector": "SELECT TOP (1) t.PeriodSpecID AS FinancialPeriodID,d.AccountID,x.FormID AS ProjectID\nFROM gnd_fiaci.tblTransDetailDetail x JOIN gnd_fiaci.tblTransDetail d ON d.IG=x.TransDetailIG JOIN gnd_fiaci.tblTrans t ON t.ID=d.TransID\nWHERE x.FormTypeID=12261 AND t.PeriodSpecID IS NOT NULL AND d.AccountID IS NOT NULL ORDER BY x.IG",
    "interpretation_notes": [
      "Identifiers are supplied parameters. Project form type 12261 is verified schema configuration. EXISTS preserves one result per accounting line."
    ],
    "logical_joins": [
      "Typed project dimension: FormTypeID=12261 and FormID=@ProjectID; no direct project-table FK."
    ],
    "expected_result_columns": [
      "TransactionID",
      "TransactionCode",
      "DocDate",
      "PeriodSpecID",
      "AccountingLineID",
      "AccountID",
      "Description",
      "Debit",
      "Credit"
    ]
  },
  "REAL-C02": {
    "reference_sql": "SELECT s.ID AS ServiceInvoiceID,s.TotalVat AS InvoiceVAT,\n       t.ID AS AccountingTransactionID,v.PostedVAT,v.VATPostingLineCount,\n       s.TotalVat-v.PostedVAT AS VATDifference\nFROM [gnd_scpch].[tblServiceInvoice] AS s\nLEFT JOIN [gnd_fiaci].[tblTrans] AS t\n  ON t.FormTypeID=1208179 AND t.FormID=s.ID\nOUTER APPLY (\n    SELECT SUM(d.Debit-d.Credit) AS PostedVAT,COUNT_BIG(*) AS VATPostingLineCount\n    FROM [gnd_fiaci].[tblTransDetail] AS d\n    WHERE d.TransID=t.ID AND d.AccountID=348\n) AS v\nWHERE s.ID=@ServiceInvoiceID;",
    "parameter_types": {
      "ServiceInvoiceID": "int"
    },
    "validation_parameter_selector": "SELECT TOP (1) s.ID AS ServiceInvoiceID FROM gnd_scpch.tblServiceInvoice s\nWHERE s.TotalVat>0 AND EXISTS(SELECT 1 FROM gnd_fiaci.tblTrans t WHERE t.FormTypeID=1208179 AND t.FormID=s.ID) ORDER BY s.ID",
    "interpretation_notes": [
      "VAT account 348 and source form type 1208179 are verified configuration, not sampled row IDs. Posted VAT is net debit minus credit on VAT lines only, reported per associated journal. Missing VAT postings remain NULL, not zero."
    ],
    "logical_joins": [
      "tblTrans.FormID=tblServiceInvoice.ID when tblTrans.FormTypeID=1208179."
    ],
    "expected_result_columns": [
      "ServiceInvoiceID",
      "InvoiceVAT",
      "AccountingTransactionID",
      "PostedVAT",
      "VATPostingLineCount",
      "VATDifference"
    ]
  },
  "REAL-C03": {
    "reference_sql": "SELECT d.PurchaseRequestID,d.IG AS PurchaseRequestLineID,d.Sequence,\n       d.RequestReason,d.ConsumptionPurpose\nFROM [gnd_scpch].[tblPurchaseRequestDetail] AS d;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [],
    "logical_joins": [],
    "expected_result_columns": [
      "PurchaseRequestID",
      "PurchaseRequestLineID",
      "Sequence",
      "RequestReason",
      "ConsumptionPurpose"
    ]
  },
  "REAL-C04": {
    "reference_sql": "WITH StageLines AS (\n    SELECT N'Pro forma invoice' AS DocumentStage,p.ID AS ProformaID,\n           CAST(NULL AS int) AS CommercialInvoiceID,CAST(NULL AS int) AS WaybillID,\n           CAST(NULL AS int) AS ReceiptID,p.ID AS DocumentID,\n           CONVERT(nvarchar(100),d.IG) AS DocumentLineID,d.Sequence,\n           d.GoodID,d.Qty,\n           CONVERT(nvarchar(max),o.RegistrationNumber) AS OrderRegistrationNumber,\n           CAST(NULL AS nvarchar(max)) AS CustomsDeclarationNumber\n    FROM [gnd_scimp].[tblProformaInvoice] AS p\n    INNER JOIN [gnd_scimp].[tblProformaInvoiceDetail] AS d ON d.ProformaInvoiceID=p.ID\n    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n    UNION ALL\n    SELECT N'Commercial invoice',p.ID,c.ID,NULL,NULL,c.ID,\n           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n           CONVERT(nvarchar(max),o.RegistrationNumber),\n           CONVERT(nvarchar(max),k.CottageNumber)\n    FROM [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c\n    INNER JOIN [gnd_scimp].[tblCurrencyPurchaseInvoiceDetail] AS d ON d.CurrencyPurchaseInvoiceID=c.ID\n    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON p.ID=c.ProformaInvoiceID\n    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=c.ID\n    UNION ALL\n    SELECT N'Domestic waybill',p.ID,c.ID,w.ID,NULL,w.ID,\n           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n           CONVERT(nvarchar(max),o.RegistrationNumber),\n           CONVERT(nvarchar(max),k.CottageNumber)\n    FROM [gnd_sclog].[tblInternalBillOfLading] AS w\n    INNER JOIN [gnd_sclog].[tblInternalBillOfLadingGoodDetail] AS d ON d.BillOfLadingID=w.ID\n    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=w.CottageID\n    LEFT JOIN [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c ON c.ID=k.ID\n    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON p.ID=c.ProformaInvoiceID\n    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n    UNION ALL\n    SELECT N'Goods receipt',p.ID,c.ID,w.ID,r.ID,r.ID,\n           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n           CONVERT(nvarchar(max),o.RegistrationNumber),\n           CONVERT(nvarchar(max),k.CottageNumber)\n    FROM [gnd_scimp].[tblForeignReceiveGoods] AS r\n    INNER JOIN [gnd_scimp].[tblForeignReceiveGoodsDetail] AS d ON d.ForeignReceiveGoodsID=r.ID\n    LEFT JOIN [gnd_sclog].[tblInternalBillOfLading] AS w ON w.ID=r.ID\n    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=w.CottageID\n    LEFT JOIN [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c ON c.ID=k.ID\n    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON p.ID=c.ProformaInvoiceID\n    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n)\nSELECT s.DocumentStage,s.ProformaID,s.CommercialInvoiceID,s.WaybillID,s.ReceiptID,\n       s.DocumentID,s.DocumentLineID,s.Sequence,s.GoodID,s.Qty AS RecordedQuantity,\n       g.UnitTypeID,u.Farsi AS UnitLabel,u.English AS UnitEnglish,\n       s.OrderRegistrationNumber,s.CustomsDeclarationNumber\nFROM StageLines AS s\nLEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=s.GoodID\nLEFT JOIN [gnd_spgod].[tblGoodUnitTypeL] AS u ON u.ID=g.UnitTypeID;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [
      "UNION ALL preserves one row per recorded stage detail. No sibling detail joins or cross-stage sums. Pro forma rows have no downstream customs number attached: one pro forma can have multiple subsequent invoices. Optional ancestry and lookup joins preserve lines with missing metadata. Units are current item-master units; no conversion or invented historical unit is applied."
    ],
    "logical_joins": [
      "tblCottage.ID=tblCurrencyPurchaseInvoice.ID via verified FK inheritance chain Cottage -> WareHouseBill -> BillOfLading -> PackingList -> CurrencyPurchaseInvoice; intermediate business tables are not queried."
    ],
    "expected_result_columns": [
      "DocumentStage",
      "ProformaID",
      "CommercialInvoiceID",
      "WaybillID",
      "ReceiptID",
      "DocumentID",
      "DocumentLineID",
      "Sequence",
      "GoodID",
      "RecordedQuantity",
      "UnitTypeID",
      "UnitLabel",
      "UnitEnglish",
      "OrderRegistrationNumber",
      "CustomsDeclarationNumber"
    ]
  },
  "REAL-C05": {
    "reference_sql": "SELECT d.ExitID,d.IG AS WarehouseIssueLineID,d.Sequence,d.CredbGoodID AS GoodID,\n       g.GoodCode,d.Qty\nFROM [gnd_scinv].[tblExitDetail] AS d\nLEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.CredbGoodID;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [],
    "logical_joins": [],
    "expected_result_columns": [
      "ExitID",
      "WarehouseIssueLineID",
      "Sequence",
      "GoodID",
      "GoodCode",
      "Qty"
    ]
  },
  "REAL-C06": {
    "reference_sql": "SELECT s.ID AS AssignmentID,s.ShiftID,s.FromDate,s.EndDateStatus\nFROM [gnd_hrcio].[tblEmployeeShift] AS s\nINNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=s.EmployeeID\nWHERE e.ID=@EmployeeID AND e.IsLeaved=1\nORDER BY s.FromDate,s.ID;",
    "parameter_types": {
      "EmployeeID": "int"
    },
    "validation_parameter_selector": "SELECT TOP (1) e.ID AS EmployeeID FROM gnd_hrprs.tblEmployee e\nWHERE e.IsLeaved=1 AND EXISTS(SELECT 1 FROM gnd_hrcio.tblEmployeeShift s WHERE s.EmployeeID=e.ID) ORDER BY e.ID",
    "interpretation_notes": [
      "Return every dated assignment for the supplied former employee, without filtering to current assignments. IsLeaved defines former status; NULL EndDateStatus remains unknown."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "AssignmentID",
      "ShiftID",
      "FromDate",
      "EndDateStatus"
    ]
  },
  "REAL-C07": {
    "reference_sql": "SELECT b.ID AS SettlementID,N'Stored field' AS ComponentSource,\n       v.Component AS ComponentKey,v.Component AS ComponentLabel,\n       CAST(NULL AS nvarchar(100)) AS ParameterLineID,\n       v.Amount AS RecordedAmount,CAST(NULL AS money) AS DebitAmount,\n       CAST(NULL AS money) AS CreditAmount\nFROM [gnd_hrpyr].[tblBonusBill] AS b\nCROSS APPLY (VALUES\n    (N'Eidi',b.[Eidi]),\n    (N'Sanavat',b.[Sanavat]),\n    (N'CredbBazKharidMorkhasi',b.[CredbBazKharidMorkhasi]),\n    (N'CreditBazKharidMorkhasi',b.[CreditBazKharidMorkhasi]),\n    (N'RemainedDebit',b.[RemainedDebit]),\n    (N'RemainedCredit',b.[RemainedCredit]),\n    (N'Maliat',b.[Maliat]),\n    (N'MandeGhabelePardakht',b.[MandeGhabelePardakht]),\n    (N'JameMashmoulMaliat',b.[JameMashmoulMaliat]),\n    (N'JameEzafat',b.[JameEzafat]),\n    (N'JameKosourat',b.[JameKosourat]),\n    (N'SahmSandogh',b.[SahmSandogh]),\n    (N'UniformCost',b.[UniformCost]),\n    (N'ComplementallyInsurance',b.[ComplementallyInsurance]),\n    (N'JameDaryafti',b.[JameDaryafti]),\n    (N'JameKasrshavande',b.[JameKasrshavande]),\n    (N'PurchasableService',b.[PurchasableService])\n) AS v(Component,Amount)\nWHERE b.ID=@SettlementID\nUNION ALL\nSELECT b.ID,N'Parameter row',CONVERT(nvarchar(100),d.MonthlyParameterTypeID),\n       t.Description,CONVERT(nvarchar(100),d.IG),NULL,d.DebitAccValue,d.CreditAccValue\nFROM [gnd_hrpyr].[tblBonusBill] AS b\nINNER JOIN [gnd_hrpyr].[tblBonusBillParameter] AS d ON d.BonusBillID=b.ID\nLEFT JOIN [gnd_hrpyr].[tblMonthlyParameterType] AS t ON t.ID=d.MonthlyParameterTypeID\nWHERE b.ID=@SettlementID;",
    "parameter_types": {
      "SettlementID": "int"
    },
    "validation_parameter_selector": "SELECT TOP (1) b.ID AS SettlementID FROM gnd_hrpyr.tblBonusBill b\nWHERE EXISTS(SELECT 1 FROM gnd_hrpyr.tblBonusBillParameter d WHERE d.BonusBillID=b.ID) ORDER BY b.ID",
    "interpretation_notes": [
      "Includes all stored monetary fields, including totals as separately labeled stored fields, plus actual parameter rows. Do not add these output amounts together: stored totals can overlap component amounts. NULL and zero remain distinct. RuzeKarkard is a worked-days measure despite its SQL money type and is excluded. Printed application-only lines are not generated."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "SettlementID",
      "ComponentSource",
      "ComponentKey",
      "ComponentLabel",
      "ParameterLineID",
      "RecordedAmount",
      "DebitAmount",
      "CreditAmount"
    ]
  },
  "REAL-C08": {
    "reference_sql": "SELECT i.ID AS InterweavingID,i.InterweavingCode,t.ID AS PackagingTypeID,\n       t.Farsi AS PackagingLabel,\n       SUM(p.NetWeight) AS TotalRecordedNetWeight\nFROM [gnd_scprd].[tblPacking] AS p\nINNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=p.InterWeavingID\nINNER JOIN [gnd_spgod].[tblPackagingType] AS t ON t.ID=p.PackagingTypeID\nWHERE t.ID IN (1,2,3)\nGROUP BY i.ID,i.InterweavingCode,t.ID,t.Farsi;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [
      "Verified packaging IDs: 1=pallet, 2=carton, 3=bag. Sum recorded NetWeight only. All-NULL groups remain NULL; NULL readings do not become invented zeros."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "InterweavingID",
      "InterweavingCode",
      "PackagingTypeID",
      "PackagingLabel",
      "TotalRecordedNetWeight"
    ]
  },
  "REAL-C09": {
    "reference_sql": "SELECT e.ID AS EquipmentID,e.NameInEnglish AS EquipmentName,\n       k.English AS EquipmentKind,r.ID AS RoutineID,r.English AS RoutineName,\n       s.ID AS SensorID,s.Description AS SensorDescription,\n       f.ID AS FeedbackID,c.IG AS ReadingID,f.EndDate AS GrindingCompletionDate,\n       c.SensorValue AS CotDiameter\nFROM [gnd_amspt].[tblFeedbackCheckList] AS c\nINNER JOIN [gnd_amspt].[tblFeedback] AS f ON f.ID=c.FeedbackID\nINNER JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=f.RoutineID\nINNER JOIN [gnd_amast].[tblSensor] AS s ON s.ID=c.SensorID\nINNER JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=f.EquipmentID\nINNER JOIN [gnd_amast].[tblEquipmentKind] AS k ON k.ID=e.EquipmentKindID\nWHERE e.ID=@EquipmentID AND k.ID=56 AND r.ID=403 AND s.ID=30\n  AND f.EndDate>=@FromDate AND f.EndDate<DATEADD(day,1,@ThroughDate)\n  AND c.SensorValue BETWEEN @MinimumDiameter AND @MaximumDiameter\nORDER BY f.EndDate,c.IG;",
    "parameter_types": {
      "EquipmentID": "int",
      "FromDate": "date",
      "ThroughDate": "date",
      "MinimumDiameter": "decimal",
      "MaximumDiameter": "decimal"
    },
    "validation_parameter_selector": "SELECT TOP (1) f.EquipmentID,CONVERT(date,f.EndDate) AS FromDate,CONVERT(date,f.EndDate) AS ThroughDate,c.SensorValue AS MinimumDiameter,c.SensorValue AS MaximumDiameter\nFROM gnd_amspt.tblFeedbackCheckList c JOIN gnd_amspt.tblFeedback f ON f.ID=c.FeedbackID JOIN gnd_amast.tblEquipment e ON e.ID=f.EquipmentID\nWHERE f.RoutineID=403 AND c.SensorID=30 AND e.EquipmentKindID=56 AND c.SensorValue IS NOT NULL AND f.EndDate IS NOT NULL ORDER BY c.IG",
    "interpretation_notes": [
      "Equipment kind 56, routine 403 and sensor 30 are verified domain configuration. Date range is inclusive of both calendar dates; diameter endpoints inclusive. Individual readings are retained, without latest-only selection."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "EquipmentID",
      "EquipmentName",
      "EquipmentKind",
      "RoutineID",
      "RoutineName",
      "SensorID",
      "SensorDescription",
      "FeedbackID",
      "ReadingID",
      "GrindingCompletionDate",
      "CotDiameter"
    ]
  },
  "REAL-C10": {
    "reference_sql": "SELECT w.ID AS WorkOrderID,w.Code,w.WorkOrderTitle,w.SuggestedExecutionDate\nFROM [gnd_amspt].[tblWorkOrder] AS w\nWHERE w.SuggestedExecutionDate>=@FromDate\n  AND w.SuggestedExecutionDate<DATEADD(day,1,@ThroughDate);",
    "parameter_types": {
      "FromDate": "date",
      "ThroughDate": "date"
    },
    "validation_parameter_selector": "SELECT TOP (1) CONVERT(date,SuggestedExecutionDate) AS FromDate,CONVERT(date,SuggestedExecutionDate) AS ThroughDate FROM gnd_amspt.tblWorkOrder WHERE SuggestedExecutionDate IS NOT NULL ORDER BY ID",
    "interpretation_notes": [
      "Inclusive calendar-date range; use SuggestedExecutionDate, not TargetDate."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "WorkOrderID",
      "Code",
      "WorkOrderTitle",
      "SuggestedExecutionDate"
    ]
  },
  "REAL-C11": {
    "reference_sql": "SELECT b.ID AS BankGuaranteeID,b.AccValue AS GuaranteeAmount,\n       b.DepositValue AS DepositAmount,\n       b.AccValue-b.DepositValue AS NetAmount\nFROM [gnd_firpd].[tblBankGuaranty] AS b;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [],
    "logical_joins": [],
    "expected_result_columns": [
      "BankGuaranteeID",
      "GuaranteeAmount",
      "DepositAmount",
      "NetAmount"
    ]
  },
  "REAL-C14": {
    "reference_sql": "WITH CurrentPeriods AS (\n    SELECT p.ID,p.BeginDate,p.EndDate\n    FROM [gnd_fiaci].[tblPeriodSpec] AS p\n    WHERE CONVERT(date,GETDATE()) BETWEEN p.BeginDate AND p.EndDate\n), Movements AS (\n    SELECT p.ID AS PeriodID,e.CredbInventoryID AS InventoryID,\n           d.CredbGoodID AS GoodID,COALESCE(d.Qty,0) AS SignedQuantity\n    FROM [gnd_scinv].[tblEnter] AS e\n    INNER JOIN [gnd_scinv].[tblEnterDetail] AS d ON d.EnterID=e.ID\n    INNER JOIN CurrentPeriods AS p ON e.DoneDate BETWEEN p.BeginDate AND p.EndDate\n    WHERE e.Code IS NOT NULL\n    UNION ALL\n    SELECT p.ID,e.CredbInventoryID,d.CredbGoodID,-COALESCE(d.Qty,0)\n    FROM [gnd_scinv].[tblExit] AS e\n    INNER JOIN [gnd_scinv].[tblExitDetail] AS d ON d.ExitID=e.ID\n    INNER JOIN CurrentPeriods AS p ON e.DoneDate BETWEEN p.BeginDate AND p.EndDate\n    WHERE e.Code IS NOT NULL\n), Balances AS (\n    SELECT PeriodID,InventoryID,GoodID,SUM(SignedQuantity) AS PostedStock\n    FROM Movements\n    GROUP BY PeriodID,InventoryID,GoodID\n)\nSELECT DISTINCT i.ID AS InterweavingID,i.InterweavingCode\nFROM Balances AS b\nINNER JOIN [gnd_spgod].[tblGood] AS g ON g.ID=b.GoodID\nINNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=g.InterweavingID\nWHERE b.PostedStock>0 AND NULLIF(LTRIM(RTRIM(g.LotNumber)),N'') IS NOT NULL;",
    "parameter_types": {},
    "validation_parameter_selector": null,
    "interpretation_notes": [
      "Current period is evaluated using SQL Server GETDATE(). Posted means non-NULL movement Code; quantity NULL handling follows the inspected stock logic. Balance is per item, warehouse and current period. Do not subtract demand, reservations or allocations, or add undocumented warehouse restrictions. Results are date-dependent."
    ],
    "logical_joins": [
      "Movement DoneDate lies within PeriodSpec.BeginDate/EndDate (date-range relationship).",
      "Good.InterweavingID=Interweaving.ID uses their common Project key and verified subtype semantics; no direct FK between these two tables."
    ],
    "expected_result_columns": [
      "InterweavingID",
      "InterweavingCode"
    ]
  },
  "REAL-C15": {
    "reference_sql": "SELECT w.YearMonthID,y.FromDate AS PayrollMonthStart,y.ToDate AS PayrollMonthEnd,\n       w.RemainedLeave AS RecordedLeaveBalanceDays\nFROM [gnd_hrpyr].[tblWorkTime] AS w\nINNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID\nWHERE w.EmployeeID=@EmployeeID AND w.YearMonthID=@PayrollMonthID;",
    "parameter_types": {
      "EmployeeID": "int",
      "PayrollMonthID": "int"
    },
    "validation_parameter_selector": "SELECT TOP (1) w.EmployeeID,w.YearMonthID AS PayrollMonthID FROM gnd_hrpyr.tblWorkTime w ORDER BY w.ID DESC",
    "interpretation_notes": [
      "Return physically stored days for the selected employee/month. NULL is not recorded and remains NULL. Do not recalculate leave or claim correctness of the original accrual calculation."
    ],
    "logical_joins": [],
    "expected_result_columns": [
      "YearMonthID",
      "PayrollMonthStart",
      "PayrollMonthEnd",
      "RecordedLeaveBalanceDays"
    ]
  }
}''')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    paths = [FROZEN]
    for directory in ("retrieval", "schema_extraction"):
        paths.extend(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix.lower() in {".py", ".json", ".index", ".pkl", ".npy", ".faiss", ".bin", ".pt", ".safetensors"})
    paths.extend(ROOT / "evaluation" / name for name in (
        "gold_sql_definitions.py", "validate_text2sql_gold.py",
        "text2sql_gold_benchmark.py", "text2sql_gold_validation.json",
        "TEXT2SQL_GOLD_VALIDATION.md"))
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths)) if p.exists()}


def table_names(sql):
    return sorted(set(".".join(match) for match in
                      re.findall(r"\[(gnd_[A-Za-z0-9_]+)\]\.\[([A-Za-z0-9_]+)\]", sql)))


def assert_select(sql, reference=False):
    clean = re.sub(r"N?'(?:''|[^'])*'", "''", sql)
    if not re.match(r"^\s*(SELECT|WITH)\b", clean, re.I):
        raise ValueError("Only SELECT or SELECT CTEs are allowed")
    # Curated reference statements contain no comments. Reject them rather than
    # attempting to interpret executable tokens hidden behind comment boundaries.
    if any(marker in clean for marker in ("--", "/*", "*/")):
        raise ValueError("Comments are outside the curated SELECT-only scope")
    if re.search(r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|EXEC|EXECUTE|INTO|TRUNCATE|DBCC|GRANT|REVOKE|DENY|OPENROWSET|OPENQUERY|WAITFOR|BACKUP|RESTORE|BULK|USE|SET|DECLARE|BEGIN|COMMIT|ROLLBACK|SHUTDOWN|RECONFIGURE|KILL)\b", clean, re.I):
        raise ValueError("Statement outside SELECT-only scope")
    if ";" in clean.strip().rstrip(";"):
        raise ValueError("Multiple statements are prohibited")
    if reference and re.search(r"\b(TOP|OFFSET|FETCH)\b", clean, re.I):
        raise ValueError("Reference SQL may not impose a row cap")


def check_definitions():
    frozen = runpy.run_path(str(FROZEN))["tests"]
    assert len(frozen) == 13
    assert Counter(t["difficulty"] for t in frozen) == {"easy": 4, "medium": 5, "hard": 4}
    assert set(REFERENCES) == {t["id"] for t in frozen}
    for t in frozen:
        ref = REFERENCES[t["id"]]
        assert_select(ref["reference_sql"], reference=True)
        assert set(table_names(ref["reference_sql"])) == set(t["expected_tables"]), t["id"]
        assert t["expected_table_count"] == len(t["expected_tables"])
        assert set(re.findall(r"@([A-Za-z][A-Za-z0-9_]*)", ref["reference_sql"])) == set(ref["parameter_types"])
        if ref["validation_parameter_selector"]:
            assert_select(ref["validation_parameter_selector"])
    return frozen


def schema_evidence(connection, frozen):
    evidence = {}
    names = sorted({name for t in frozen for name in t["expected_tables"]})
    cur = connection.cursor()
    for name in names:
        cur.execute("""SELECT c.name,t.name,c.is_nullable,c.is_computed
            FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
            WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id""", name)
        columns = [dict(zip(("name","data_type","nullable","computed"), row))
                   for row in cur.fetchmany(300)]
        cur.cancel()
        cur.execute("""SELECT c.name FROM sys.indexes i
            JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE i.object_id=OBJECT_ID(?) AND i.is_primary_key=1 ORDER BY ic.key_ordinal""", name)
        pk = [r[0] for r in cur.fetchmany(20)]
        cur.cancel()
        cur.execute("""SELECT fk.name,pc.name,
            OBJECT_SCHEMA_NAME(fk.referenced_object_id)+'.'+OBJECT_NAME(fk.referenced_object_id),
            rc.name,fk.is_disabled,fk.is_not_trusted
            FROM sys.foreign_keys fk
            JOIN sys.foreign_key_columns fc ON fc.constraint_object_id=fk.object_id
            JOIN sys.columns pc ON pc.object_id=fc.parent_object_id AND pc.column_id=fc.parent_column_id
            JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
            WHERE fk.parent_object_id=OBJECT_ID(?) ORDER BY fk.name,fc.constraint_column_id""", name)
        fks = [dict(zip(("constraint","source_column","target_table","target_column","disabled","untrusted"), row))
               for row in cur.fetchmany(300)]
        cur.cancel()
        if not columns:
            raise ValueError("Required expected table is inaccessible")
        evidence[name] = {"columns": columns, "primary_key": pk, "foreign_keys": fks}
    cur.close()
    return evidence


def validate_case(connection, case):
    ref = REFERENCES[case["id"]]
    result = {
        "id": case["id"], "reference_sql_sha256": hashlib.sha256(ref["reference_sql"].encode()).hexdigest(),
        "expected_tables_actually_referenced": table_names(ref["reference_sql"]),
        "logical_joins": ref["logical_joins"], "interpretation_notes": ref["interpretation_notes"],
        "parameter_types": ref["parameter_types"],
        "validation_parameter_selection": ref["validation_parameter_selector"],
        "parameter_selection_scope": "Deterministic bounded existing-row example for validation only; not part of reference SQL.",
        "bound_parameter_values_persisted": False,
        "execution_valid": False, "result_columns": [], "empty": None,
        "row_count": "not fully counted", "row_count_exact": False,
        "rows_fetched": 0, "fetch_limit": SAMPLE_LIMIT,
        "validation_scope": "Execution and at most the first 10 returned rows; no full-result semantic certification.",
    }
    cur = connection.cursor()
    started = time.monotonic()
    try:
        values = {}
        if ref["validation_parameter_selector"]:
            cur.execute(ref["validation_parameter_selector"])
            names = [c[0] for c in cur.description]
            row = cur.fetchone()
            cur.cancel()
            if row is None:
                result["failure_reason"] = "No parameter example available; reference query was not executed."
                return result
            values = dict(zip(names, row))
            assert set(values) == set(ref["parameter_types"])
        ordered = []
        def bind(match):
            ordered.append(values[match.group(1)])
            return "?"
        executable = re.sub(r"@([A-Za-z][A-Za-z0-9_]*)", bind, ref["reference_sql"])
        if ordered:
            cur.execute(executable, *ordered)
        else:
            cur.execute(executable)
        columns = [c[0] for c in cur.description]
        rows = cur.fetchmany(SAMPLE_LIMIT)
        cur.cancel()
        result.update({
            "execution_valid": True, "result_columns": columns,
            "result_columns_match": columns == ref["expected_result_columns"],
            "empty": len(rows) == 0, "rows_fetched": len(rows),
            "row_count": len(rows) if len(rows) < SAMPLE_LIMIT else "not fully counted",
            "row_count_exact": len(rows) < SAMPLE_LIMIT,
            "row_count_lower_bound": len(rows),
            "sample_null_counts": {name: sum(r[i] is None for r in rows) for i, name in enumerate(columns)},
            "sample_blank_string_counts": {name: sum(isinstance(r[i], str) and not r[i].strip() for r in rows) for i, name in enumerate(columns)},
        })
        if not result["result_columns_match"]:
            result["failure_reason"] = "Returned column names differ from the declared reference output."
        if case["id"] == "REAL-C07":
            result["sample_zero_amount_cells"] = sum(
                r[i] == 0 for r in rows for i, name in enumerate(columns)
                if name in ("RecordedAmount", "DebitAmount", "CreditAmount") and r[i] is not None)
    except Exception as error:
        result["error"] = safe_error(error)
        try:
            cur.cancel()
        except Exception:
            pass
    finally:
        cur.close()
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["validated_at_utc"] = datetime.now(timezone.utc).isoformat()
    return result


def summary_for(results):
    values = list(results.values())
    return {
        "case_count": 13,
        "attempted": len(values),
        "executable_queries": sum(r["execution_valid"] for r in values),
        "non_empty_queries": sum(r["execution_valid"] and r["empty"] is False for r in values),
        "empty_queries": sum(r["execution_valid"] and r["empty"] is True for r in values),
        "failed_queries": [r["id"] for r in values if not r["execution_valid"]],
        "result_column_mismatches": [r["id"] for r in values if r["execution_valid"] and not r.get("result_columns_match")],
        "logical_join_cases": [r["id"] for r in values if r["logical_joins"]],
        "exact_table_sets_match": True,
        "sample_rows_persisted": False,
        "retrieval_executed": False,
        "model_generation_executed": False,
    }


def write_outputs(frozen, payload):
    payload["summary"] = summary_for(payload["cases"])
    EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gold = []
    for case in frozen:
        ref = REFERENCES[case["id"]]
        result = payload["cases"].get(case["id"], {})
        gold.append({
            **case, "reference_sql": ref["reference_sql"],
            "parameters": ref["parameter_types"],
            "reference_interpretation_notes": ref["interpretation_notes"],
            "logical_joins": ref["logical_joins"],
            "execution_valid": result.get("execution_valid", False),
            "result_columns": result.get("result_columns", []),
            "validation": result,
        })
    GOLD.write_text(
        '"""Validated reference definitions for the frozen real-world ERP benchmark.\n'
        'Named SQL parameters are bound externally; validation fetches at most 10 rows.\n'
        'No sampled result rows or personal parameter identifiers are stored.\n"""\n\n'
        + "validation_summary = " + pprint.pformat(payload["summary"], sort_dicts=False, width=100)
        + "\n\ntests = " + pprint.pformat(gold, sort_dicts=False, width=100) + "\n",
        encoding="utf-8")
    s = payload["summary"]
    lines = [
        "# Real-world gold SQL validation", "",
        f"Target: {payload['target_database']}. Validated with a read-only account.",
        f"Executable: **{s['executable_queries']}/13**; non-empty: **{s['non_empty_queries']}**; empty: **{s['empty_queries']}**.",
        "", "Each reference SELECT is unbounded; only the client fetch is capped at 10 rows.",
        "Fewer than 10 rows proves exhaustion for that execution. A 10-row sample is recorded as not fully counted.",
        "Parameter-dependent outcomes apply to documented diagnostic example bindings, not every possible parameter value.",
        "Example business identifiers and result rows are not persisted. Parameter selector SQL is included in the JSON for reproducibility.",
        "", "| Case | Executes | Empty | Rows | Exact | Columns |",
        "|---|---|---|---|---|---|",
    ]
    for case in frozen:
        r = payload["cases"].get(case["id"], {})
        lines.append(f"| {case['id']} | {r.get('execution_valid',False)} | {r.get('empty')} | {r.get('row_count','not attempted')} | {r.get('row_count_exact',False)} | {', '.join(r.get('result_columns',[]))} |")
    lines += ["", "## Interpretation and sample limitations", ""]
    for case in frozen:
        ref = REFERENCES[case["id"]]
        r = payload["cases"].get(case["id"], {})
        lines.append(f"### {case['id']}\n")
        lines.append(case["question"] + "\n")
        lines.append("Expected/referenced tables: " + ", ".join(case["expected_tables"]) + ".\n")
        for note in ref["interpretation_notes"] + ref["logical_joins"]:
            lines.append("- " + note)
        nulls = {k:v for k,v in r.get("sample_null_counts",{}).items() if v}
        blanks = {k:v for k,v in r.get("sample_blank_string_counts",{}).items() if v}
        if nulls:
            lines.append(f"- NULL counts in the bounded sample ({r.get('rows_fetched',0)} rows): {nulls}. These are not whole-table completeness measurements.")
        if blanks:
            lines.append(f"- Blank-string counts in the same sample: {blanks}.")
        if r.get("error"):
            lines.append("- Execution failure: " + json.dumps(r["error"]))
        lines.append("")
    lines += [
        "## Scope and integrity", "",
        "All reference SQL table sets exactly match the frozen expected sets (40 unique tables).",
        "REAL-C04 remains a 12-table query; its frozen Top-10 ceiling remains 10/12.",
        "The frozen definition, prior gold benchmark, retrieval code and artifacts were hash-checked and left unchanged.",
        "No retrieval or model generation ran. No business writes, DDL, business stored procedures, commit or push were performed.",
        "Live metadata and verification hashes are stored in the JSON. Computed DepositValue retains its existing function dependency.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--cases", nargs="+")
    args = parser.parse_args()
    frozen = check_definitions()
    if args.check_only:
        print("PASS: 13 definitions, 4/5/4 difficulties, exact expected tables, named parameters, SELECT-only uncapped reference SQL.")
        return
    if args.cases and not set(args.cases) <= set(REFERENCES):
        raise ValueError("Unknown case selection")
    before = protected_hashes()
    ref_hash = hashlib.sha256(json.dumps(REFERENCES, sort_keys=True).encode()).hexdigest()
    if EVIDENCE.exists():
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        if payload["protected_hashes"] != before:
            raise ValueError("Protected files changed since prior validation")
        if payload["reference_definitions_sha256"] != ref_hash:
            payload["cases"] = {
                k:v for k,v in payload["cases"].items()
                if v["reference_sql_sha256"] == hashlib.sha256(REFERENCES[k]["reference_sql"].encode()).hexdigest()
            }
    else:
        payload = {"cases": {}, "protected_hashes": before}
    payload["reference_definitions_sha256"] = ref_hash
    connection = connect_read_only()
    connection.timeout = 60
    try:
        cur = connection.cursor()
        cur.execute("SELECT DB_NAME(), CONVERT(date,GETDATE())")
        target, server_date = cur.fetchone()
        cur.close()
        if target != "GD4_60_SPN":
            raise ValueError("Unexpected database target")
        payload["target_database"] = target
        payload["server_date_at_validation"] = str(server_date)
        if "live_schema" not in payload:
            payload["live_schema"] = schema_evidence(connection, frozen)
        for case in frozen:
            key = case["id"]
            if args.cases and key not in args.cases:
                continue
            if not args.cases and payload["cases"].get(key, {}).get("execution_valid"):
                print(key, "reused", flush=True)
                continue
            result = validate_case(connection, case)
            payload["cases"][key] = result
            EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(key, json.dumps({k:result.get(k) for k in ("execution_valid","empty","rows_fetched","row_count","error")}), flush=True)
    finally:
        connection.close()
    if before != protected_hashes():
        raise ValueError("Protected files changed during validation")
    payload["protected_files_unchanged"] = True
    payload["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_outputs(frozen, payload)
    print(json.dumps(payload["summary"]), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Validation stopped:", json.dumps(safe_error(error)), flush=True)
        raise SystemExit(1)

