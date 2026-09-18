"""Reference SELECTs for the approved held-out questions; no database access."""

# Each query preserves the driving record's grain. Nullable FK lookups use
# LEFT JOIN; mandatory parent links use INNER JOIN. Do not deduplicate results.
# Values, durations, flags, and stored labels are returned without interpretation.
definitions = {
    "ERP-H01": {
        "driving_table": "gnd_crsls.tblCustomer",
        "reference_sql": """SELECT
    c.[CustomerCode],
    c.[MaxCashCredit],
    c.[MaxNonCashCredit],
    c.[AgreedLedgerReceiveDays],
    c.[AgreedChequesDuration]
FROM [gnd_crsls].[tblCustomer] AS c;""",
    },
    "ERP-H02": {
        "driving_table": "gnd_scpch.tblPurchasableService",
        "reference_sql": """SELECT
    s.[Name] AS [ServiceName],
    s.[LastPrice],
    s.[PaymentDelayInMonth]
FROM [gnd_scpch].[tblPurchasableService] AS s;""",
    },
    "ERP-H03": {
        "driving_table": "gnd_scinv.tblLocation",
        "reference_sql": """SELECT
    l.[Label] AS [LocationLabel],
    l.[InventoryID],
    l.[Volume]
FROM [gnd_scinv].[tblLocation] AS l;""",
    },
    "ERP-H04": {
        "driving_table": "gnd_hrpyr.tblSalaryTaxList",
        "reference_sql": """SELECT
    t.[PaymentDate],
    t.[PayableValue],
    t.[CompanyID],
    t.[TaxBranchID],
    t.[YearMonthID]
FROM [gnd_hrpyr].[tblSalaryTaxList] AS t;""",
    },
    "ERP-H05": {
        "driving_table": "gnd_pjprj.tblDailyReport",
        "reference_sql": """SELECT
    r.[ProjectID],
    r.[Date] AS [ReportDate],
    r.[TaskTitle],
    r.[Description],
    r.[ReporterID],
    r.[SpentTimeDur] AS [RecordedTimeSpent]
FROM [gnd_pjprj].[tblDailyReport] AS r;""",
        "semantic_notes": ["SpentTimeDur is returned as stored; no undocumented time unit is assumed."],
    },
    "ERP-H06": {
        "driving_table": "gnd_crsls.tblCustomerAddress",
        "reference_sql": """SELECT
    c.[CustomerCode],
    a.[Address],
    a.[POBox],
    a.[Phone]
FROM [gnd_crsls].[tblCustomerAddress] AS a
INNER JOIN [gnd_crsls].[tblCustomer] AS c
    ON a.[CustomerID] = c.[ID];""",
    },
    "ERP-H07": {
        "driving_table": "gnd_scpch.tblSupplierEvaluation",
        "reference_sql": """SELECT
    e.[SupplierID],
    e.[DoneDate] AS [EvaluationDate],
    e.[Score] AS [RecordedScore],
    p.[Descriptions] AS [AssessmentCriterionDescription],
    p.[IsMandatory]
FROM [gnd_scpch].[tblSupplierEvaluation] AS e
LEFT JOIN [gnd_scpch].[tblSupplierEvaluationParameter] AS p
    ON e.[SupplierEvaluationParameterID] = p.[ID];""",
        "semantic_notes": ["Preserve evaluations with no criterion; the recorded score comes from the evaluation, not the criterion definition."],
    },
    "ERP-H08": {
        "driving_table": "gnd_scinv.tblCounterDetail",
        "reference_sql": """SELECT
    c.[Code] AS [CountCode],
    c.[DoneDate] AS [CountDate],
    d.[Sequence] AS [LineSequence],
    d.[BarCode] AS [ScannedBarcode],
    d.[Qty] AS [CountedQuantity],
    d.[PackCount] AS [PackageCount],
    d.[LastUpdateTime]
FROM [gnd_scinv].[tblCounterDetail] AS d
INNER JOIN [gnd_scinv].[tblCounter] AS c
    ON d.[CounterID] = c.[ID];""",
        "semantic_notes": ["One row per count line; headers without lines do not create synthetic line results."],
    },
    "ERP-H09": {
        "driving_table": "gnd_hrprs.tblEmployeeRequiredDocument",
        "reference_sql": """SELECT
    d.[EmployeeID],
    t.[English] AS [DocumentTypeEnglish],
    d.[Sequence] AS [DocumentSequence],
    d.[HasAttachment],
    d.[PictureName]
FROM [gnd_hrprs].[tblEmployeeRequiredDocument] AS d
INNER JOIN [gnd_hrprs].[tblDocumentType] AS t
    ON d.[DocumentTypeID] = t.[ID];""",
    },
    "ERP-H10": {
        "driving_table": "gnd_hrpyr.tblTaxTableDetail",
        "reference_sql": """SELECT
    t.[FromDate] AS [EffectiveStartDate],
    t.[ToDate] AS [EffectiveEndDate],
    t.[TaxBranchID],
    d.[Row] AS [BracketRowNumber],
    d.[MinSalaryValue],
    d.[MaxSalaryValue],
    d.[TaxValue],
    d.[TaxPercent]
FROM [gnd_hrpyr].[tblTaxTableDetail] AS d
LEFT JOIN [gnd_hrpyr].[tblTaxTable] AS t
    ON d.[TaxTableID] = t.[ID];""",
        "semantic_notes": ["TaxTableID is nullable; preserve every bracket. Report configured amounts and percentages without calculating tax."],
    },
    "ERP-H11": {
        "driving_table": "gnd_scprd.tblProductionReportManufacturingStopDetail",
        "reference_sql": """SELECT
    d.[ProductionReportManufacturingID],
    d.[StopCode],
    d.[StartTime],
    d.[EndTime],
    t.[Description] AS [StopTypeDescription]
FROM [gnd_scprd].[tblProductionReportManufacturingStopDetail] AS d
LEFT JOIN [gnd_amast].[tblStopType] AS t
    ON d.[StopTypeID] = t.[ID];""",
        "semantic_notes": ["StopTypeID is nullable; preserve unclassified stoppages."],
    },
    "ERP-H12": {
        "driving_table": "gnd_scqam.tblCartonInspectionTestDetail",
        "reference_sql": """SELECT
    t.[Date] AS [InspectionDate],
    t.[PackingDate],
    d.[BobbinNo],
    d.[Weight] AS [MeasuredWeight],
    d.[Humidity],
    d.[ConeHardness],
    d.[Checker]
FROM [gnd_scqam].[tblCartonInspectionTestDetail] AS d
INNER JOIN [gnd_scqam].[tblCartonInspectionTest] AS t
    ON d.[CartonInspectionTestID] = t.[ID];""",
        "semantic_notes": ["ConeHardness is a nullable bit flag, returned as stored, not a numeric hardness measurement."],
    },
    "ERP-H13": {
        "driving_table": "gnd_crsls.tblLoadingSerialDetail",
        "reference_sql": """SELECT
    h.[Code] AS [LoadingCode],
    h.[DoneDate] AS [LoadingDate],
    d.[Sequence] AS [LineSequence],
    d.[Qty] AS [Quantity],
    d.[PackCount] AS [PackageCount],
    s.[Serial]
FROM [gnd_crsls].[tblLoadingSerialDetail] AS s
INNER JOIN [gnd_crsls].[tblLoadingDetail] AS d
    ON s.[LoadingDetailIG] = d.[IG]
INNER JOIN [gnd_crsls].[tblLoading] AS h
    ON d.[LoadingID] = h.[ID];""",
        "semantic_notes": ["One row per recorded serial; line quantity and package count repeat for each serial and must not be summed at this grain."],
    },
    "ERP-H14": {
        "driving_table": "gnd_scpch.tblRequestBuyServiceDetail",
        "reference_sql": """SELECT
    h.[Code] AS [RequestCode],
    h.[DoneDate] AS [RequestDate],
    d.[Sequence] AS [LineSequence],
    s.[Name] AS [ServiceName],
    d.[Qty] AS [RequestedQuantity],
    d.[ProposalFee] AS [ProposedFee],
    d.[BuyFee] AS [BuyingFee],
    d.[TotalValue] AS [RecordedLineTotal]
FROM [gnd_scpch].[tblRequestBuyServiceDetail] AS d
INNER JOIN [gnd_scpch].[tblRequestBuyService] AS h
    ON d.[RequestBuyServiceID] = h.[ID]
INNER JOIN [gnd_scpch].[tblPurchasableService] AS s
    ON d.[PurchasableServiceID] = s.[ID];""",
    },
    "ERP-H15": {
        "driving_table": "gnd_hrprs.tblJobTitle",
        "reference_sql": """SELECT
    j.[JobTitle],
    p.[Name] AS [LegalPositionName],
    p.[TrialPeriod],
    g.[Description] AS [JobGroupDescription]
FROM [gnd_hrprs].[tblJobTitle] AS j
INNER JOIN [gnd_hrprs].[tblLegalPosition] AS p
    ON j.[LegalPositionID] = p.[ID]
INNER JOIN [gnd_hrprs].[tblJobGroup] AS g
    ON j.[JobGroupID] = g.[ID];""",
        "semantic_notes": ["TrialPeriod is returned as configured; no undocumented duration unit is assumed."],
    },
    "ERP-H16": {
        "driving_table": "gnd_scprd.tblYarnDefectSpindleDefectionDetail",
        "reference_sql": """SELECT
    y.[EquipmentID],
    s.[HeadNumber],
    t.[English] AS [DefectTypeEnglish],
    d.[IsPrimaryDefection] AS [IsPrimaryDefect],
    d.[SpindleCount] AS [AffectedSpindleCount],
    d.[SpindleTotalWeight] AS [RecordedTotalSpindleWeight]
FROM [gnd_scprd].[tblYarnDefectSpindleDefectionDetail] AS d
INNER JOIN [gnd_scprd].[tblYarnDefectSpindleDetail] AS s
    ON d.[YarnDefectSpindleIG] = s.[IG]
INNER JOIN [gnd_scprd].[tblYarnDefect] AS y
    ON s.[YarnDefectID] = y.[ID]
INNER JOIN [gnd_scprd].[tblDefectionType] AS t
    ON d.[DefectionTypeID] = t.[ID];""",
        "semantic_notes": ["One row per defect entry; use that entry's count and weight, without aggregating parent spindle totals."],
    },
    "ERP-H17": {
        "driving_table": "gnd_scqam.tblAuditInspectionDetail",
        "reference_sql": """SELECT
    i.[AuditDate],
    i.[ShiftName],
    i.[IsFinal],
    q.[QuestionTitle],
    q.[MaxScore] AS [QuestionMaximumScore],
    d.[Score] AS [AwardedScore],
    d.[Description] AS [DetailDescription]
FROM [gnd_scqam].[tblAuditInspectionDetail] AS d
INNER JOIN [gnd_scqam].[tblAuditInspection] AS i
    ON d.[AuditInspectionID] = i.[ID]
INNER JOIN [gnd_scqam].[tblAuditQuestion] AS q
    ON d.[AuditQuestionID] = q.[ID];""",
        "semantic_notes": ["Use the current question-definition maximum, not the inspection total maximum. No IsDeleted/IsFinal filter is requested or applied."],
    },
    "ERP-H18": {
        "driving_table": "gnd_amast.tblEquipmentFailure",
        "reference_sql": """SELECT
    e.[SerialNumber] AS [EquipmentSerialNumber],
    e.[Model] AS [EquipmentModel],
    f.[FailureDate],
    t.[Description] AS [FailureTypeDescription],
    f.[Description] AS [FailureDescription],
    f.[Comment] AS [FailureComment]
FROM [gnd_amast].[tblEquipmentFailure] AS f
INNER JOIN [gnd_amast].[tblEquipment] AS e
    ON f.[EquipmentID] = e.[ID]
INNER JOIN [gnd_amast].[tblFailureType] AS t
    ON f.[FailureTypeID] = t.[ID];""",
    },
    "ERP-H19": {
        "driving_table": "gnd_fiaci.tblTransDetail",
        "reference_sql": """SELECT
    t.[TransCode] AS [TransactionCode],
    t.[DocDate] AS [DocumentDate],
    d.[RowNumber],
    a.[AccountCode],
    a.[Title] AS [AccountTitle],
    d.[Description] AS [LineDescription],
    d.[Debit] AS [DebitAmount],
    d.[Credit] AS [CreditAmount]
FROM [gnd_fiaci].[tblTransDetail] AS d
INNER JOIN [gnd_fiaci].[tblTrans] AS t
    ON d.[TransID] = t.[ID]
INNER JOIN [gnd_fiaci].[tblAccount] AS a
    ON d.[AccountID] = a.[ID];""",
    },
    "ERP-H20": {
        "driving_table": "gnd_pjprj.tblProjectStep",
        "reference_sql": """SELECT
    p.[English] AS [ProjectEnglishName],
    ps.[Sequence] AS [StepSequence],
    s.[English] AS [StepEnglishLabel],
    ps.[StartDate],
    ps.[EndDate],
    ps.[Duration] AS [RecordedDuration],
    ms.[DefaultDuration] AS [ModelStepDefaultDuration],
    ps.[IsDone],
    ps.[NotNeeded]
FROM [gnd_pjprj].[tblProjectStep] AS ps
INNER JOIN [gnd_pjprj].[tblProject] AS p
    ON ps.[ProjectID] = p.[ID]
LEFT JOIN [gnd_pjprj].[tblModelStep] AS ms
    ON ps.[ModelStepID] = ms.[ID]
LEFT JOIN [gnd_pjprj].[tblStep] AS s
    ON ms.[StepID] = s.[ID];""",
        "semantic_notes": ["Preserve project steps with no ModelStepID; missing labels and defaults remain NULL. Durations are returned as stored."],
    },
}
