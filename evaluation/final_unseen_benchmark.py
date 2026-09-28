"""50 human-approved, bounded-validated final-unseen benchmark cases."""

FINAL_UNSEEN_CASES = [{'id': 'FINAL-U01',
  'question': 'Show each sales and services invoice with its invoice date, invoice number, and annual sales '
              'order number.',
  'domain': 'sales',
  'secondary_domains': [],
  'difficulty': 'Easy',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_crsls.tblSalesAndServicesInvoice'],
  'expected_table_count': 1,
  'relationship_notes': 'Single-table invoice projection; no join is required.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Display the annual order number on sales invoices. Normalization changes are '
                        'recorded in the private case-specific fidelity audit.',
  'relationship_types': ['single_table'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['InvoiceID', 'InvoiceNumber', 'InvoiceDate', 'AnnualSalesOrderNumber']},
 {'id': 'FINAL-U02',
  'question': "Show each purchase order with its originating purchase request and the requested item's name, "
              'quantity, and description.',
  'domain': 'purchasing',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_scpch.tblPurchaseOrder',
                      'gnd_scpch.tblPurchaseRequest',
                      'gnd_scpch.tblPurchaseRequestDetail',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 4,
  'relationship_notes': 'PurchaseOrder.FormTypeID/FormID logically identifies PurchaseRequest.ID; '
                        'PurchaseRequestDetail.PurchaseRequestID joins the request; '
                        'PurchaseRequestDetail.GoodID joins Good.ID.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Include the originating purchase request, requested goods, quantity and description '
                        'on purchase-order output. Normalization changes are recorded in the private '
                        'case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['PurchaseOrderID',
                     'PurchaseOrderCode',
                     'PurchaseRequestID',
                     'PurchaseRequestCode',
                     'RequestLineID',
                     'GoodID',
                     'GoodName',
                     'RequestedQty',
                     'Description']},
 {'id': 'FINAL-U03',
  'question': 'Show warehouse item requests whose process is not fully completed, with requester, item, '
              'requested quantity, quantity currently in the purchasing queue, and remaining quantity.',
  'domain': 'purchasing',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_hrprs.tblEmployee',
                      'gnd_scpch.tblGoodServiceRequest',
                      'gnd_scpch.tblGoodServiceRequestDetail',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 4,
  'relationship_notes': 'GoodServiceRequestDetail.GoodServiceRequestID joins the request; '
                        'RequestedEmployeeID joins Employee.ID; detail GoodID joins Good.ID.',
  'semantic_note': 'Human rule: completion is Code=99 on GoodServiceRequest itself. Code is nullable and '
                   'NULL rows exist. The existing fnGoodRequestInQueueFromGoodID explicitly uses '
                   'ISNULL(gsr.Code,-1)<>99; that same NULL-inclusive non-completion rule is used without '
                   'downstream status inference.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human rule: completion is Code=99 on GoodServiceRequest itself. Code is '
                             'nullable and NULL rows exist. The existing fnGoodRequestInQueueFromGoodID '
                             'explicitly uses ISNULL(gsr.Code,-1)<>99; that same NULL-inclusive '
                             'non-completion rule is used without downstream status inference.',
  'semantic_implementation_blocker': False,
  'result_columns': ['RequestID',
                     'RequestCode',
                     'RequestedDate',
                     'EmployeeID',
                     'EmployeeCode',
                     'RequestLineID',
                     'GoodID',
                     'GoodName',
                     'RequestQty',
                     'QtyInQueue',
                     'RemainedQty']},
 {'id': 'FINAL-U04',
  'question': 'List the loading records for @ReportDate by driver, including the total net cargo weight.',
  'domain': 'imports/logistics',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_crsls.tblLoading',
                      'gnd_crsls.tblLoadingDetail',
                      'gnd_crsls.tblLoadingSerialDetail',
                      'gnd_scinv.tblSerial',
                      'gnd_scinv.tblTransportationCompanyDriverDetail',
                      'gnd_scprd.tblPacking',
                      'gnd_scprd.tblRawMaterialPacking',
                      'gnd_scprd.tblWastePacking'],
  'expected_table_count': 8,
  'relationship_notes': 'Loading.TransportationCompanyDriverIG joins TransportationCompanyDriverDetail.IG.',
  'semantic_note': 'Use COALESCE(CargoTotalNetWeight,TotalNetWeight): stored cargo weight when present, '
                   'computed total net weight when NULL. Same-day @ReportDate range; driver via '
                   'TransportationCompanyDriverIG. Explicit latest human decision supersedes the former '
                   'no-fallback interpretation.',
  'fidelity_rationale': 'Explicit latest human-approved meaning supersedes the prior active interpretation; '
                        'private final_authoritative_approval.txt records the decision.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'dependency_note': 'TotalNetWeight fallback uses ERP helper functions; all eight required physical tables '
                     'are included in the metadata-derived closure. No unresolved dependencies or '
                     'current-time helpers.',
  'result_columns': ['LoadingID', 'Code', 'DoneDate', 'DriverRecordID', 'DriverName', 'TotalNetCargoWeight']},
 {'id': 'FINAL-U05',
  'question': 'List sales orders with at least one unshipped line and an annual sales order number greater '
              'than or equal to @MinAnnualSalesOrderNumber.',
  'domain': 'imports/logistics',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_crsls.tblSalesOrder',
                      'gnd_crsls.tblSalesOrderDetail',
                      'gnd_crsls.tblSalesOrderWasteDetail'],
  'expected_table_count': 3,
  'relationship_notes': 'SalesOrderDetail.SalesOrderID joins SalesOrder.ID inside the unshipped-line '
                        'existence test.',
  'semantic_note': 'Human rule: NULL HasShipped means unshipped. DeliveryDate reproduces the existing helper '
                   'branch (OrderTypeID=1267: maximum detail delivery date; otherwise maximum waste-detail '
                   'delivery date) but omits its GETDATE fallback. Missing delivery dates remain NULL.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human rule: NULL HasShipped means unshipped. DeliveryDate reproduces the '
                             'existing helper branch (OrderTypeID=1267: maximum detail delivery date; '
                             'otherwise maximum waste-detail delivery date) but omits its GETDATE fallback. '
                             'Missing delivery dates remain NULL.',
  'semantic_implementation_blocker': False,
  'result_columns': ['SalesOrderID',
                     'Code',
                     'OrderDate',
                     'AnnualSalesOrderNumber',
                     'DeliveryDate',
                     'DeliveryToCustomerID']},
 {'id': 'FINAL-U06',
  'question': 'Show purchase-invoice goods lines alongside each linked warehouse receipt, including the '
              'receipt identifier, warehouse, item code and description, invoiced quantity, and invoiced '
              'amount.',
  'domain': 'inventory',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_scinv.tblEnter',
                      'gnd_scinv.tblInventory',
                      'gnd_scpch.tblPurchaseInvoiceGoodAndService',
                      'gnd_scpch.tblPurchaseInvoiceGoodDetailEnter',
                      'gnd_scpch.tblPurchaseInvoiceSeparatedEnter',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 6,
  'relationship_notes': 'PurchaseInvoiceGoodDetailEnter.PurchaseInvoiceGoodAndServiceID -> '
                        'PurchaseInvoiceGoodAndService.ID (FK). '
                        'PurchaseInvoiceSeparatedEnter.FormTypeID=1513618/FormID -> invoice.ID; '
                        'Enter.FormTypeID=27887/FormID -> separated receipt.ID (explicit report metadata, '
                        'polymorphic). Enter.CredbInventoryID -> Inventory.ID; invoice detail.GoodID -> '
                        'Good.ID (FK). ',
  'semantic_note': 'Source-linked report definition proves invoice -> separated receipt (FormTypeID 1513618) '
                   '-> warehouse receipt (27887). Invoice.FormID alone is not a receipt ID. Preserve the '
                   'report grain: invoice goods line alongside each linked receipt, not an asserted '
                   'receipt-detail allocation.',
  'fidelity_rationale': 'Add warehouse identifiers and item codes to the complete purchase-invoice report '
                        'associated with warehouse receipts. Normalization changes are recorded in the '
                        'private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['PurchaseInvoiceID',
                     'PurchaseInvoiceCode',
                     'ReceiptID',
                     'InvoiceLineID',
                     'InventoryID',
                     'InventoryName',
                     'GoodID',
                     'GoodCode',
                     'GoodName',
                     'Qty',
                     'AccValue']},
 {'id': 'FINAL-U07',
  'question': 'For each employee and payroll month, show the number of recorded additional off dates.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrcio.tblEmployeeShiftAdditionalOffDates',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 3,
  'relationship_notes': 'EmployeeID joins Employee.ID; an off date is assigned to YearMonth by the inclusive '
                        'FromDate/ToDate interval (a logical date-range join).',
  'semantic_note': 'Human decision confirms explicitly recorded additional off dates only; ordinary roster '
                   'off days are excluded. Existing SQL is unchanged. An empty source table is retained as a '
                   'valid empty result.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision confirms explicitly recorded additional off dates only; '
                             'ordinary roster off days are excluded. Existing SQL is unchanged. An empty '
                             'source table is retained as a valid empty result.',
  'semantic_implementation_blocker': False,
  'result_columns': ['EmployeeID',
                     'EmployeeCode',
                     'YearMonthID',
                     'Year',
                     'MonthID',
                     'AdditionalOffDateCount']},
 {'id': 'FINAL-U08',
  'question': 'For exit-permission requests in the selected date range, show counts by department, exit '
              'reason and workflow status, and average minutes from initial request registration to final '
              'approval, excluding never-approved requests from the average even when retained in counts.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbpm.tblProcessStep',
                      'gnd_egbse.tblDepartment',
                      'gnd_egwfm.tblRunStatusTypeL',
                      'gnd_egwfm.tblWork',
                      'gnd_egwfm.tblWorkRoute',
                      'gnd_hrcio.tblEmployeeExitPermission',
                      'gnu_hrcio.xblEmployeeExitPermission'],
  'expected_table_count': 7,
  'relationship_notes': 'Permit.ID -> xblEmployeeExitPermission.ID; Work/WorkRoute FormTypeID=39754 and '
                        'FormID -> permit.ID; WorkRoute.CurrentProcessStepID -> ProcessStep.ID. Approval '
                        'aggregation has one row per permit across all matching routes.',
  'semantic_note': 'CLOSED authoritative rule implemented: initial registration is '
                   'xblEmployeeExitPermission.CreateDate. Final approval is MAX '
                   'WorkRoute.LastPlaceChangeDate at a ProcessStep named End, across every matching '
                   'permit-form route and process. Status grouping retains the previous latest-task '
                   'convention only for the status label; it never determines approval. Never-approved '
                   'permits remain in counts and contribute NULL to AVG. RunStatusTypeID=3 alone is not '
                   'approval.',
  'fidelity_rationale': 'CLOSED authoritative rule implemented: initial registration is '
                        'xblEmployeeExitPermission.CreateDate. Final approval is MAX '
                        'WorkRoute.LastPlaceChangeDate at a ProcessStep named End, across every matching '
                        'permit-form route and process. Status grouping retains the previous latest-task '
                        'convention only for the status label; it never determines approval. Never-approved '
                        'permits remain in counts and contribute NULL to AVG. RunStatusTypeID=3 alone is not '
                        'approval.',
  'relationship_types': ['physical_fk_or_key_join',
                         'polymorphic',
                         'logical_or_temporal',
                         'aggregation',
                         'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'result_columns': ['DepartmentID',
                     'DepartmentName',
                     'ExitReason',
                     'WorkflowStatusID',
                     'WorkflowStatus',
                     'PermitCount',
                     'AverageElapsedMinutes'],
  'semantic_implementation_blocker': False},
 {'id': 'FINAL-U09',
  'question': 'Show the history of employee shift modifications, including the modification date, previous '
              'shift, new shift, and recorded change description.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_hrcio.tblEmployeeShift',
                      'gnd_hrcio.tblEmployeeShiftModifications',
                      'gnd_hrcio.tblShiftTemplate',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 4,
  'relationship_notes': 'Modification.EmployeeID -> Employee.ID. Base EmployeeShift joins the same '
                        'employee/date using the approved interval/status predicates and maximum eligible '
                        'FromDate; identical tied ShiftIDs are deduplicated. Both ShiftIDs -> '
                        'ShiftTemplate.ID.',
  'semantic_note': 'CLOSED authoritative rule implemented: modification.ShiftID is the new daily override. '
                   'Previous effective shift comes from the greatest eligible base-assignment FromDate on '
                   'that same date, with EndDateStatus eligibility and CurrentStatusTypeID NOT IN (4,6). '
                   'DISTINCT collapses identical ShiftIDs tied at that date; the authoritative diagnostic '
                   'found no different ShiftIDs among such ties. No LAG, prior-day substitution, or ID '
                   'ordering is used.',
  'fidelity_rationale': 'CLOSED authoritative rule implemented: modification.ShiftID is the new daily '
                        'override. Previous effective shift comes from the greatest eligible base-assignment '
                        'FromDate on that same date, with EndDateStatus eligibility and CurrentStatusTypeID '
                        'NOT IN (4,6). DISTINCT collapses identical ShiftIDs tied at that date; the '
                        'authoritative diagnostic found no different ShiftIDs among such ties. No LAG, '
                        'prior-day substitution, or ID ordering is used.',
  'relationship_types': ['physical_fk_or_key_join', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'result_columns': ['ModificationID',
                     'EmployeeID',
                     'EmployeeCode',
                     'ModificationDate',
                     'PreviousShiftID',
                     'PreviousShift',
                     'NewShiftID',
                     'NewShift',
                     'DescriptionUpdated'],
  'semantic_implementation_blocker': False},
 {'id': 'FINAL-U10',
  'question': 'For each employee and complete payroll month between @FromPayrollMonthID and '
              '@ThroughPayrollMonthID, show stored work hours, non-work hours, regular overtime hours, leave '
              'days and hours, and mission days and hours.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth', 'gnd_hrprs.tblEmployee', 'gnd_hrpyr.tblWorkTime'],
  'expected_table_count': 3,
  'relationship_notes': 'WorkTime.EmployeeID -> Employee.ID and WorkTime.YearMonthID -> YearMonth.ID. '
                        'Parameter month rows bound complete calendar periods.',
  'semantic_note': 'Monthly WorkTime facts are authoritative. Non-work is stored shortfall '
                   '(SaatKasrKarcdur); overtime is the stored regular overtime component. Duration fields '
                   'are minutes, divided by 60.0; AnnualLeave and TedadRuzMamuriat are days. Month '
                   'parameters are monthly YearMonth IDs, ordered by calendar dates, not numeric IDs. No '
                   'event recomputation or proration.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Monthly WorkTime facts are authoritative. Non-work is stored shortfall '
                             '(SaatKasrKarcdur); overtime is the stored regular overtime component. Duration '
                             'fields are minutes, divided by 60.0; AnnualLeave and TedadRuzMamuriat are '
                             'days. Month parameters are monthly YearMonth IDs, ordered by calendar dates, '
                             'not numeric IDs. No event recomputation or proration.',
  'semantic_implementation_blocker': False,
  'result_columns': ['WorkTimeID',
                     'EmployeeID',
                     'EmployeeCode',
                     'YearMonthID',
                     'WorkHours',
                     'NonWorkHours',
                     'RegularOvertimeHours',
                     'LeaveDays',
                     'LeaveHours',
                     'MissionDays',
                     'MissionHours']},
 {'id': 'FINAL-U11',
  'question': 'For each employee and payroll month with active meal credits, show total recorded meal '
              'entitlement, requested meal quantity, delivered meal count, and remaining entitlement after '
              'delivery.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrfod.tblEmployeeFood',
                      'gnd_hrfod.tblEmployeeFoodDelivery',
                      'gnd_hrfod.tblEmployeeFoodRequest',
                      'gnd_hrfod.tblEmployeeFoodRequestDetail',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 6,
  'relationship_notes': 'Employee identity links independent credit/request/delivery aggregates. '
                        'RequestDetail.EmployeeFoodRequestID -> Request.ID. Date-range joins to monthly '
                        'YearMonth are logical calendar joins; no FK is claimed.',
  'semantic_note': 'Active FoodCount credits are additive per employee/payroll month. Requests and delivered '
                   'meals are independently aggregated over the same nonoverlapping monthly YearMonth dates; '
                   'each total joins once. Remaining = credits minus delivered rows. Months without credits '
                   'are outside the entitlement-led report.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Active FoodCount credits are additive per employee/payroll month. Requests and '
                             'delivered meals are independently aggregated over the same nonoverlapping '
                             'monthly YearMonth dates; each total joins once. Remaining = credits minus '
                             'delivered rows. Months without credits are outside the entitlement-led report.',
  'semantic_implementation_blocker': False,
  'result_columns': ['EmployeeID',
                     'EmployeeCode',
                     'YearMonthID',
                     'RecordedMealEntitlement',
                     'RequestedMealQuantity',
                     'DeliveredMealCount',
                     'RemainingEntitlement']},
 {'id': 'FINAL-U12',
  'question': 'For each employee loan request, show the request date, stored portion value, stored maximum '
              "loan amount, and the employee's latest recorded fund balance as of @AsOfDate.",
  'domain': 'payroll',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_hrprs.tblEmployee',
                      'gnd_hrpyr.tblCofferMembership',
                      'gnd_hrpyr.tblEmployeeLoanRequest'],
  'expected_table_count': 3,
  'relationship_notes': 'LoanRequest.EmployeeID joins Employee.ID; fund membership is selected logically by '
                        'EmployeeID and the effective date interval.',
  'semantic_note': 'Stored UpperLoanAmount is the authoritative maximum; PortionValue remains stored. '
                   'Additional balance is latest dated CofferMembership row valid at @AsOfDate, ordered '
                   'FromDate DESC, ID DESC; it never recalculates the ceiling.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Stored UpperLoanAmount is the authoritative maximum; PortionValue remains '
                             'stored. Additional balance is latest dated CofferMembership row valid at '
                             '@AsOfDate, ordered FromDate DESC, ID DESC; it never recalculates the ceiling.',
  'semantic_implementation_blocker': False,
  'result_columns': ['LoanRequestID',
                     'EmployeeID',
                     'EmployeeCode',
                     'RequestDate',
                     'StoredPortionValue',
                     'StoredMaximumLoanAmount',
                     'MembershipID',
                     'LatestRecordedFundBalance',
                     'BalanceEffectiveFrom']},
 {'id': 'FINAL-U13',
  'question': 'Show total packed net production by interweaving, including yarn type, spinning system, '
              'quality, and spinning count for filtering.',
  'domain': 'production',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_pjprj.tblInterweaving',
                      'gnd_scprd.tblPacking',
                      'gnd_spgod.tblQualityType',
                      'gnd_spgod.tblSpinningCountType',
                      'gnd_spgod.tblSpinningSystemType',
                      'gnd_spgod.tblYarnType'],
  'expected_table_count': 6,
  'relationship_notes': "Packing.InterWeavingID joins Interweaving.ID; Interweaving's yarn, spinning-system, "
                        'quality, and spinning-count IDs join their lookup tables.',
  'semantic_note': 'Production quantity is the sum of stored Packing.NetWeight.',
  'fidelity_rationale': 'Enable yarn-group attribute filtering in production reporting. Normalization '
                        'changes are recorded in the private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['InterweavingID',
                     'InterweavingCode',
                     'YarnType',
                     'SpinningSystem',
                     'Quality',
                     'SpinningCount',
                     'TotalPackedNetWeight']},
 {'id': 'FINAL-U14',
  'domain': 'production',
  'question': 'For each bobbin-label record, show its yarn-group code and the spinning-system name defined '
              'for that yarn group.',
  'difficulty': 'Hard',
  'secondary_domains': ['projects'],
  'expected_tables': ['gnd_pjprj.tblInterweaving',
                      'gnd_scprd.tblSpindleLable',
                      'gnd_spgod.tblSpinningSystemType'],
  'relationship_notes': 'SpindleLable.InterweavingID -> Interweaving.ID; Interweaving.SpinningSystemTypeID '
                        '-> SpinningSystemType.ID are explicit FKs.',
  'semantic_note': 'One row per stored bobbin-label record, not per generated printed label. The '
                   'spinning-system name is its stored Persian display name; no translation or machine-name '
                   'substitution. UI editability and mandatory-entry changes are outside the extracted '
                   'reporting need.',
  'fidelity_rationale': 'The source explicitly requests yarn-group-defined spinning-system information on '
                        'bobbin labels. Physical mappings are verified by ERP form metadata.',
  'relationship_types': ['explicit_fk'],
  'expected_table_count': 3,
  'feasibility_status': 'FEASIBLE',
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'replacement_human_review_status': 'FINAL_APPROVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['BobbinLabelID', 'InterweavingID', 'InterweavingCode', 'SpinningSystemName']},
 {'id': 'FINAL-U15',
  'question': 'List quality-control records since @StartDate for cotton fibers, viscose fibers, paper '
              'bobbins, and plastic bobbins that have no directly associated purchase invoice, including the '
              'item and recorded quantities.',
  'domain': 'quality',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_scpch.tblPurchaseInvoiceGoodAndService',
                      'gnd_scpch.tblQualityControl',
                      'gnd_scpch.tblQualityControlDetail',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 4,
  'relationship_notes': 'QualityControlDetail.QualityControlID joins QualityControl.ID and GoodID joins '
                        'Good.ID; invoice absence uses the logical FormTypeID/FormID source-document link.',
  'semantic_note': 'Authoritative non-asset scope: GoodGroupID 1487/1488/1489/1490. Direct invoice '
                   'FormTypeID=1684173/FormID=QualityControl.ID is sufficient. No broad GoodType or '
                   'packaging-supply category is substituted.',
  'fidelity_rationale': 'Authoritative non-asset scope: GoodGroupID 1487/1488/1489/1490. Direct invoice '
                        'FormTypeID=1684173/FormID=QualityControl.ID is sufficient. No broad GoodType or '
                        'packaging-supply category is substituted.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'result_columns': ['QualityControlID',
                     'Code',
                     'DoneDate',
                     'QualityControlLineID',
                     'GoodID',
                     'GoodCode',
                     'GoodName',
                     'Qty',
                     'NotifiQTY',
                     'CQty'],
  'semantic_implementation_blocker': False},
 {'id': 'FINAL-U16',
  'question': 'List generated maintenance work orders that have no assigned responsible employee, including '
              'equipment, routine, and suggested execution date.',
  'domain': 'assets/maintenance',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_amast.tblEquipment', 'gnd_amspt.tblRoutine', 'gnd_amspt.tblWorkOrder'],
  'expected_table_count': 3,
  'relationship_notes': 'WorkOrder.EquipmentID joins Equipment.ID and RoutineID joins Routine.ID.',
  'semantic_note': 'Human-approved unassigned criterion is solely ResponsibleEmployeeID IS NULL; no '
                   'scheduling, recurrence, team, contractor or due-date condition.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human-approved unassigned criterion is solely ResponsibleEmployeeID IS NULL; '
                             'no scheduling, recurrence, team, contractor or due-date condition.',
  'semantic_implementation_blocker': False,
  'result_columns': ['WorkOrderID',
                     'Code',
                     'WorkOrderTitle',
                     'SuggestedExecutionDate',
                     'EquipmentID',
                     'EquipmentName',
                     'RoutineID',
                     'RoutineName']},
 {'id': 'FINAL-U17',
  'domain': 'assets/maintenance',
  'question': 'For @RoutineID, list the recorded overlapping maintenance activities, showing the '
              'activity-card name and each covered activity identifier and name.',
  'difficulty': 'Medium',
  'secondary_domains': [],
  'expected_tables': ['gnd_amspt.tblRoutine', 'gnd_amspt.tblRoutineCovered'],
  'relationship_notes': 'RoutineCovered.RoutineID -> Routine.ID and RoutineCovered.CoveredRoutineID -> '
                        'Routine.ID are explicit FKs; Routine is joined twice in different roles.',
  'semantic_note': 'Overlapping means the explicitly stored coverage relation labelled Covered Routine in '
                   'ERP metadata. It does not mean calculated time overlap or simultaneous/prerequisite '
                   'routines. One row per coverage-detail IG. @RoutineID replaces source-specific activity '
                   'identifiers.',
  'fidelity_rationale': 'The source says populated overlapping-activity details are not visible on activity '
                        'cards. The normalized question retrieves those existing relationships without '
                        'changing them.',
  'relationship_types': ['explicit_fk'],
  'expected_table_count': 2,
  'feasibility_status': 'FEASIBLE',
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'replacement_human_review_status': 'FINAL_APPROVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['RoutineID', 'RoutineName', 'CoverageLineID', 'CoveredRoutineID', 'CoveredRoutineName']},
 {'id': 'FINAL-U18',
  'question': 'List payment requests dated from @FromDate through @ThroughDate, including each '
              'request-detail row.',
  'domain': 'finance/treasury',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_firpd.tblPayRequest', 'gnd_firpd.tblPayRequestDetail'],
  'expected_table_count': 2,
  'relationship_notes': 'PayRequestDetail.PayRequestID -> PayRequest.ID. One row per request detail; no '
                        'payment-execution join.',
  'semantic_note': 'Human decision limits the report to request plus request-detail grain, one result row '
                   'per request detail. The date range filters PayRequestDate. RequestedExecutionDate is the '
                   'requested header date, not an executed payment. No PayRequestPayment dependency or '
                   'payment execution fields remain.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision limits the report to request plus request-detail grain, one '
                             'result row per request detail. The date range filters PayRequestDate. '
                             'RequestedExecutionDate is the requested header date, not an executed payment. '
                             'No PayRequestPayment dependency or payment execution fields remain.',
  'semantic_implementation_blocker': False,
  'result_columns': ['PayRequestID',
                     'Code',
                     'PayRequestDate',
                     'RequestedExecutionDate',
                     'PayRequestLineID',
                     'Sequence',
                     'Amount',
                     'LineDescription',
                     'PayDate']},
 {'id': 'FINAL-U19',
  'question': 'Show each bank receipt with its accounting detail lines, including account, amount, and '
              'descriptions.',
  'domain': 'finance/treasury',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_fiaci.tblAccount', 'gnd_firpd.tblBankInput', 'gnd_firpd.tblBankInputDetail'],
  'expected_table_count': 3,
  'relationship_notes': 'BankInputDetail.BankInputID joins BankInput.ID and AccountID joins Account.ID.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Display accounting document detail when a bank receipt is opened. Normalization '
                        'changes are recorded in the private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['BankReceiptID',
                     'Code',
                     'DoneDate',
                     'ReceiptAmount',
                     'AccountingLineID',
                     'Sequence',
                     'AccountID',
                     'AccountCode',
                     'AccountName',
                     'LineAmount',
                     'LineDescription',
                     'TransDetail']},
 {'id': 'FINAL-U20',
  'question': 'For the selected accounting detail entity, show every journal line and the account through '
              'which it moved.',
  'domain': 'finance/treasury',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_fiaci.tblAccount',
                      'gnd_fiaci.tblTrans',
                      'gnd_fiaci.tblTransDetail',
                      'gnd_fiaci.tblTransDetailDetail'],
  'expected_table_count': 4,
  'relationship_notes': 'TransDetailDetail.TransDetailIG joins TransDetail.IG; TransDetail.TransID joins '
                        'Trans.ID and AccountID joins Account.ID; FormTypeID/FormID selects the polymorphic '
                        'source entity.',
  'semantic_note': 'The selected accounting detail entity is supplied by FormTypeID and FormID parameters.',
  'fidelity_rationale': 'Show the accounts and journal movements associated with a selected analytic entity. '
                        'Normalization changes are recorded in the private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['TransactionID',
                     'TransactionCode',
                     'DocDate',
                     'JournalLineID',
                     'RowNumber',
                     'AccountID',
                     'AccountCode',
                     'AccountName',
                     'Description',
                     'Debit',
                     'Credit']},
 {'id': 'FINAL-U21',
  'question': 'List each project with its related goods-and-services purchase invoices, including invoice '
              'date, supplier identifier, and total payable.',
  'domain': 'projects',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_pjprj.tblProject', 'gnd_scpch.tblPurchaseInvoiceGoodAndService'],
  'expected_table_count': 2,
  'relationship_notes': 'PurchaseInvoiceGoodAndService.CredbProjectID joins Project.ID.',
  'semantic_note': 'Human decision confirms goods/services purchase invoices only, using their explicit '
                   'CredbProjectID relationship. Existing SQL is unchanged.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision confirms goods/services purchase invoices only, using their '
                             'explicit CredbProjectID relationship. Existing SQL is unchanged.',
  'semantic_implementation_blocker': False,
  'result_columns': ['ProjectID',
                     'ProjectName',
                     'PurchaseInvoiceID',
                     'PurchaseInvoiceCode',
                     'InvoiceDate',
                     'SupplierID',
                     'TotalPayable']},
 {'id': 'FINAL-U22',
  'domain': 'other/unclear',
  'question': 'For each user with a recorded chat visit, show the latest recorded visit date and time.',
  'difficulty': 'Easy',
  'secondary_domains': [],
  'expected_tables': ['gnd_egbse.tblChatLastSeen'],
  'relationship_notes': 'Single-table aggregation by UserID; no user-profile or message-content join is '
                        'required.',
  'semantic_note': 'UserID identifies the user without outputting a username or personal name. '
                   'MAX(LastSeenDate) gives the latest stored chat timestamp if more than one row exists. '
                   'This is not a claim of current online presence, room-specific attendance, or message '
                   'reading.',
  'fidelity_rationale': 'The source asks to display the last date/time of chat visitation. The target stores '
                        'a direct user-level last-seen timestamp.',
  'relationship_types': ['single_table'],
  'expected_table_count': 1,
  'feasibility_status': 'FEASIBLE',
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'replacement_human_review_status': 'FINAL_APPROVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['UserID', 'LastSeenAt']},
 {'id': 'FINAL-U23',
  'question': 'List each role with the systems, forms, and reports assigned to it, including display and '
              'edit permissions.',
  'domain': 'other/unclear',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblRole',
                      'gnd_egbse.tblRoleDomain',
                      'gnd_egbse.tblRoleSystem',
                      'gnd_egbse.tblRoleSystemForm',
                      'gnd_egbse.tblRoleSystemReport',
                      'gnd_egfrm.tblFormType',
                      'gnd_egrpt.tblReport',
                      'gnd_egsys.tblCaption',
                      'gnd_egsys.tblSystem'],
  'expected_table_count': 9,
  'relationship_notes': 'RoleDomain joins Role; RoleSystem joins RoleDomain; form/report permission rows '
                        'join RoleSystem and then their form/report metadata and caption.',
  'semantic_note': 'Forms and reports are combined into one permission-shaped result with UNION ALL.',
  'fidelity_rationale': 'Correct the report of role contents. Normalization changes are recorded in the '
                        'private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['RoleID',
                     'RoleName',
                     'SystemID',
                     'SystemName',
                     'ContentType',
                     'ContentID',
                     'ContentName',
                     'GrantDisplay',
                     'GrantEdit']},
 {'id': 'FINAL-U24',
  'question': 'Show internal letters with their current workflow step and run status so completed and '
              'in-progress letters can be filtered.',
  'domain': 'other/unclear',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbpm.tblProcessStep',
                      'gnd_egwfm.tblRunStatusTypeL',
                      'gnd_egwfm.tblWork',
                      'gnd_ofsct.tblInternalLetter'],
  'expected_table_count': 4,
  'relationship_notes': 'Work.FormTypeID/FormID is the polymorphic logical link to InternalLetter.ID; '
                        'CurrentProcessStepID and RunStatusTypeID join their workflow lookups.',
  'semantic_note': 'Sequential workflow is human-authorized. Latest task is greatest Work.ID, consistent '
                   'with ERP task ordering and the last-step helper, without timestamp ranking. '
                   'FormTypeID=501 identifies InternalLetter.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'logical_or_temporal', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Sequential workflow is human-authorized. Latest task is greatest Work.ID, '
                             'consistent with ERP task ordering and the last-step helper, without timestamp '
                             'ranking. FormTypeID=501 identifies InternalLetter.',
  'semantic_implementation_blocker': False,
  'result_columns': ['InternalLetterID',
                     'Code',
                     'Date',
                     'Subject',
                     'CurrentProcessStepID',
                     'CurrentWorkflowStep',
                     'RunStatusTypeID',
                     'WorkflowRunStatus']},
 {'id': 'FINAL-U25',
  'question': 'List goods consumed more than once by the same requester, with the good identifier and '
              'description, requester, occurrence count, and total consumed quantity.',
  'domain': 'assets/maintenance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_scinv.tblGoodConsume', 'gnd_scinv.tblGoodConsumeDetail', 'gnd_spgod.tblGood'],
  'expected_table_count': 3,
  'relationship_notes': 'GoodConsumeDetail.GoodConsumeID -> GoodConsume.ID; GoodConsumeDetail.GoodID -> '
                        'Good.ID. Equipment and asset joins are not required.',
  'semantic_note': 'Duplicate key is GoodID plus RequesterEmployeeID, not description or asset. Each '
                   'GoodConsumeDetail row is one occurrence. COUNT_BIG(*) counts occurrences; SUM(Qty) '
                   'preserves recorded quantities.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Duplicate key is GoodID plus RequesterEmployeeID, not description or asset. '
                             'Each GoodConsumeDetail row is one occurrence. COUNT_BIG(*) counts occurrences; '
                             'SUM(Qty) preserves recorded quantities.',
  'semantic_implementation_blocker': False,
  'result_columns': ['GoodID',
                     'ItemDescription',
                     'RequesterEmployeeID',
                     'OccurrenceCount',
                     'TotalConsumedQuantity']},
 {'id': 'FINAL-U26',
  'question': 'List maintenance work-order feedback records with a negative recorded work amount, including '
              'the work order, equipment, feedback date, and continuation flag.',
  'domain': 'assets/maintenance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_amast.tblEquipment',
                      'gnd_amspt.tblFeedback',
                      'gnd_amspt.tblWorkOrder',
                      'gnd_egwfm.tblWorkRoute'],
  'expected_table_count': 4,
  'relationship_notes': 'Feedback.ID is also WorkOrder.ID by an explicit FK; EquipmentID joins Equipment.ID, '
                        'and workflow continuation is inferred from a WorkRoute with the feedback form type '
                        'and ID.',
  'semantic_note': 'Human-approved continuation proof is EXISTS WorkRoute with feedback FormTypeID=1136748 '
                   'and FormID=feedback.ID. Any current status is permitted; route existence proves Continue '
                   'at least once.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human-approved continuation proof is EXISTS WorkRoute with feedback '
                             'FormTypeID=1136748 and FormID=feedback.ID. Any current status is permitted; '
                             'route existence proves Continue at least once.',
  'semantic_implementation_blocker': False,
  'result_columns': ['FeedbackID',
                     'WorkOrderID',
                     'WorkOrderCode',
                     'EquipmentID',
                     'EquipmentName',
                     'FeedbackDate',
                     'AmountOfWork',
                     'HasContinued']},
 {'id': 'FINAL-U27',
  'question': 'List cheque-collection accounting lines missing an analytic required by their account, '
              'including the collection document, journal line, account, and missing analytic form type.',
  'domain': 'finance/treasury',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egfrm.tblFormEquivalency',
                      'gnd_fiaci.tblAccountDetail',
                      'gnd_fiaci.tblTrans',
                      'gnd_fiaci.tblTransDetail',
                      'gnd_fiaci.tblTransDetailDetail',
                      'gnd_firpd.tblInputChequeBankReceive'],
  'expected_table_count': 6,
  'relationship_notes': 'TransDetail.TransID -> Trans.ID; TransDetailDetail.TransDetailIG -> TransDetail.IG. '
                        'Required AccountDetail shares AccountID. Trans.FormTypeID/FormID or '
                        'TransDetail.ReferenceFormTypeID/ReferenceFormID resolves polymorphically to '
                        'InputChequeBankReceive at metadata form type 12413. FormEquivalency supplies '
                        'analytic equivalence; no direct collection FK is claimed.',
  'semantic_note': 'Required analytic types come from AccountDetail. Supplied types are matched through '
                   'FormEquivalency using the ERP spMonitorMissingDetailDetail NOT EXISTS pattern. '
                   'Cheque-collection form type 12413 is explicitly mapped in ERP metadata and used by the '
                   'auto-accounting caller. Source-document identity uses either the journal header or '
                   'explicit journal-line reference. Each output row is one missing required type on one '
                   'accounting line; no bank-account NULL shortcut.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'logical_or_temporal', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Required analytic types come from AccountDetail. Supplied types are matched '
                             'through FormEquivalency using the ERP spMonitorMissingDetailDetail NOT EXISTS '
                             'pattern. Cheque-collection form type 12413 is explicitly mapped in ERP '
                             'metadata and used by the auto-accounting caller. Source-document identity uses '
                             'either the journal header or explicit journal-line reference. Each output row '
                             'is one missing required type on one accounting line; no bank-account NULL '
                             'shortcut.',
  'semantic_implementation_blocker': False,
  'result_columns': ['CollectionID',
                     'CollectionCode',
                     'CollectionDate',
                     'TransID',
                     'TransDetailIG',
                     'AccountID',
                     'MissingAnalyticFormTypeID']},
 {'id': 'FINAL-U28',
  'question': 'List payment requests with their counterparty, destination description, and line '
              'descriptions.',
  'domain': 'finance/treasury',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblContact', 'gnd_firpd.tblPayRequest', 'gnd_firpd.tblPayRequestDetail'],
  'expected_table_count': 3,
  'relationship_notes': 'PayRequestDetail.PayRequestID joins PayRequest.ID and PayRequest.PayContactID joins '
                        'Contact.ID.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Add counterparty and destination description to the payment-request management '
                        'report. Normalization changes are recorded in the private case-specific fidelity '
                        'audit.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['PayRequestID',
                     'Code',
                     'PayRequestDate',
                     'PayContactID',
                     'Counterparty',
                     'DestinationDescription',
                     'PayRequestLineID',
                     'Sequence',
                     'LineDescription',
                     'Amount']},
 {'id': 'FINAL-U29',
  'domain': 'finance/treasury',
  'question': 'List received-cheque records whose cheque number occurs more than once on the same receipt '
              'date, including each record identifier, cheque number, receipt date, and duplicate count.',
  'difficulty': 'Medium',
  'secondary_domains': [],
  'expected_tables': ['gnd_firpd.tblInputCheque'],
  'relationship_notes': 'Single-table window count partitioned by ChequeNumber and DoneDate; no counterparty '
                        'join is needed.',
  'semantic_note': 'DoneDate is the receipt date, as confirmed by the ERP cheque report; ExecuteDate is the '
                   'due date. Duplicate equality follows stored ChequeNumber and database collation, with no '
                   'invented bank/account key or string normalization. Empty results are valid after data '
                   'correction.',
  'fidelity_rationale': 'The source explicitly requests a duplicate-cheque report, separate from prevention '
                        'during entry. Gold implements only the read-only report.',
  'relationship_types': ['single_table'],
  'expected_table_count': 1,
  'feasibility_status': 'FEASIBLE',
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'replacement_human_review_status': 'FINAL_APPROVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['InputChequeID', 'ChequeNumber', 'ReceiptDate', 'DuplicateCount']},
 {'id': 'FINAL-U30',
  'question': "For each loading record, show every scanned barcode's weight and the total scanned weight "
              'grouped by interweaving.',
  'domain': 'imports/logistics',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_crsls.tblLoading',
                      'gnd_crsls.tblLoadingScannedBarcode',
                      'gnd_pjprj.tblInterweaving'],
  'expected_table_count': 3,
  'relationship_notes': 'LoadingScannedBarcode.LoadingID joins Loading.ID and InterweavingID joins '
                        'Interweaving.ID; a window sum calculates the loading/interweaving total weight.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Show scanned barcode weights and yarn-group weight totals during loading. '
                        'Normalization changes are recorded in the private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['LoadingID',
                     'LoadingCode',
                     'DoneDate',
                     'ScannedBarcodeID',
                     'Barcode',
                     'Serial',
                     'InterweavingID',
                     'InterweavingCode',
                     'NetWeight',
                     'InterweavingTotalScannedWeight']},
 {'id': 'FINAL-U31',
  'question': 'For the goods on @PurchaseRequestID, show stock by inventory in @PeriodSpecID and @CompanyID '
              'from the fiscal-period beginning through @EndDate: entered quantity, exited quantity, and '
              'remaining quantity. Include zero balances when recorded movements net to zero.',
  'domain': 'inventory',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_fiaci.tblPeriodSpec',
                      'gnd_scinv.tblEnter',
                      'gnd_scinv.tblEnterDetail',
                      'gnd_scinv.tblExit',
                      'gnd_scinv.tblExitDetail',
                      'gnd_scinv.tblInventory',
                      'gnd_scpch.tblPurchaseRequest',
                      'gnd_scpch.tblPurchaseRequestDetail',
                      'gnd_spgod.tblGood',
                      'gnu_scinv.xblEnter',
                      'gnu_scinv.xblExit'],
  'expected_table_count': 11,
  'relationship_notes': 'PurchaseRequestDetail.PurchaseRequestID -> PurchaseRequest.ID and GoodID -> '
                        'Good.ID. vwEnter/vwExit explicitly join header/detail, fiscal period by DoneDate, '
                        'and xbl header identity for company. Aggregation grain is GoodID + '
                        'CredbInventoryID, not request detail.',
  'semantic_note': 'Stock/existence, not kardex. Purchase request selects distinct goods; its date is not a '
                   'stock boundary. Mirrors spGoodExistance: Code IS NOT NULL, movement-date fiscal period, '
                   'creator company, EnterQty minus ExitQty. An out-of-period or NULL end date uses the '
                   'selected period end, as in the ERP procedure. Includes all inventories with eligible '
                   'movements for the selected goods; no user-access predicate is copied. CreatorCompanyID '
                   'requires physical gnu_scinv.xblEnter/xblExit dependencies outside the frozen retrieval '
                   'corpus; they are retained honestly.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Stock/existence, not kardex. Purchase request selects distinct goods; its date '
                             'is not a stock boundary. Mirrors spGoodExistance: Code IS NOT NULL, '
                             'movement-date fiscal period, creator company, EnterQty minus ExitQty. An '
                             'out-of-period or NULL end date uses the selected period end, as in the ERP '
                             'procedure. Includes all inventories with eligible movements for the selected '
                             'goods; no user-access predicate is copied. CreatorCompanyID requires physical '
                             'gnu_scinv.xblEnter/xblExit dependencies outside the frozen retrieval corpus; '
                             'they are retained honestly.',
  'semantic_implementation_blocker': False,
  'result_columns': ['GoodID',
                     'GoodCode',
                     'GoodName',
                     'InventoryID',
                     'InventoryName',
                     'EnteredQuantity',
                     'ExitedQuantity',
                     'RemainingQuantity']},
 {'id': 'FINAL-U32',
  'question': 'List warehouse receipt lines with receipt date, warehouse, item code and description, '
              'quantity, amount, and supplier.',
  'domain': 'inventory',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblContact',
                      'gnd_scinv.tblEnter',
                      'gnd_scinv.tblEnterDetail',
                      'gnd_scinv.tblInventory',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 5,
  'relationship_notes': 'EnterDetail.EnterID -> Enter.ID; Enter.CredbInventoryID -> Inventory.ID; '
                        'EnterDetail.CredbGoodID -> Good.ID; Enter.CredbRelatedToPersonID -> Contact.ID. '
                        'Explicit human-approved receipt-line interpretation.',
  'semantic_note': 'One row per warehouse receipt line. Receipt date from Enter.DoneDate; quantity and '
                   'amount from EnterDetail.Qty/AccValue; supplier from Enter.CredbRelatedToPersonID -> '
                   'Contact.ID. Latest human decision supersedes invoice-line interpretation.',
  'fidelity_rationale': 'Explicit latest human-approved meaning supersedes the prior active interpretation; '
                        'private final_authoritative_approval.txt records the decision.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['WarehouseReceiptID',
                     'ReceiptCode',
                     'ReceiptDate',
                     'InventoryID',
                     'InventoryName',
                     'ReceiptLineID',
                     'GoodID',
                     'GoodCode',
                     'GoodDescription',
                     'Qty',
                     'AccValue',
                     'SupplierID',
                     'SupplierName']},
 {'id': 'FINAL-U33',
  'question': 'List workflow tasks recorded as Done on @ReportDate, showing their task identifiers and '
              'completion timestamps.',
  'domain': 'other/unclear',
  'secondary_domains': [],
  'difficulty': 'Easy',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egwfm.tblWorkEnd'],
  'expected_table_count': 1,
  'relationship_notes': 'WorkEnd.ID is the task identifier and is both the primary key and an FK to Work.ID. '
                        'No Work join is required when only the identifier and recorded completion time are '
                        'requested.',
  'semantic_note': 'DoneStatusTypeL ID=1 explicitly means Done. WorkEnd.CreateDate is written at the end '
                   'action, and the ID primary key gives one stored end row per task. A half-open '
                   'calendar-day filter includes every time on @ReportDate; the relative source date is '
                   'parameterized. Unrequested originating-form identifiers and completion comments were '
                   'removed during wording review. This is the normalized stored-Done information need, not '
                   'a claim to reproduce every undocumented column or status of the original application '
                   'report. Final human approval of the normalized case remains pending.',
  'fidelity_rationale': 'The source requests completed-task information for the requested day. Keep the '
                        'date-specific task list and minimal identifying timestamp; do not introduce form, '
                        'comment, user, web-session or broader closed-status requirements.',
  'relationship_types': ['single_table'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'source_fidelity_review_status': 'REVIEWED_MINIMAL_WORDING; FINAL_HUMAN_APPROVAL_PENDING',
  'replacement_human_review_status': 'FINAL_APPROVED',
  'resolved_human_decision': 'DoneStatusTypeL ID=1 explicitly means Done. WorkEnd.CreateDate is written at '
                             'the end action, and the ID primary key gives one stored end row per task. A '
                             'half-open calendar-day filter includes every time on @ReportDate; the relative '
                             'source date is parameterized. Unrequested originating-form identifiers and '
                             'completion comments were removed during wording review. This is the normalized '
                             'stored-Done information need, not a claim to reproduce every undocumented '
                             'column or status of the original application report. Final human approval of '
                             'the normalized case remains pending.',
  'semantic_implementation_blocker': False,
  'result_columns': ['WorkID', 'CompletedAt']},
 {'id': 'FINAL-U34',
  'question': 'List all currently active workflow tasks still waiting for Continue or a response on the '
              'current assignment, with their assigned person and current step.',
  'domain': 'other/unclear',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbpm.tblProcessStep',
                      'gnd_egbse.tblContact',
                      'gnd_egwfm.tblRunStatusTypeL',
                      'gnd_egwfm.tblWork'],
  'expected_table_count': 4,
  'relationship_notes': "Work's current user, process-step, and run-status IDs join Contact, ProcessStep, "
                        'and RunStatusType; active assigned work excludes completed and information-only '
                        'rows.',
  'semantic_note': 'Every stored Work with RunStatusTypeID IN (0,1) is a current running assignment, '
                   'matching vwRunningWorks. Parallel rows are preserved. LastPlaceChangeDate is the current '
                   'assignment arrival timestamp; CurrentUserID joins Contact directly and may remain NULL '
                   'for role/position/team assignments.',
  'fidelity_rationale': 'Every stored Work with RunStatusTypeID IN (0,1) is a current running assignment, '
                        'matching vwRunningWorks. Parallel rows are preserved. LastPlaceChangeDate is the '
                        'current assignment arrival timestamp; CurrentUserID joins Contact directly and may '
                        'remain NULL for role/position/team assignments.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'result_columns': ['WorkID',
                     'FormTypeID',
                     'FormID',
                     'AssignedDate',
                     'CurrentUserID',
                     'CurrentAssignee',
                     'CurrentProcessStepID',
                     'CurrentStep',
                     'RunStatusTypeID',
                     'RunStatus'],
  'semantic_implementation_blocker': False},
 {'id': 'FINAL-U35',
  'question': 'List internal letters with their sent date, sender, recipients, and subject.',
  'domain': 'other/unclear',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblContact',
                      'gnd_ofsct.tblInternalLetter',
                      'gnd_ofsct.tblRecEmpInternalLetter'],
  'expected_table_count': 3,
  'relationship_notes': 'InternalLetter.SenderID joins Contact; RecEmpInternalLetter joins the letter and '
                        'its PersonID joins Contact for recipients.',
  'semantic_note': 'Human decision requests sent date only. InternalLetter.Date supplies SentDate; no '
                   'time-of-day or workflow timestamp is inferred.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision requests sent date only. InternalLetter.Date supplies SentDate; '
                             'no time-of-day or workflow timestamp is inferred.',
  'semantic_implementation_blocker': False,
  'result_columns': ['InternalLetterID',
                     'Code',
                     'SentDate',
                     'Subject',
                     'SenderID',
                     'Sender',
                     'RecipientID',
                     'Recipient',
                     'IsMainRecipient']},
 {'id': 'FINAL-U36',
  'question': 'For each employee and payroll month, show employee code, holiday-day count, regular overtime '
              'hours, and Friday overtime hours.',
  'domain': 'payroll',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth', 'gnd_hrprs.tblEmployee', 'gnd_hrpyr.tblWorkTime'],
  'expected_table_count': 3,
  'relationship_notes': 'WorkTime.EmployeeID and YearMonthID join Employee and YearMonth.',
  'semantic_note': 'Human decision confirms Employee.EmployeeCode. SaatEzafeKarcdur and SaatJomehKaricdur '
                   'store minutes; divide by 60.0 for Hours outputs. HolidayDayCount remains the stored day '
                   'count.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision confirms Employee.EmployeeCode. SaatEzafeKarcdur and '
                             'SaatJomehKaricdur store minutes; divide by 60.0 for Hours outputs. '
                             'HolidayDayCount remains the stored day count.',
  'semantic_implementation_blocker': False,
  'result_columns': ['WorkTimeID',
                     'EmployeeID',
                     'EmployeeCode',
                     'YearMonthID',
                     'Year',
                     'MonthID',
                     'HolidayDayCount',
                     'RegularOvertimeHours',
                     'FridayOvertimeHours']},
 {'id': 'FINAL-U37',
  'question': 'For each employee, show the monthly and annual remaining-leave balances used by the '
              'leave-request form for the Persian month and leave year containing @AsOfDate, using only '
              'finally approved leave usage.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblConvertDateTypeL',
                      'gnd_egbse.tblPersonStatus',
                      'gnd_egbse.tblPosition',
                      'gnd_egbse.tblSecurityConfig',
                      'gnd_egbse.tblUnit',
                      'gnd_egbse.tblUser',
                      'gnd_egbse.tblYearMonth',
                      'gnd_egsys.tblSystemConfig',
                      'gnd_egsys.tblSystemConfigDetail',
                      'gnd_hrcio.tblAttendenceRules',
                      'gnd_hrcio.tblCalendarHolidays',
                      'gnd_hrcio.tblCardLog',
                      'gnd_hrcio.tblEmployeeLeave',
                      'gnd_hrcio.tblEmployeeSavedLeave',
                      'gnd_hrcio.tblEmployeeShift',
                      'gnd_hrcio.tblEmployeeShiftModifications',
                      'gnd_hrcio.tblShift',
                      'gnd_hrcio.tblShiftDetail',
                      'gnd_hrcio.tblShiftTemplate',
                      'gnd_hrcio.tblShiftTemplateDetail',
                      'gnd_hrcio.tblWorkShiftType',
                      'gnd_hrprs.tblContract',
                      'gnd_hrprs.tblEmployee',
                      'gnd_hrprs.tblEmployeeEmploymentStatus',
                      'gnd_hrprs.tblEmployeeIncentive',
                      'gnu_hrcio.xblEmployeeShift'],
  'expected_table_count': 26,
  'relationship_notes': 'Calendar employee/day consumption feeds the original request and annual-cap period '
                        'calculations. Leave, shifts, clocks, employment status, attendance rules, saved '
                        'leave and configuration follow the inspected source joins; required view '
                        'dependencies are included explicitly.',
  'semantic_note': 'SELECT-only transcription of the authoritative leave-request and annual-cap '
                   'calculations. Approved daily leave takes precedence at employee/date grain, including '
                   'zero daily consumption; hourly contribution on that date is suppressed. All '
                   'otherwise-valid clock events across CardCode values form one employee/day stream. The '
                   'existing fnLeaveCalc effective-clock ordering and pairing are retained; CardCode neither '
                   'splits the pivot nor selects a result. Configuration, employment proration, holiday '
                   'adjustments, carry-forward and annual-cap incentives are retained. Both human '
                   'clarifications are implemented; bounded execution and private regressions passed.',
  'fidelity_rationale': 'SELECT-only transcription of the authoritative leave-request and annual-cap '
                        'calculations. Approved daily leave takes precedence at employee/date grain, '
                        'including zero daily consumption; hourly contribution on that date is suppressed. '
                        'All otherwise-valid clock events across CardCode values form one employee/day '
                        'stream. The existing fnLeaveCalc effective-clock ordering and pairing are retained; '
                        'CardCode neither splits the pivot nor selects a result. Configuration, employment '
                        'proration, holiday adjustments, carry-forward and annual-cap incentives are '
                        'retained. Both human clarifications are implemented; bounded execution and private '
                        'regressions passed.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'result_columns': ['EmployeeID', 'MonthlyRemainingLeaveMinutes', 'AnnualRemainingLeaveMinutes'],
  'semantic_implementation_blocker': False,
  'reference_sql_status': 'SELECT_ONLY_INLINE_BOUNDED_VALIDATED'},
 {'id': 'FINAL-U38',
  'question': 'Show the recorded departed employees for HR evaluation @EvaluationID covering three payroll '
              'months, with their hire and termination dates.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrapr.tblManagerHRFeedback',
                      'gnd_hrapr.tblManagerHRFeedbackLeavedEmployeeDetail'],
  'expected_table_count': 3,
  'relationship_notes': 'LeavedEmployeeDetail.ManagerHRFeedbackID -> ManagerHRFeedback.ID; parent '
                        'FromYearMonthID/ToYearMonthID -> YearMonth.ID. Detail dates filtered to that '
                        'period.',
  'semantic_note': 'One row per recorded departed-employee detail in the selected HR evaluation, restricted '
                   'to its stored payroll-period boundaries. @EvaluationID must identify an evaluation '
                   'covering three payroll months. Hire and termination dates are the recorded detail fields '
                   'populated by the ERP HR-evaluation procedure. The independently requested '
                   'active-employee score recalculation is outside this atomic departed-employee reporting '
                   'requirement. No live shift attribution is invented.',
  'fidelity_rationale': 'One row per recorded departed-employee detail in the selected HR evaluation, '
                        'restricted to its stored payroll-period boundaries. @EvaluationID must identify an '
                        'evaluation covering three payroll months. Hire and termination dates are the '
                        'recorded detail fields populated by the ERP HR-evaluation procedure. The '
                        'independently requested active-employee score recalculation is outside this atomic '
                        'departed-employee reporting requirement. No live shift attribution is invented.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'result_columns': ['EvaluationID', 'UnitID', 'EmployeeID', 'HireDate', 'TerminationDate'],
  'semantic_implementation_blocker': False,
  'replacement_human_review_status': 'FINAL_APPROVED'},
 {'id': 'FINAL-U39',
  'question': "Summarize monthly employee work hours and regular overtime hours by each employee's last "
              'effective organizational position in that payroll month.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrprs.tblContract',
                      'gnd_hrprs.tblLegalPosition',
                      'gnd_hrpyr.tblWorkTime'],
  'expected_table_count': 4,
  'relationship_notes': 'WorkTime.YearMonthID -> YearMonth.ID. EmployeeID correlates the one effective '
                        'Contract selected per fact. Contract.LegalPositionID -> LegalPosition.ID; no '
                        'many-contract aggregation.',
  'semantic_note': 'Uses the exact interval eligibility and FromDate DESC, ID DESC ordering of '
                   'spEmployeeWorkTimeReportNew contract selection, separately for each payroll month. One '
                   'contract result per WorkTime row; no splitting or multiplication. Missing assignment is '
                   'retained as NULL. Stored minutes divided by 60.0.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Uses the exact interval eligibility and FromDate DESC, ID DESC ordering of '
                             'spEmployeeWorkTimeReportNew contract selection, separately for each payroll '
                             'month. One contract result per WorkTime row; no splitting or multiplication. '
                             'Missing assignment is retained as NULL. Stored minutes divided by 60.0.',
  'semantic_implementation_blocker': False,
  'result_columns': ['YearMonthID',
                     'LegalPositionID',
                     'ApprovedPosition',
                     'EmployeeCount',
                     'TotalWorkHours',
                     'TotalRegularOvertimeHours']},
 {'id': 'FINAL-U40',
  'question': 'Summarize stored work hours, regular overtime hours, and hourly leave by personnel group for '
              'complete payroll months from @FromPayrollMonthID through @ThroughPayrollMonthID, attributing '
              "each monthly fact to the employee's last effective personnel group that month.",
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrprs.tblContract',
                      'gnd_hrprs.tblJobGroup',
                      'gnd_hrpyr.tblWorkTime'],
  'expected_table_count': 4,
  'relationship_notes': 'Monthly WorkTime -> YearMonth; one effective Contract by EmployeeID/month; '
                        'Contract.JobGroupID -> JobGroup.ID. Personnel group is separate from Unit and '
                        'Department.',
  'semantic_note': 'Complete monthly facts only; no daily proration. Effective contract interval/order '
                   'follows spEmployeeWorkTimeReportNew. OUTER APPLY returns at most one assignment, '
                   'retaining unmatched facts under NULL group. Duration fields are stored minutes, divided '
                   'by 60.0.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Complete monthly facts only; no daily proration. Effective contract '
                             'interval/order follows spEmployeeWorkTimeReportNew. OUTER APPLY returns at '
                             'most one assignment, retaining unmatched facts under NULL group. Duration '
                             'fields are stored minutes, divided by 60.0.',
  'semantic_implementation_blocker': False,
  'result_columns': ['JobGroupID',
                     'PersonnelGroup',
                     'EmployeeCount',
                     'TotalWorkHours',
                     'TotalRegularOvertimeHours',
                     'TotalLeaveHours']},
 {'id': 'FINAL-U41',
  'question': 'For @EmployeeID, list daily worktime and attendance events for the payroll month containing '
              '@AsOfDate.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrcio.tblCardLog',
                      'gnd_hrcio.tblWorkTimeAllDays',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 4,
  'relationship_notes': 'Daily worktime joins Employee and YearMonth; attendance CardLog events join '
                        'logically by employee and calendar date.',
  'semantic_note': 'Source explicitly requires the current month. Replace server clock with @AsOfDate and '
                   'freeze the validation date; select an existing employee privately rather than invalid '
                   'sentinel 0. Daily values repeat per attendance event intentionally and are not '
                   'aggregated.',
  'fidelity_rationale': 'Allow an employee to view limited daily worktime and attendance detail for the '
                        'current month only. Normalization changes are recorded in the private case-specific '
                        'fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['EmployeeID',
                     'EmployeeCode',
                     'Date',
                     'WorkTime',
                     'NotWorkTime',
                     'TotalAdditionalTime',
                     'LeaveHours',
                     'HourMission',
                     'AttendanceEventID',
                     'ClockTime',
                     'AlternateClockTime',
                     'EnterExitTypeID']},
 {'id': 'FINAL-U42',
  'question': 'List approved forgotten-attendance records that are not reflected in daily worktime, '
              'including employee, date, and recorded times.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egwfm.tblWork',
                      'gnd_hrcio.tblCardLog',
                      'gnd_hrcio.tblForgottenEnterExit',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 4,
  'relationship_notes': 'Latest Work.FormID -> ForgottenEnterExit.ID at FormTypeID=1389122; '
                        'ForgottenEnterExit.EmployeeID -> Employee.ID; anti-join '
                        'CardLog.FormTypeID=1389122/FormID -> request.ID.',
  'semantic_note': 'Authoritative benchmark rule: latest Work for FormTypeID=1389122/FormID by CreateDate '
                   'DESC, ID DESC must have RunStatusTypeID=3. Not reflected means NOT EXISTS any CardLog '
                   'with that source FormTypeID/FormID, independent of IsDisable. One row per qualifying '
                   'forgotten-attendance request.',
  'fidelity_rationale': 'Explicit latest human-approved meaning supersedes the prior active interpretation; '
                        'private final_authoritative_approval.txt records the decision.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['ForgottenAttendanceID',
                     'EmployeeID',
                     'EmployeeCode',
                     'DayDate',
                     'ClockTime',
                     'PermissionTypeID']},
 {'id': 'FINAL-U43',
  'question': 'For each employee and payroll month, count distinct dates with a valid non-off shift and at '
              'least one active attendance event, counting a date with multiple qualifying shifts only once.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth',
                      'gnd_hrcio.tblCardLog',
                      'gnd_hrcio.tblEmployeeShift',
                      'gnd_hrcio.tblEmployeeShiftModifications',
                      'gnd_hrcio.tblShift',
                      'gnd_hrcio.tblShiftDetail',
                      'gnd_hrcio.tblShiftTemplate',
                      'gnd_hrcio.tblWorkShiftType',
                      'gnd_hrprs.tblEmployee'],
  'expected_table_count': 9,
  'relationship_notes': 'Shift-report view supplies roster/modification validity. CardLog is correlated by '
                        'EmployeeID + DayDate without a physical composite FK. YearMonth is a logical '
                        'date-range join; EmployeeID -> Employee.ID.',
  'semantic_note': 'Human-authorized qualification: vwEmployeeShiftCompleteReport row with IsOff=0 plus same '
                   'EmployeeID/date CardLog.IsDisable=0. COUNT(DISTINCT Date), not roster-only eligibility. '
                   'Monthly YearMonth date ranges are verified nonoverlapping. The view dependency closure '
                   'is retained.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'logical_or_temporal', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human-authorized qualification: vwEmployeeShiftCompleteReport row with IsOff=0 '
                             'plus same EmployeeID/date CardLog.IsDisable=0. COUNT(DISTINCT Date), not '
                             'roster-only eligibility. Monthly YearMonth date ranges are verified '
                             'nonoverlapping. The view dependency closure is retained.',
  'semantic_implementation_blocker': False,
  'result_columns': ['EmployeeID', 'EmployeeCode', 'YearMonthID', 'ShiftWorkDayCount']},
 {'id': 'FINAL-U44',
  'question': 'For each employee and payroll month, show unrounded regular overtime and holiday overtime '
              'hours.',
  'domain': 'personnel/attendance',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblYearMonth', 'gnd_hrprs.tblEmployee', 'gnd_hrpyr.tblWorkTime'],
  'expected_table_count': 3,
  'relationship_notes': 'WorkTime.EmployeeID and YearMonthID join Employee and YearMonth.',
  'semantic_note': 'Human decision confirms unrounded system overtime fields SystemSaatEzafeKarcdur and '
                   'SystemSaatEzafekarTatilicdur, stored in minutes. Divide by 60.0 without rounding; '
                   'payroll overtime fields are not substitutes.',
  'fidelity_rationale': 'The reviewed scope and the evidence-backed interpretation are preserved; see '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Human decision confirms unrounded system overtime fields '
                             'SystemSaatEzafeKarcdur and SystemSaatEzafekarTatilicdur, stored in minutes. '
                             'Divide by 60.0 without rounding; payroll overtime fields are not substitutes.',
  'semantic_implementation_blocker': False,
  'result_columns': ['EmployeeID',
                     'EmployeeCode',
                     'YearMonthID',
                     'Year',
                     'MonthID',
                     'UnroundedRegularOvertimeHours',
                     'UnroundedHolidayOvertimeHours']},
 {'id': 'FINAL-U45',
  'domain': 'production',
  'question': "For yarn group @InterweavingID selected from the ERP's yarn-group list and packing dates from "
              "@FromDate through @ThroughDate, list serial-numbered packs included by the ERP's 'packing "
              "without warehouse receipt' report, showing packing identifier, packing date, and serial.",
  'difficulty': 'Hard',
  'secondary_domains': ['inventory'],
  'expected_tables': ['gnd_ficac.tblProjectStandardProduction',
                      'gnd_ficac.tblProjectStandardProductionScannedBarcode',
                      'gnd_scprd.tblPacking'],
  'relationship_notes': 'Packing.Serial = ProjectStandardProductionScannedBarcode.Serial is a logical join '
                        'explicitly used by the ERP report, not an FK. '
                        'ProjectStandardProductionScannedBarcode.ProjectStandardProductionID -> '
                        'ProjectStandardProduction.ID is an FK. InterWeavingID filtering uses Packing '
                        'directly.',
  'semantic_note': 'Preserves the named report OnlyWithoutEnter filter: the maximum ISNULL(Code,0) across '
                   'production records linked by serial is not 99; no linked record also qualifies. This is '
                   'the report criterion, not an independent proof that no warehouse receipt exists. '
                   'Non-null serial and inclusive packing dates are preserved. One row per pack; unused '
                   'display-name and stock-status joins are omitted. No direct inventory anti-join or '
                   'invented approval rule is added. Parameter contract: @InterweavingID must identify an '
                   'entry in gnd_pjprj.evInterweaving, matching an ERP-selectable yarn group. Some physical '
                   'packing references are absent from that entity view; accepting arbitrary IDs would not '
                   'preserve the report. The production entity-view identity join was separately checked and '
                   'removes no current production records. These display/audit-view joins are not physical '
                   'Gold dependencies; the valid input domain and current-data invariant are explicit.',
  'fidelity_rationale': 'The source explicitly asks for a yarn-group filter on the existing named report. '
                        'Its ERP report expression binds a specific procedure, whose date, serial and '
                        'OnlyWithoutEnter predicates are retained in read-only SELECT form.',
  'relationship_types': ['explicit_fk', 'logical_join'],
  'expected_table_count': 3,
  'feasibility_status': 'FEASIBLE',
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'replaced_original_case': True,
  'replacement_human_review_status': 'FINAL_APPROVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['PackingID', 'PackingDate', 'Serial']},
 {'id': 'FINAL-U46',
  'question': 'For purchase-invoice lines with a missing or zero unit price, show the warehouse amount, '
              'quantity, and warehouse amount per unit.',
  'domain': 'purchasing',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_scpch.tblPurchaseInvoiceGoodAndService',
                      'gnd_scpch.tblPurchaseInvoiceGoodDetailEnter',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 3,
  'relationship_notes': 'PurchaseInvoiceGoodDetailEnter.PurchaseInvoiceGoodAndServiceID -> invoice.ID and '
                        'GoodID -> Good.ID are explicit FKs. Only the projected/calculated amount changes to '
                        'InvValue.',
  'semantic_note': 'The original warehouse-amount phrase exactly matches the explicit InvValue caption. '
                   'AccValue has the distinct Amount caption. Divide InvValue by Qty, returning NULL for '
                   'zero or NULL quantity; preserve stored NULL amounts. Missing-or-zero price is explicit '
                   'in the revised wording. This is a read-only projection, not a price update.',
  'fidelity_rationale': 'The original warehouse-amount phrase exactly matches the explicit InvValue caption. '
                        'AccValue has the distinct Amount caption. Divide InvValue by Qty, returning NULL '
                        'for zero or NULL quantity; preserve stored NULL amounts. Missing-or-zero price is '
                        'explicit in the revised wording. This is a read-only projection, not a price '
                        'update.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'semantic_implementation_blocker': False,
  'result_columns': ['PurchaseInvoiceID',
                     'PurchaseInvoiceCode',
                     'InvoiceLineID',
                     'GoodID',
                     'GoodCode',
                     'GoodName',
                     'Qty',
                     'WarehouseAmount',
                     'UnitPrice',
                     'WarehouseAmountPerUnit']},
 {'id': 'FINAL-U47',
  'question': 'List purchase inquiries with the employee who requested the purchase.',
  'domain': 'purchasing',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_hrprs.tblEmployee',
                      'gnd_scpch.tblPurchaseInquiry',
                      'gnd_scpch.tblPurchaseOrder',
                      'gnd_scpch.tblPurchaseOrderDetail',
                      'gnd_scpch.tblPurchaseRequest',
                      'gnd_scpch.tblPurchaseRequestDetail'],
  'expected_table_count': 6,
  'relationship_notes': 'PurchaseInquiry joins PurchaseOrder, PurchaseOrderDetail, PurchaseRequestDetail, '
                        'PurchaseRequest, and the requesting Employee through explicit relationships.',
  'semantic_note': 'The query uses directly stored fields and explicit Gold joins without an additional '
                   'business rule.',
  'fidelity_rationale': 'Add the original purchase requester to purchase-inquiry output. Normalization '
                        'changes are recorded in the private case-specific fidelity audit.',
  'relationship_types': ['physical_fk_or_key_join', 'aggregation'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'semantic_implementation_blocker': False,
  'result_columns': ['PurchaseInquiryID',
                     'PurchaseInquiryCode',
                     'DoneDate',
                     'PurchaseRequestID',
                     'RequestEmployeeID',
                     'EmployeeCode']},
 {'id': 'FINAL-U48',
  'question': 'List purchase inquiries with the person currently responsible for workflow approval.',
  'domain': 'purchasing',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbpm.tblProcessStep',
                      'gnd_egbse.tblContact',
                      'gnd_egwfm.tblWork',
                      'gnd_scpch.tblPurchaseInquiry'],
  'expected_table_count': 4,
  'relationship_notes': 'Work is keyed to the inquiry by FormTypeID=1927645 and FormID. Existing SQL ranks '
                        'all Work rows before filtering completion; it does NOT select the latest '
                        'non-completed row. Lifecycle/order/person semantics remain on hold.',
  'semantic_note': 'Latest inquiry task uses greatest Work.ID, explicitly used by '
                   'fnPurchaseInquiry_LastStepName. Only statuses 0/1 are active, exactly as vwRunningWorks. '
                   'Select latest before testing active status, so no fallback to an older active task. '
                   'CurrentUserID -> Contact.ID is the declared workflow assignee FK; NULL when the latest '
                   'task is inactive or unassigned.',
  'fidelity_rationale': 'Authoritative human business decision dated 2026-09-27 supersedes prior '
                        'normalization uncertainty; physical implementation status is recorded in '
                        'semantic_note.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'resolved_human_decision': 'Latest inquiry task uses greatest Work.ID, explicitly used by '
                             'fnPurchaseInquiry_LastStepName. Only statuses 0/1 are active, exactly as '
                             'vwRunningWorks. Select latest before testing active status, so no fallback to '
                             'an older active task. CurrentUserID -> Contact.ID is the declared workflow '
                             'assignee FK; NULL when the latest task is inactive or unassigned.',
  'semantic_implementation_blocker': False,
  'result_columns': ['PurchaseInquiryID',
                     'PurchaseInquiryCode',
                     'DoneDate',
                     'CurrentUserID',
                     'CurrentApprover',
                     'CurrentProcessStepID',
                     'CurrentApprovalStep',
                     'RunStatusTypeID']},
 {'id': 'FINAL-U49',
  'question': 'Show the open purchase pro forma report, including each pro forma item line and its remaining '
              'quantity after quality control of delivered items.',
  'domain': 'quality',
  'secondary_domains': [],
  'difficulty': 'Hard',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_egbse.tblContact',
                      'gnd_egbse.tblConvertDateTypeL',
                      'gnd_egbse.tblPerson',
                      'gnd_egbse.tblPersonStatus',
                      'gnd_egbse.tblPosition',
                      'gnd_egbse.tblPrefix',
                      'gnd_egbse.tblUser',
                      'gnd_scpch.tblNotifyEnter',
                      'gnd_scpch.tblPrePurchaseInvoice',
                      'gnd_scpch.tblPrePurchaseInvoiceDetail',
                      'gnd_scpch.tblQualityControl',
                      'gnd_scpch.tblQualityControlDetail',
                      'gnd_scpch.tblSupplier',
                      'gnd_spgod.tblGood',
                      'gnu_egbse.xblContact',
                      'gnu_egbse.xblPerson',
                      'gnu_egbse.xblPrefix',
                      'gnu_scpch.xblPrePurchaseInvoice',
                      'gnu_scpch.xblSupplier'],
  'expected_table_count': 19,
  'relationship_notes': 'NotifyEnter FormTypeID=17889/FormID -> PrePurchaseInvoice.ID; QualityControl '
                        'FormTypeID=1666058/FormID -> NotifyEnter.ID; QualityControlDetail.QualityControlID '
                        '-> QualityControl.ID; PrePurchaseInvoiceDetail.PrePurchaseInvoiceID -> invoice and '
                        'GoodID -> Good.ID. Report aggregates by invoice/item then joins detail lines.',
  'semantic_note': 'SELECT/CTE transcription of the existing open purchase pro forma report. Its original '
                   'notification/QC eligibility, join multiplicity, per-item remaining-quantity calculation, '
                   'positive-balance filter and detail-line grain are retained. This reports ERP-defined '
                   'remaining quantities; it does not silently repair or reinterpret the report arithmetic. '
                   'Entity-view display dependencies are included.',
  'fidelity_rationale': 'SELECT/CTE transcription of the existing open purchase pro forma report. Its '
                        'original notification/QC eligibility, join multiplicity, per-item '
                        'remaining-quantity calculation, positive-balance filter and detail-line grain are '
                        'retained. This reports ERP-defined remaining quantities; it does not silently '
                        'repair or reinterpret the report arithmetic. Entity-view display dependencies are '
                        'included.',
  'relationship_types': ['physical_fk_or_key_join', 'polymorphic', 'aggregation', 'cte_or_window'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'replacement_completed': True,
  'result_columns': ['ID', 'PrePurchaseInvoice', 'ItemsNotReceived', 'RemainedQty'],
  'semantic_implementation_blocker': False,
  'replacement_human_review_status': 'FINAL_APPROVED'},
 {'id': 'FINAL-U50',
  'question': 'List every goods and service line on sales invoices with invoice number and date, customer, '
              'line type, item or service, quantity, unit price, discount, VAT, and the ERP-calculated line '
              'value before VAT.',
  'domain': 'sales',
  'secondary_domains': [],
  'difficulty': 'Medium',
  'feasibility_status': 'FEASIBLE',
  'expected_tables': ['gnd_crsls.tblCustomer',
                      'gnd_crsls.tblSalesAndServicesInvoice',
                      'gnd_crsls.tblSalesAndServicesInvoiceSalesDetail',
                      'gnd_crsls.tblSalesAndServicesInvoiceServDetail',
                      'gnd_crsls.tblSellableService',
                      'gnd_egbse.tblContact',
                      'gnd_fiaci.tblVatPercentage',
                      'gnd_spgod.tblGood'],
  'expected_table_count': 8,
  'relationship_notes': 'Both invoice detail tables reference SalesAndServicesInvoice.ID by FK. Goods '
                        'detail.GoodID -> Good.ID; service detail.SellableServiceID -> SellableService.ID. '
                        'Invoice.CredbCustomerID -> Customer.ID -> Contact.ID through shared identity. '
                        'Computed pricing/tax dependencies are separately audited.',
  'semantic_note': 'UNION ALL preserves goods and service lines. LineType plus InvoiceLineID identifies the '
                   'line family. Goods use existing RowTotalPayable (Qty times ActualUnitPrice less '
                   'discount); services use existing SalesValue (Qty times UnitPrice less discount). Both '
                   'exclude VAT, which is a separate output; neither value is recomputed with a new pricing '
                   'rule. Displayed goods UnitPrice can differ from ActualUnitPrice used by the ERP '
                   'calculation.',
  'fidelity_rationale': 'UNION ALL preserves goods and service lines. LineType plus InvoiceLineID identifies '
                        'the line family. Goods use existing RowTotalPayable (Qty times ActualUnitPrice less '
                        'discount); services use existing SalesValue (Qty times UnitPrice less discount). '
                        'Both exclude VAT, which is a separate output; neither value is recomputed with a '
                        'new pricing rule. Displayed goods UnitPrice can differ from ActualUnitPrice used by '
                        'the ERP calculation.',
  'relationship_types': ['physical_fk_or_key_join'],
  'semantic_audit_status': 'FINAL_APPROVED_BOUNDED_VALIDATED',
  'human_approved': True,
  'expected_tables_status': 'FINAL_APPROVED_CURRENT_SQL_DEPENDENCIES',
  'human_decision_classification': 'HUMAN_DECISION_RESOLVED',
  'replacement_required': False,
  'semantic_implementation_blocker': False,
  'result_columns': ['SalesInvoiceID',
                     'InvoiceNumber',
                     'InvoiceDate',
                     'CredbCustomerID',
                     'CustomerCode',
                     'CustomerName',
                     'LineType',
                     'InvoiceLineID',
                     'ItemID',
                     'ItemName',
                     'Qty',
                     'UnitPrice',
                     'DiscountValue',
                     'Vat',
                     'ERPLineValueBeforeVAT']}]
