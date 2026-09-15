tests = [
    {
        "question": (
            "List goods with their good code, barcode, Farsi and English "
            "names, retail unit price, and VAT flag."
        ),
        "expected_tables": [
            "gnd_spgod.tblGood",
        ],
        "reason": (
            "The goods table directly contains the requested identifiers, "
            "names, price, and VAT columns."
        ),
        "difficulty": "easy",
    },
    {
        "question": (
            "List employees with their employee code, legal first and last "
            "names, employment date, employment end date, and whether they "
            "have left."
        ),
        "expected_tables": [
            "gnd_hrprs.tblEmployee",
        ],
        "reason": (
            "The employee table contains all requested identity and "
            "employment-status fields without requiring a join."
        ),
        "difficulty": "easy",
    },
    {
        "question": (
            "Show sales invoice lines with the invoice code and date, line "
            "sequence, quantity, unit price, discount value, and VAT amount."
        ),
        "expected_tables": [
            "gnd_crsls.tblSalesInvoice",
            "gnd_crsls.tblSalesInvoiceDetail",
        ],
        "reason": (
            "SalesInvoiceDetail.SalesInvoiceID has an explicit foreign key "
            "to SalesInvoice.ID; the header supplies code and date while the "
            "detail supplies line amounts."
        ),
        "difficulty": "medium",
    },
    {
        "question": (
            "Summarize sales quantity and sold value by good and sales "
            "invoice date, showing each good's code and Farsi and English "
            "names."
        ),
        "expected_tables": [
            "gnd_crsls.tblSalesInvoice",
            "gnd_crsls.tblSalesInvoiceDetail",
            "gnd_spgod.tblGood",
        ],
        "reason": (
            "SalesInvoiceDetail links directly to SalesInvoice through "
            "SalesInvoiceID and to tblGood through GoodID; its Qty and "
            "SoldValue columns support the requested aggregation."
        ),
        "difficulty": "hard",
    },
    {
        "question": (
            "Report the recorded quantity of each good in each inventory, "
            "showing the inventory's Farsi and English names and the good's "
            "code and names."
        ),
        "expected_tables": [
            "gnd_scinv.tblInventoryQty",
            "gnd_scinv.tblInventory",
            "gnd_spgod.tblGood",
        ],
        "reason": (
            "InventoryQty contains Qty and has direct foreign keys from "
            "InventoryID to tblInventory and from GoodID to tblGood."
        ),
        "difficulty": "hard",
    },
    {
        "question": (
            "Show purchase order lines with the purchase order code and "
            "date, line quantity, purchase quantity, remaining and "
            "in-queue quantities, request reason, and consumption purpose."
        ),
        "expected_tables": [
            "gnd_scpch.tblPurchaseOrder",
            "gnd_scpch.tblPurchaseOrderDetail",
        ],
        "reason": (
            "PurchaseOrderDetail.PurchaseOrderID has an explicit foreign key "
            "to PurchaseOrder.ID; the requested quantities and reasons are "
            "present on the detail rows."
        ),
        "difficulty": "medium",
    },
    {
        "question": (
            "Compare planned daily production by equipment, showing the "
            "schedule dates, equipment names and technical number, planned "
            "daily production, efficiency, and speed."
        ),
        "expected_tables": [
            "gnd_scprd.tblProductionSchedule",
            "gnd_scprd.tblProductionScheduleDetail",
            "gnd_amast.tblEquipment",
        ],
        "reason": (
            "ProductionScheduleDetail links to ProductionSchedule through "
            "ProductionScheduleID and to tblEquipment through EquipmentID; "
            "it contains DailyProduction, Efficiency, and Speed."
        ),
        "difficulty": "hard",
    },
    {
        "question": (
            "Show quality-control records by date with each inspected good's "
            "code and names, inspected quantity, notified quantity, and "
            "quality-control description."
        ),
        "expected_tables": [
            "gnd_scpch.tblQualityControl",
            "gnd_scpch.tblQualityControlDetail",
            "gnd_spgod.tblGood",
        ],
        "reason": (
            "QualityControlDetail links to QualityControl through "
            "QualityControlID and to tblGood through GoodID; the detail "
            "contains Qty, NotifiQTY, and QCDescription."
        ),
        "difficulty": "hard",
    },
    {
        "question": (
            "Report employee education history with employee code and legal "
            "name, education degree description, graduation date, and score."
        ),
        "expected_tables": [
            "gnd_hrprs.tblEmployee",
            "gnd_hrprs.tblEmployeeEducation",
            "gnd_hrprs.tblEducationDegreeTypeL",
        ],
        "reason": (
            "EmployeeEducation links to tblEmployee through EmployeeID and "
            "to tblEducationDegreeTypeL through EducationTypeID; it directly "
            "stores GraduateDate and Score."
        ),
        "difficulty": "hard",
    },
]
