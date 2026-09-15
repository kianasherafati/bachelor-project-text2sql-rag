"""Frozen, human-reviewed held-out ERP schema-retrieval benchmark."""


tests = [
    {
        "id": "ERP-H01",
        "domain": "sales",
        "difficulty": "easy",
        "question": (
            "List customer codes with their maximum cash and non-cash credit "
            "limits, agreed ledger-receipt days, and agreed cheque duration."
        ),
        "expected_tables": ["gnd_crsls.tblCustomer"],
        "reason": (
            "tblCustomer contains CustomerCode, MaxCashCredit, MaxNonCashCredit, "
            "AgreedLedgerReceiveDays, and AgreedChequesDuration."
        ),
        "fk_paths": [],
    },
    {
        "id": "ERP-H02",
        "domain": "purchasing",
        "difficulty": "easy",
        "question": (
            "Show the names of purchasable services, their last recorded prices, "
            "and their configured payment delays in months."
        ),
        "expected_tables": ["gnd_scpch.tblPurchasableService"],
        "reason": "tblPurchasableService supplies Name, LastPrice, and PaymentDelayInMonth.",
        "fk_paths": [],
    },
    {
        "id": "ERP-H03",
        "domain": "inventory",
        "difficulty": "easy",
        "question": (
            "List storage-location labels with their inventory identifiers and "
            "recorded volumes."
        ),
        "expected_tables": ["gnd_scinv.tblLocation"],
        "reason": "tblLocation supplies Label, InventoryID, and Volume.",
        "fk_paths": [],
    },
    {
        "id": "ERP-H04",
        "domain": "payroll",
        "difficulty": "easy",
        "question": (
            "List salary-tax lists with their payment dates and payable values, "
            "showing the company, tax-branch, and year-month identifiers."
        ),
        "expected_tables": ["gnd_hrpyr.tblSalaryTaxList"],
        "reason": (
            "tblSalaryTaxList contains PaymentDate, PayableValue, CompanyID, "
            "TaxBranchID, and YearMonthID."
        ),
        "fk_paths": [],
    },
    {
        "id": "ERP-H05",
        "domain": "projects",
        "difficulty": "easy",
        "question": (
            "Show daily project-report entries with the project identifier, report "
            "date, task title, description, reporter identifier, and recorded time spent."
        ),
        "expected_tables": ["gnd_pjprj.tblDailyReport"],
        "reason": (
            "tblDailyReport contains ProjectID, Date, TaskTitle, Description, "
            "ReporterID, and SpentTimeDur."
        ),
        "fk_paths": [],
    },
    {
        "id": "ERP-H06",
        "domain": "sales",
        "difficulty": "medium",
        "question": (
            "Prepare a customer contact-address report showing customer code, "
            "street address, post-office box, and telephone number for each recorded address."
        ),
        "expected_tables": [
            "gnd_crsls.tblCustomerAddress",
            "gnd_crsls.tblCustomer",
        ],
        "reason": (
            "tblCustomerAddress supplies Address, POBox, and Phone; tblCustomer "
            "supplies CustomerCode."
        ),
        "fk_paths": [
            "gnd_crsls.tblCustomerAddress.CustomerID -> gnd_crsls.tblCustomer.ID",
        ],
    },
    {
        "id": "ERP-H07",
        "domain": "purchasing",
        "difficulty": "medium",
        "question": (
            "For each supplier evaluation record, show the supplier identifier, "
            "evaluation date, recorded score, assessment criterion description, "
            "and whether the criterion is mandatory."
        ),
        "expected_tables": [
            "gnd_scpch.tblSupplierEvaluation",
            "gnd_scpch.tblSupplierEvaluationParameter",
        ],
        "reason": (
            "tblSupplierEvaluation supplies SupplierID, DoneDate, and Score; "
            "tblSupplierEvaluationParameter supplies Descriptions and IsMandatory."
        ),
        "fk_paths": [
            "gnd_scpch.tblSupplierEvaluation.SupplierEvaluationParameterID -> "
            "gnd_scpch.tblSupplierEvaluationParameter.ID",
        ],
    },
    {
        "id": "ERP-H08",
        "domain": "inventory",
        "difficulty": "medium",
        "question": (
            "Show physical stock-count sheets with their count code and date, and "
            "each line's sequence, scanned barcode, counted quantity, package count, "
            "and last-update time."
        ),
        "expected_tables": ["gnd_scinv.tblCounter", "gnd_scinv.tblCounterDetail"],
        "reason": (
            "tblCounter supplies Code and DoneDate; tblCounterDetail supplies Sequence, "
            "BarCode, Qty, PackCount, and LastUpdateTime."
        ),
        "fk_paths": [
            "gnd_scinv.tblCounterDetail.CounterID -> gnd_scinv.tblCounter.ID",
        ],
    },
    {
        "id": "ERP-H09",
        "domain": "hr/personnel",
        "difficulty": "medium",
        "question": (
            "For each employee identifier, list the required personnel-document types "
            "using their stored English labels, document sequence, attachment flag, "
            "and picture filename."
        ),
        "expected_tables": [
            "gnd_hrprs.tblEmployeeRequiredDocument",
            "gnd_hrprs.tblDocumentType",
        ],
        "reason": (
            "tblEmployeeRequiredDocument supplies EmployeeID, Sequence, HasAttachment, "
            "and PictureName; tblDocumentType supplies the stored English label."
        ),
        "fk_paths": [
            "gnd_hrprs.tblEmployeeRequiredDocument.DocumentTypeID -> "
            "gnd_hrprs.tblDocumentType.ID",
        ],
    },
    {
        "id": "ERP-H10",
        "domain": "payroll",
        "difficulty": "medium",
        "question": (
            "List configured payroll tax brackets with their effective start and end "
            "dates, tax-branch identifier, bracket row number, minimum and maximum "
            "salary values, tax value, and tax percentage."
        ),
        "expected_tables": ["gnd_hrpyr.tblTaxTable", "gnd_hrpyr.tblTaxTableDetail"],
        "reason": (
            "tblTaxTable supplies FromDate, ToDate, and TaxBranchID; tblTaxTableDetail "
            "supplies Row, MinSalaryValue, MaxSalaryValue, TaxValue, and TaxPercent."
        ),
        "fk_paths": [
            "gnd_hrpyr.tblTaxTableDetail.TaxTableID -> gnd_hrpyr.tblTaxTable.ID",
        ],
    },
    {
        "id": "ERP-H11",
        "domain": "production",
        "difficulty": "medium",
        "question": (
            "List manufacturing-report stoppage entries with the manufacturing-record "
            "identifier, stop code, start and end times, and stop-type description."
        ),
        "expected_tables": [
            "gnd_scprd.tblProductionReportManufacturingStopDetail",
            "gnd_amast.tblStopType",
        ],
        "reason": (
            "tblProductionReportManufacturingStopDetail supplies the manufacturing "
            "record identifier, StopCode, StartTime, and EndTime; tblStopType supplies Description."
        ),
        "fk_paths": [
            "gnd_scprd.tblProductionReportManufacturingStopDetail.StopTypeID -> "
            "gnd_amast.tblStopType.ID",
        ],
    },
    {
        "id": "ERP-H12",
        "domain": "quality control",
        "difficulty": "medium",
        "question": (
            "Show carton-inspection results with inspection date and packing date, and "
            "each bobbin's number, measured weight, humidity, cone hardness, and checker."
        ),
        "expected_tables": [
            "gnd_scqam.tblCartonInspectionTest",
            "gnd_scqam.tblCartonInspectionTestDetail",
        ],
        "reason": (
            "tblCartonInspectionTest supplies Date and PackingDate; its detail supplies "
            "BobbinNo, Weight, Humidity, ConeHardness, and Checker."
        ),
        "fk_paths": [
            "gnd_scqam.tblCartonInspectionTestDetail.CartonInspectionTestID -> "
            "gnd_scqam.tblCartonInspectionTest.ID",
        ],
    },
    {
        "id": "ERP-H13",
        "domain": "sales",
        "difficulty": "hard",
        "question": (
            "Trace serial numbers recorded against shipment-loading lines, showing the "
            "loading code and date, line sequence, quantity, package count, and serial number."
        ),
        "expected_tables": [
            "gnd_crsls.tblLoading",
            "gnd_crsls.tblLoadingDetail",
            "gnd_crsls.tblLoadingSerialDetail",
        ],
        "reason": (
            "tblLoading supplies Code and DoneDate; tblLoadingDetail supplies Sequence, "
            "Qty, and PackCount; tblLoadingSerialDetail supplies Serial."
        ),
        "fk_paths": [
            "gnd_crsls.tblLoadingSerialDetail.LoadingDetailIG -> gnd_crsls.tblLoadingDetail.IG",
            "gnd_crsls.tblLoadingDetail.LoadingID -> gnd_crsls.tblLoading.ID",
        ],
    },
    {
        "id": "ERP-H14",
        "domain": "purchasing",
        "difficulty": "hard",
        "question": (
            "Show service-purchase requests with their request code and date, line "
            "sequence, service name, requested quantity, proposed fee, buying fee, "
            "and recorded line total."
        ),
        "expected_tables": [
            "gnd_scpch.tblRequestBuyService",
            "gnd_scpch.tblRequestBuyServiceDetail",
            "gnd_scpch.tblPurchasableService",
        ],
        "reason": (
            "tblRequestBuyService supplies Code and DoneDate; its detail supplies "
            "Sequence, Qty, ProposalFee, BuyFee, and TotalValue; tblPurchasableService supplies Name."
        ),
        "fk_paths": [
            "gnd_scpch.tblRequestBuyServiceDetail.RequestBuyServiceID -> "
            "gnd_scpch.tblRequestBuyService.ID",
            "gnd_scpch.tblRequestBuyServiceDetail.PurchasableServiceID -> "
            "gnd_scpch.tblPurchasableService.ID",
        ],
    },
    {
        "id": "ERP-H15",
        "domain": "hr/personnel",
        "difficulty": "hard",
        "question": (
            "Prepare a job-classification register showing each job title, its legal-position "
            "name and configured trial period, and its job-group description."
        ),
        "expected_tables": [
            "gnd_hrprs.tblJobTitle",
            "gnd_hrprs.tblLegalPosition",
            "gnd_hrprs.tblJobGroup",
        ],
        "reason": (
            "tblJobTitle supplies the title and links; tblLegalPosition supplies Name and "
            "TrialPeriod; tblJobGroup supplies Description."
        ),
        "fk_paths": [
            "gnd_hrprs.tblJobTitle.LegalPositionID -> gnd_hrprs.tblLegalPosition.ID",
            "gnd_hrprs.tblJobTitle.JobGroupID -> gnd_hrprs.tblJobGroup.ID",
        ],
    },
    {
        "id": "ERP-H16",
        "domain": "production",
        "difficulty": "hard",
        "question": (
            "Break down recorded yarn defects by equipment identifier and spindle head "
            "number, showing the stored English defect-type label, primary-defect flag, "
            "affected spindle count, and total spindle weight recorded for each defect entry."
        ),
        "expected_tables": [
            "gnd_scprd.tblYarnDefect",
            "gnd_scprd.tblYarnDefectSpindleDetail",
            "gnd_scprd.tblYarnDefectSpindleDefectionDetail",
            "gnd_scprd.tblDefectionType",
        ],
        "reason": (
            "tblYarnDefect supplies EquipmentID; the spindle detail supplies HeadNumber; "
            "the defection detail supplies the flag, count, and weight; tblDefectionType "
            "supplies its stored English label."
        ),
        "fk_paths": [
            "gnd_scprd.tblYarnDefectSpindleDefectionDetail.YarnDefectSpindleIG -> "
            "gnd_scprd.tblYarnDefectSpindleDetail.IG",
            "gnd_scprd.tblYarnDefectSpindleDetail.YarnDefectID -> gnd_scprd.tblYarnDefect.ID",
            "gnd_scprd.tblYarnDefectSpindleDefectionDetail.DefectionTypeID -> "
            "gnd_scprd.tblDefectionType.ID",
        ],
    },
    {
        "id": "ERP-H17",
        "domain": "quality control",
        "difficulty": "hard",
        "question": (
            "Show audit-inspection question scores with audit date, shift name, finalization "
            "flag, question title, question maximum score, awarded score, and the recorded "
            "detail description."
        ),
        "expected_tables": [
            "gnd_scqam.tblAuditInspection",
            "gnd_scqam.tblAuditInspectionDetail",
            "gnd_scqam.tblAuditQuestion",
        ],
        "reason": (
            "tblAuditInspection supplies AuditDate, ShiftName, and IsFinal; its detail "
            "supplies awarded Score and Description; tblAuditQuestion supplies QuestionTitle and MaxScore."
        ),
        "fk_paths": [
            "gnd_scqam.tblAuditInspectionDetail.AuditInspectionID -> gnd_scqam.tblAuditInspection.ID",
            "gnd_scqam.tblAuditInspectionDetail.AuditQuestionID -> gnd_scqam.tblAuditQuestion.ID",
        ],
    },
    {
        "id": "ERP-H18",
        "domain": "assets/equipment",
        "difficulty": "hard",
        "question": (
            "Prepare an equipment-failure register showing equipment serial number and "
            "model, failure date, failure-type description, and the recorded failure "
            "description and comment."
        ),
        "expected_tables": [
            "gnd_amast.tblEquipmentFailure",
            "gnd_amast.tblEquipment",
            "gnd_amast.tblFailureType",
        ],
        "reason": (
            "tblEquipmentFailure supplies FailureDate, Description, and Comment; "
            "tblEquipment supplies SerialNumber and Model; tblFailureType supplies Description."
        ),
        "fk_paths": [
            "gnd_amast.tblEquipmentFailure.EquipmentID -> gnd_amast.tblEquipment.ID",
            "gnd_amast.tblEquipmentFailure.FailureTypeID -> gnd_amast.tblFailureType.ID",
        ],
    },
    {
        "id": "ERP-H19",
        "domain": "finance/accounting",
        "difficulty": "hard",
        "question": (
            "Show accounting transaction lines with transaction code and document date, "
            "row number, account code and title, line description, debit amount, and credit amount."
        ),
        "expected_tables": [
            "gnd_fiaci.tblTrans",
            "gnd_fiaci.tblTransDetail",
            "gnd_fiaci.tblAccount",
        ],
        "reason": (
            "tblTrans supplies TransCode and DocDate; tblTransDetail supplies RowNumber, "
            "Description, Debit, and Credit; tblAccount supplies AccountCode and Title."
        ),
        "fk_paths": [
            "gnd_fiaci.tblTransDetail.TransID -> gnd_fiaci.tblTrans.ID",
            "gnd_fiaci.tblTransDetail.AccountID -> gnd_fiaci.tblAccount.ID",
        ],
    },
    {
        "id": "ERP-H20",
        "domain": "projects",
        "difficulty": "hard",
        "question": (
            "Show project steps with the project's stored English name, step sequence and "
            "stored English step label, start and end dates, recorded duration, model-step "
            "default duration, and completion and not-needed flags."
        ),
        "expected_tables": [
            "gnd_pjprj.tblProjectStep",
            "gnd_pjprj.tblProject",
            "gnd_pjprj.tblModelStep",
            "gnd_pjprj.tblStep",
        ],
        "reason": (
            "tblProjectStep supplies dates, duration, sequence, and flags; tblProject supplies "
            "the stored English name; tblModelStep supplies DefaultDuration; tblStep supplies "
            "the stored English step label."
        ),
        "fk_paths": [
            "gnd_pjprj.tblProjectStep.ProjectID -> gnd_pjprj.tblProject.ID",
            "gnd_pjprj.tblProjectStep.ModelStepID -> gnd_pjprj.tblModelStep.ID",
            "gnd_pjprj.tblModelStep.StepID -> gnd_pjprj.tblStep.ID",
        ],
    },
]
