"""Frozen real-world ERP Text-to-SQL benchmark.

The questions originated from customer information needs and were frozen only
after an independent, read-only feasibility review of GD4_60_SPN. This module
contains benchmark definitions only: it does not contain gold SQL, support
ticket text or provenance, or executable evaluation logic.
"""


TOP_K = 10


tests = [
    {
        "id": "REAL-C01",
        "question": (
            "Show account activity for a specified financial period, account, "
            "and project, including only entries for that project."
        ),
        "domain": "accounting",
        "difficulty": "medium",
        "expected_tables": [
            "gnd_fiaci.tblTrans",
            "gnd_fiaci.tblTransDetail",
            "gnd_fiaci.tblTransDetailDetail",
        ],
        "expected_table_count": 3,
        "relationship_notes": [
            "FK: gnd_fiaci.tblTransDetail.TransID -> gnd_fiaci.tblTrans.ID.",
            (
                "FK: gnd_fiaci.tblTransDetailDetail.TransDetailIG -> "
                "gnd_fiaci.tblTransDetail.IG."
            ),
            (
                "Project is a polymorphic accounting dimension: "
                "tblTransDetailDetail.FormTypeID = 12261 identifies Project, "
                "and FormID identifies the project; there is no direct FK from "
                "FormID to the project table."
            ),
        ],
        "feasibility_status": "FEASIBLE",
        "semantic_evaluation_note": (
            "Match project by the typed dimension pair and avoid duplicating an "
            "accounting line when testing for the project dimension. Account, "
            "period, and project labels are not requested."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C02",
        "question": (
            "For a selected service-purchase invoice, compare its tax amount "
            "with the tax amount in its associated accounting entry."
        ),
        "domain": "purchasing",
        "difficulty": "hard",
        "expected_tables": [
            "gnd_scpch.tblServiceInvoice",
            "gnd_fiaci.tblTrans",
            "gnd_fiaci.tblTransDetail",
        ],
        "expected_table_count": 3,
        "relationship_notes": [
            "FK: gnd_fiaci.tblTransDetail.TransID -> gnd_fiaci.tblTrans.ID.",
            (
                "Logical source-document join: tblTrans.FormID = "
                "tblServiceInvoice.ID with tblTrans.FormTypeID = 1208179; "
                "there is no direct invoice-to-transaction FK."
            ),
        ],
        "feasibility_status": "FEASIBLE",
        "semantic_evaluation_note": (
            "The SPN posting template maps ServiceInvoice.TotalVat to VAT-and-"
            "duties account ID 348. Compare against that posted tax line, not "
            "against the journal's total debit or credit."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C03",
        "question": (
            "Show purchase-request lines with their recorded request reason and "
            "intended use."
        ),
        "domain": "purchasing",
        "difficulty": "easy",
        "expected_tables": ["gnd_scpch.tblPurchaseRequestDetail"],
        "expected_table_count": 1,
        "relationship_notes": [],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "RequestReason and ConsumptionPurpose are stored on each purchase-"
            "request line. Do not claim universal line-level provenance from an "
            "originating warehouse requisition."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C04",
        "question": (
            "Show imports by pro forma invoice, commercial invoice, domestic "
            "waybill, and goods receipt, with each stage's item-line quantity "
            "in the item's recorded unit, the order-registration number, and "
            "the customs-declaration number where applicable. Keep quantities "
            "separate between stages."
        ),
        "domain": "imports",
        "difficulty": "hard",
        "expected_tables": [
            "gnd_scimp.tblProformaInvoice",
            "gnd_scimp.tblProformaInvoiceDetail",
            "gnd_scimp.tblCurrencyPurchaseInvoice",
            "gnd_scimp.tblCurrencyPurchaseInvoiceDetail",
            "gnd_scimp.tblOrderRegistration",
            "gnd_scimp.tblCottage",
            "gnd_sclog.tblInternalBillOfLading",
            "gnd_sclog.tblInternalBillOfLadingGoodDetail",
            "gnd_scimp.tblForeignReceiveGoods",
            "gnd_scimp.tblForeignReceiveGoodsDetail",
            "gnd_spgod.tblGood",
            "gnd_spgod.tblGoodUnitTypeL",
        ],
        "expected_table_count": 12,
        "relationship_notes": [
            (
                "FK: tblProformaInvoiceDetail.ProformaInvoiceID -> "
                "tblProformaInvoice.ID."
            ),
            (
                "FK: tblCurrencyPurchaseInvoice.ProformaInvoiceID -> "
                "tblProformaInvoice.ID."
            ),
            (
                "FK: tblCurrencyPurchaseInvoiceDetail.CurrencyPurchaseInvoiceID "
                "-> tblCurrencyPurchaseInvoice.ID."
            ),
            "FK: tblOrderRegistration.ID -> tblProformaInvoice.ID.",
            "FK: tblInternalBillOfLading.CottageID -> tblCottage.ID.",
            (
                "FK: tblInternalBillOfLadingGoodDetail.BillOfLadingID -> "
                "tblInternalBillOfLading.ID."
            ),
            "FK: tblForeignReceiveGoods.ID -> tblInternalBillOfLading.ID.",
            (
                "FK: tblForeignReceiveGoodsDetail.ForeignReceiveGoodsID -> "
                "tblForeignReceiveGoods.ID."
            ),
            (
                "Each stage-detail GoodID references gnd_spgod.tblGood.ID; "
                "tblGood.UnitTypeID -> gnd_spgod.tblGoodUnitTypeL.ID."
            ),
            (
                "Invoice-to-customs linkage is the verified shared-ID FK chain "
                "Cottage -> WareHouseBill -> BillOfLading -> PackingList -> "
                "CurrencyPurchaseInvoice. The intermediate inheritance tables "
                "are relationship evidence but are not required output tables."
            ),
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "Return separate stage/item-line records. Do not aggregate quantities "
            "across stages or flatten sibling detail sets into a cross-product. "
            "The consolidated ForeignPurchase structure is empty in this SPN snapshot."
        ),
        "top10_full_coverage_possible": False,
        "top10_recall_ceiling": 10 / 12,
    },
    {
        "id": "REAL-C05",
        "question": "List warehouse issue lines and include the item code for each line.",
        "domain": "inventory",
        "difficulty": "medium",
        "expected_tables": [
            "gnd_scinv.tblExitDetail",
            "gnd_spgod.tblGood",
        ],
        "expected_table_count": 2,
        "relationship_notes": [
            "FK: gnd_scinv.tblExitDetail.CredbGoodID -> gnd_spgod.tblGood.ID."
        ],
        "feasibility_status": "FEASIBLE",
        "semantic_evaluation_note": (
            "Use ExitDetail.IG as the reliable line identifier; Sequence may be NULL."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C06",
        "question": (
            "Show the dated shift-assignment history of a selected former "
            "employee, including earlier assignments."
        ),
        "domain": "hr_attendance",
        "difficulty": "medium",
        "expected_tables": [
            "gnd_hrprs.tblEmployee",
            "gnd_hrcio.tblEmployeeShift",
        ],
        "expected_table_count": 2,
        "relationship_notes": [
            "FK: gnd_hrcio.tblEmployeeShift.EmployeeID -> gnd_hrprs.tblEmployee.ID."
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "Former-employee status is Employee.IsLeaved. Assignment dates are "
            "EmployeeShift.FromDate and EndDateStatus. Do not reinterpret the "
            "question as shift-change requests or approvals."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C07",
        "question": (
            "Show all recorded monetary components of a selected employee "
            "settlement statement, including components with zero amounts."
        ),
        "domain": "payroll",
        "difficulty": "medium",
        "expected_tables": [
            "gnd_hrpyr.tblBonusBill",
            "gnd_hrpyr.tblBonusBillParameter",
            "gnd_hrpyr.tblMonthlyParameterType",
        ],
        "expected_table_count": 3,
        "relationship_notes": [
            (
                "FK: gnd_hrpyr.tblBonusBillParameter.BonusBillID -> "
                "gnd_hrpyr.tblBonusBill.ID."
            ),
            (
                "FK: tblBonusBillParameter.MonthlyParameterTypeID -> "
                "gnd_hrpyr.tblMonthlyParameterType.ID."
            ),
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "Fixed components are columns on BonusBill; additional labeled "
            "components are parameter rows. Preserve the distinction between "
            "recorded zero and NULL, and do not assume every printed template "
            "line is physically stored."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C08",
        "question": (
            "Show total recorded net packaging weight for each yarn group, "
            "separately for cartons, pallets, and bags."
        ),
        "domain": "production_packaging",
        "difficulty": "medium",
        "expected_tables": [
            "gnd_scprd.tblPacking",
            "gnd_pjprj.tblInterweaving",
            "gnd_spgod.tblPackagingType",
        ],
        "expected_table_count": 3,
        "relationship_notes": [
            "FK: gnd_scprd.tblPacking.InterWeavingID -> gnd_pjprj.tblInterweaving.ID.",
            "FK: tblPacking.PackagingTypeID -> gnd_spgod.tblPackagingType.ID.",
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "The active ERP entity for همبافت is tblInterweaving; tblHambaft is "
            "the old entity. Aggregate Packing.NetWeight by interweaving and "
            "packaging type without inventing package-to-weight conversions."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C09",
        "question": (
            "Show recorded cot-diameter readings and grinding completion dates "
            "for SAURER FLYER machines, filtered by machine, completion-date "
            "range, and diameter range. Include every recorded reading in the period."
        ),
        "domain": "maintenance_condition_monitoring",
        "difficulty": "hard",
        "expected_tables": [
            "gnd_amspt.tblFeedbackCheckList",
            "gnd_amspt.tblFeedback",
            "gnd_amspt.tblRoutine",
            "gnd_amast.tblSensor",
            "gnd_amast.tblEquipment",
            "gnd_amast.tblEquipmentKind",
        ],
        "expected_table_count": 6,
        "relationship_notes": [
            "FK: tblFeedbackCheckList.FeedbackID -> gnd_amspt.tblFeedback.ID.",
            "FK: tblFeedbackCheckList.SensorID -> gnd_amast.tblSensor.ID.",
            "FK: tblFeedback.RoutineID -> gnd_amspt.tblRoutine.ID.",
            "FK: tblFeedback.EquipmentID -> gnd_amast.tblEquipment.ID.",
            "FK: tblEquipment.EquipmentKindID -> gnd_amast.tblEquipmentKind.ID.",
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "Use FeedbackCheckList.SensorValue and Feedback.EndDate. Equipment "
            "kind 56 is SAURER FLYER, routine 403 is cot grinding, and sensor 30 "
            "is its cot-diameter sensor. Historical readings exist, but repeated "
            "non-NULL readings for the same machine were not demonstrated."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C10",
        "question": (
            "List maintenance work orders whose proposed dates fall within a "
            "specified date range."
        ),
        "domain": "maintenance_condition_monitoring",
        "difficulty": "easy",
        "expected_tables": ["gnd_amspt.tblWorkOrder"],
        "expected_table_count": 1,
        "relationship_notes": [],
        "feasibility_status": "FEASIBLE",
        "semantic_evaluation_note": (
            "Filter on SuggestedExecutionDate; TargetDate is a different field."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C11",
        "question": (
            "Show each bank guarantee's amount, its deposit amount, and the net "
            "amount after deducting the deposit."
        ),
        "domain": "treasury",
        "difficulty": "easy",
        "expected_tables": ["gnd_firpd.tblBankGuaranty"],
        "expected_table_count": 1,
        "relationship_notes": [],
        "feasibility_status": "FEASIBLE",
        "semantic_evaluation_note": (
            "Amount is AccValue, deposit is computed DepositValue, and requested "
            "net is AccValue - DepositValue. TotalValue instead means AccValue + "
            "WageValue and is not the requested net."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C14",
        "question": (
            "Which yarn groups have at least one numbered lot with positive "
            "posted warehouse stock in the current financial period, without "
            "deducting reservations or allocations?"
        ),
        "domain": "sales",
        "difficulty": "hard",
        "expected_tables": [
            "gnd_spgod.tblGood",
            "gnd_pjprj.tblInterweaving",
            "gnd_scinv.tblEnter",
            "gnd_scinv.tblEnterDetail",
            "gnd_scinv.tblExit",
            "gnd_scinv.tblExitDetail",
            "gnd_fiaci.tblPeriodSpec",
        ],
        "expected_table_count": 7,
        "relationship_notes": [
            "FK: gnd_scinv.tblEnterDetail.EnterID -> gnd_scinv.tblEnter.ID.",
            "FK: gnd_scinv.tblExitDetail.ExitID -> gnd_scinv.tblExit.ID.",
            (
                "FKs: tblEnterDetail.CredbGoodID and "
                "tblExitDetail.CredbGoodID -> gnd_spgod.tblGood.ID."
            ),
            (
                "Logical subtype join: tblGood.InterweavingID = "
                "gnd_pjprj.tblInterweaving.ID. The declared FK targets the shared "
                "gnd_pjprj.tblProject.ID key; the ERP good view explicitly uses "
                "the interweaving subtype relationship."
            ),
            (
                "Financial-period membership is a date-range join from movement "
                "DoneDate to tblPeriodSpec.BeginDate/EndDate, as used by the "
                "inspected stock views and functions."
            ),
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "Compute posted stock as receipts minus issues by item and warehouse; "
            "require nonblank Good.LotNumber and positive balance. tblInventoryQty "
            "is empty in this snapshot. Do not add reservation, allocation, "
            "saleability, or order-quantity rules."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
    {
        "id": "REAL-C15",
        "question": (
            "For a selected employee and payroll month, show the leave balance "
            "in days recorded in that month's payroll work record."
        ),
        "domain": "hr_attendance",
        "difficulty": "easy",
        "expected_tables": [
            "gnd_hrpyr.tblWorkTime",
            "gnd_egbse.tblYearMonth",
        ],
        "expected_table_count": 2,
        "relationship_notes": [
            "FK: gnd_hrpyr.tblWorkTime.YearMonthID -> gnd_egbse.tblYearMonth.ID."
        ],
        "feasibility_status": "FEASIBLE WITH WORDING CLARIFICATION",
        "semantic_evaluation_note": (
            "RemainedLeave is a physically stored monthly value, uniquely keyed "
            "by employee and year-month. Preserve NULL as not recorded; do not "
            "claim that the value independently proves correct month-end accrual "
            "or carry-forward logic."
        ),
        "top10_full_coverage_possible": True,
        "top10_recall_ceiling": 1.0,
    },
]

