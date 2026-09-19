"""Validated reference definitions for the frozen real-world ERP benchmark.
Named SQL parameters are bound externally; validation fetches at most 10 rows.
No sampled result rows or personal parameter identifiers are stored.
"""

validation_summary = {'case_count': 13,
 'attempted': 13,
 'executable_queries': 13,
 'non_empty_queries': 13,
 'empty_queries': 0,
 'failed_queries': [],
 'result_column_mismatches': [],
 'logical_join_cases': ['REAL-C01', 'REAL-C02', 'REAL-C04', 'REAL-C14'],
 'exact_table_sets_match': True,
 'sample_rows_persisted': False,
 'retrieval_executed': False,
 'model_generation_executed': False}

tests = [{'id': 'REAL-C01',
  'question': 'Show account activity for a specified financial period, account, and project, '
              'including only entries for that project.',
  'domain': 'accounting',
  'difficulty': 'medium',
  'expected_tables': ['gnd_fiaci.tblTrans',
                      'gnd_fiaci.tblTransDetail',
                      'gnd_fiaci.tblTransDetailDetail'],
  'expected_table_count': 3,
  'relationship_notes': ['FK: gnd_fiaci.tblTransDetail.TransID -> gnd_fiaci.tblTrans.ID.',
                         'FK: gnd_fiaci.tblTransDetailDetail.TransDetailIG -> '
                         'gnd_fiaci.tblTransDetail.IG.',
                         'Project is a polymorphic accounting dimension: '
                         'tblTransDetailDetail.FormTypeID = 12261 identifies Project, and FormID '
                         'identifies the project; there is no direct FK from FormID to the project '
                         'table.'],
  'feasibility_status': 'FEASIBLE',
  'semantic_evaluation_note': 'Match project by the typed dimension pair and avoid duplicating an '
                              'accounting line when testing for the project dimension. Account, '
                              'period, and project labels are not requested.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT t.ID AS TransactionID,t.Code AS TransactionCode,t.DocDate,\n'
                   '       t.PeriodSpecID,d.IG AS AccountingLineID,d.AccountID,d.Description,\n'
                   '       d.Debit,d.Credit\n'
                   'FROM [gnd_fiaci].[tblTrans] AS t\n'
                   'INNER JOIN [gnd_fiaci].[tblTransDetail] AS d ON d.TransID=t.ID\n'
                   'WHERE t.PeriodSpecID=@FinancialPeriodID AND d.AccountID=@AccountID\n'
                   '  AND EXISTS (\n'
                   '      SELECT 1 FROM [gnd_fiaci].[tblTransDetailDetail] AS x\n'
                   '      WHERE x.TransDetailIG=d.IG AND x.FormTypeID=12261\n'
                   '        AND x.FormID=@ProjectID\n'
                   '  );',
  'parameters': {'FinancialPeriodID': 'int', 'AccountID': 'int', 'ProjectID': 'int'},
  'reference_interpretation_notes': ['Identifiers are supplied parameters. Project form type 12261 '
                                     'is verified schema configuration. EXISTS preserves one '
                                     'result per accounting line.'],
  'logical_joins': ['Typed project dimension: FormTypeID=12261 and FormID=@ProjectID; no direct '
                    'project-table FK.'],
  'execution_valid': True,
  'result_columns': ['TransactionID',
                     'TransactionCode',
                     'DocDate',
                     'PeriodSpecID',
                     'AccountingLineID',
                     'AccountID',
                     'Description',
                     'Debit',
                     'Credit'],
  'validation': {'id': 'REAL-C01',
                 'reference_sql_sha256': '60f7933575ecee150865c955185529baa4a5f44d708abf89eee9bcaaabc25c16',
                 'expected_tables_actually_referenced': ['gnd_fiaci.tblTrans',
                                                         'gnd_fiaci.tblTransDetail',
                                                         'gnd_fiaci.tblTransDetailDetail'],
                 'logical_joins': ['Typed project dimension: FormTypeID=12261 and '
                                   'FormID=@ProjectID; no direct project-table FK.'],
                 'interpretation_notes': ['Identifiers are supplied parameters. Project form type '
                                          '12261 is verified schema configuration. EXISTS '
                                          'preserves one result per accounting line.'],
                 'parameter_types': {'FinancialPeriodID': 'int',
                                     'AccountID': 'int',
                                     'ProjectID': 'int'},
                 'validation_parameter_selection': 'SELECT TOP (1) t.PeriodSpecID AS '
                                                   'FinancialPeriodID,d.AccountID,x.FormID AS '
                                                   'ProjectID\n'
                                                   'FROM gnd_fiaci.tblTransDetailDetail x JOIN '
                                                   'gnd_fiaci.tblTransDetail d ON '
                                                   'd.IG=x.TransDetailIG JOIN gnd_fiaci.tblTrans t '
                                                   'ON t.ID=d.TransID\n'
                                                   'WHERE x.FormTypeID=12261 AND t.PeriodSpecID IS '
                                                   'NOT NULL AND d.AccountID IS NOT NULL ORDER BY '
                                                   'x.IG',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['TransactionID',
                                    'TransactionCode',
                                    'DocDate',
                                    'PeriodSpecID',
                                    'AccountingLineID',
                                    'AccountID',
                                    'Description',
                                    'Debit',
                                    'Credit'],
                 'empty': False,
                 'row_count': 2,
                 'row_count_exact': True,
                 'rows_fetched': 2,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 2,
                 'sample_null_counts': {'TransactionID': 0,
                                        'TransactionCode': 0,
                                        'DocDate': 0,
                                        'PeriodSpecID': 0,
                                        'AccountingLineID': 0,
                                        'AccountID': 0,
                                        'Description': 0,
                                        'Debit': 0,
                                        'Credit': 0},
                 'sample_blank_string_counts': {'TransactionID': 0,
                                                'TransactionCode': 0,
                                                'DocDate': 0,
                                                'PeriodSpecID': 0,
                                                'AccountingLineID': 0,
                                                'AccountID': 0,
                                                'Description': 1,
                                                'Debit': 0,
                                                'Credit': 0},
                 'elapsed_seconds': 0.172,
                 'validated_at_utc': '2026-09-19T14:03:53.672192+00:00'}},
 {'id': 'REAL-C02',
  'question': 'For a selected service-purchase invoice, compare its tax amount with the tax amount '
              'in its associated accounting entry.',
  'domain': 'purchasing',
  'difficulty': 'hard',
  'expected_tables': ['gnd_scpch.tblServiceInvoice',
                      'gnd_fiaci.tblTrans',
                      'gnd_fiaci.tblTransDetail'],
  'expected_table_count': 3,
  'relationship_notes': ['FK: gnd_fiaci.tblTransDetail.TransID -> gnd_fiaci.tblTrans.ID.',
                         'Logical source-document join: tblTrans.FormID = tblServiceInvoice.ID '
                         'with tblTrans.FormTypeID = 1208179; there is no direct '
                         'invoice-to-transaction FK.'],
  'feasibility_status': 'FEASIBLE',
  'semantic_evaluation_note': 'The SPN posting template maps ServiceInvoice.TotalVat to '
                              'VAT-and-duties account ID 348. Compare against that posted tax '
                              "line, not against the journal's total debit or credit.",
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT s.ID AS ServiceInvoiceID,s.TotalVat AS InvoiceVAT,\n'
                   '       t.ID AS AccountingTransactionID,v.PostedVAT,v.VATPostingLineCount,\n'
                   '       s.TotalVat-v.PostedVAT AS VATDifference\n'
                   'FROM [gnd_scpch].[tblServiceInvoice] AS s\n'
                   'LEFT JOIN [gnd_fiaci].[tblTrans] AS t\n'
                   '  ON t.FormTypeID=1208179 AND t.FormID=s.ID\n'
                   'OUTER APPLY (\n'
                   '    SELECT SUM(d.Debit-d.Credit) AS PostedVAT,COUNT_BIG(*) AS '
                   'VATPostingLineCount\n'
                   '    FROM [gnd_fiaci].[tblTransDetail] AS d\n'
                   '    WHERE d.TransID=t.ID AND d.AccountID=348\n'
                   ') AS v\n'
                   'WHERE s.ID=@ServiceInvoiceID;',
  'parameters': {'ServiceInvoiceID': 'int'},
  'reference_interpretation_notes': ['VAT account 348 and source form type 1208179 are verified '
                                     'configuration, not sampled row IDs. Posted VAT is net debit '
                                     'minus credit on VAT lines only, reported per associated '
                                     'journal. Missing VAT postings remain NULL, not zero.'],
  'logical_joins': ['tblTrans.FormID=tblServiceInvoice.ID when tblTrans.FormTypeID=1208179.'],
  'execution_valid': True,
  'result_columns': ['ServiceInvoiceID',
                     'InvoiceVAT',
                     'AccountingTransactionID',
                     'PostedVAT',
                     'VATPostingLineCount',
                     'VATDifference'],
  'validation': {'id': 'REAL-C02',
                 'reference_sql_sha256': '41a5683c8dc1509929f3a03f49285a08b5ceae0570326bb53b9110f2ca3c4ee5',
                 'expected_tables_actually_referenced': ['gnd_fiaci.tblTrans',
                                                         'gnd_fiaci.tblTransDetail',
                                                         'gnd_scpch.tblServiceInvoice'],
                 'logical_joins': ['tblTrans.FormID=tblServiceInvoice.ID when '
                                   'tblTrans.FormTypeID=1208179.'],
                 'interpretation_notes': ['VAT account 348 and source form type 1208179 are '
                                          'verified configuration, not sampled row IDs. Posted VAT '
                                          'is net debit minus credit on VAT lines only, reported '
                                          'per associated journal. Missing VAT postings remain '
                                          'NULL, not zero.'],
                 'parameter_types': {'ServiceInvoiceID': 'int'},
                 'validation_parameter_selection': 'SELECT TOP (1) s.ID AS ServiceInvoiceID FROM '
                                                   'gnd_scpch.tblServiceInvoice s\n'
                                                   'WHERE s.TotalVat>0 AND EXISTS(SELECT 1 FROM '
                                                   'gnd_fiaci.tblTrans t WHERE '
                                                   't.FormTypeID=1208179 AND t.FormID=s.ID) ORDER '
                                                   'BY s.ID',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['ServiceInvoiceID',
                                    'InvoiceVAT',
                                    'AccountingTransactionID',
                                    'PostedVAT',
                                    'VATPostingLineCount',
                                    'VATDifference'],
                 'empty': False,
                 'row_count': 1,
                 'row_count_exact': True,
                 'rows_fetched': 1,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 1,
                 'sample_null_counts': {'ServiceInvoiceID': 0,
                                        'InvoiceVAT': 0,
                                        'AccountingTransactionID': 0,
                                        'PostedVAT': 0,
                                        'VATPostingLineCount': 0,
                                        'VATDifference': 0},
                 'sample_blank_string_counts': {'ServiceInvoiceID': 0,
                                                'InvoiceVAT': 0,
                                                'AccountingTransactionID': 0,
                                                'PostedVAT': 0,
                                                'VATPostingLineCount': 0,
                                                'VATDifference': 0},
                 'elapsed_seconds': 0.078,
                 'validated_at_utc': '2026-09-19T14:03:53.758238+00:00'}},
 {'id': 'REAL-C03',
  'question': 'Show purchase-request lines with their recorded request reason and intended use.',
  'domain': 'purchasing',
  'difficulty': 'easy',
  'expected_tables': ['gnd_scpch.tblPurchaseRequestDetail'],
  'expected_table_count': 1,
  'relationship_notes': [],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'RequestReason and ConsumptionPurpose are stored on each '
                              'purchase-request line. Do not claim universal line-level provenance '
                              'from an originating warehouse requisition.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT d.PurchaseRequestID,d.IG AS PurchaseRequestLineID,d.Sequence,\n'
                   '       d.RequestReason,d.ConsumptionPurpose\n'
                   'FROM [gnd_scpch].[tblPurchaseRequestDetail] AS d;',
  'parameters': {},
  'reference_interpretation_notes': [],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['PurchaseRequestID',
                     'PurchaseRequestLineID',
                     'Sequence',
                     'RequestReason',
                     'ConsumptionPurpose'],
  'validation': {'id': 'REAL-C03',
                 'reference_sql_sha256': 'fb2e51715137981b0b0c477de684dc70455a1eae59f0b09264c8ebdc2f757085',
                 'expected_tables_actually_referenced': ['gnd_scpch.tblPurchaseRequestDetail'],
                 'logical_joins': [],
                 'interpretation_notes': [],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['PurchaseRequestID',
                                    'PurchaseRequestLineID',
                                    'Sequence',
                                    'RequestReason',
                                    'ConsumptionPurpose'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'PurchaseRequestID': 0,
                                        'PurchaseRequestLineID': 0,
                                        'Sequence': 0,
                                        'RequestReason': 0,
                                        'ConsumptionPurpose': 0},
                 'sample_blank_string_counts': {'PurchaseRequestID': 0,
                                                'PurchaseRequestLineID': 0,
                                                'Sequence': 0,
                                                'RequestReason': 10,
                                                'ConsumptionPurpose': 10},
                 'elapsed_seconds': 0.062,
                 'validated_at_utc': '2026-09-19T14:03:53.821183+00:00'}},
 {'id': 'REAL-C04',
  'question': 'Show imports by pro forma invoice, commercial invoice, domestic waybill, and goods '
              "receipt, with each stage's item-line quantity in the item's recorded unit, the "
              'order-registration number, and the customs-declaration number where applicable. '
              'Keep quantities separate between stages.',
  'domain': 'imports',
  'difficulty': 'hard',
  'expected_tables': ['gnd_scimp.tblProformaInvoice',
                      'gnd_scimp.tblProformaInvoiceDetail',
                      'gnd_scimp.tblCurrencyPurchaseInvoice',
                      'gnd_scimp.tblCurrencyPurchaseInvoiceDetail',
                      'gnd_scimp.tblOrderRegistration',
                      'gnd_scimp.tblCottage',
                      'gnd_sclog.tblInternalBillOfLading',
                      'gnd_sclog.tblInternalBillOfLadingGoodDetail',
                      'gnd_scimp.tblForeignReceiveGoods',
                      'gnd_scimp.tblForeignReceiveGoodsDetail',
                      'gnd_spgod.tblGood',
                      'gnd_spgod.tblGoodUnitTypeL'],
  'expected_table_count': 12,
  'relationship_notes': ['FK: tblProformaInvoiceDetail.ProformaInvoiceID -> tblProformaInvoice.ID.',
                         'FK: tblCurrencyPurchaseInvoice.ProformaInvoiceID -> '
                         'tblProformaInvoice.ID.',
                         'FK: tblCurrencyPurchaseInvoiceDetail.CurrencyPurchaseInvoiceID -> '
                         'tblCurrencyPurchaseInvoice.ID.',
                         'FK: tblOrderRegistration.ID -> tblProformaInvoice.ID.',
                         'FK: tblInternalBillOfLading.CottageID -> tblCottage.ID.',
                         'FK: tblInternalBillOfLadingGoodDetail.BillOfLadingID -> '
                         'tblInternalBillOfLading.ID.',
                         'FK: tblForeignReceiveGoods.ID -> tblInternalBillOfLading.ID.',
                         'FK: tblForeignReceiveGoodsDetail.ForeignReceiveGoodsID -> '
                         'tblForeignReceiveGoods.ID.',
                         'Each stage-detail GoodID references gnd_spgod.tblGood.ID; '
                         'tblGood.UnitTypeID -> gnd_spgod.tblGoodUnitTypeL.ID.',
                         'Invoice-to-customs linkage is the verified shared-ID FK chain Cottage -> '
                         'WareHouseBill -> BillOfLading -> PackingList -> CurrencyPurchaseInvoice. '
                         'The intermediate inheritance tables are relationship evidence but are '
                         'not required output tables.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'Return separate stage/item-line records. Do not aggregate '
                              'quantities across stages or flatten sibling detail sets into a '
                              'cross-product. The consolidated ForeignPurchase structure is empty '
                              'in this SPN snapshot.',
  'top10_full_coverage_possible': False,
  'top10_recall_ceiling': 0.8333333333333334,
  'reference_sql': 'WITH StageLines AS (\n'
                   "    SELECT N'Pro forma invoice' AS DocumentStage,p.ID AS ProformaID,\n"
                   '           CAST(NULL AS int) AS CommercialInvoiceID,CAST(NULL AS int) AS '
                   'WaybillID,\n'
                   '           CAST(NULL AS int) AS ReceiptID,p.ID AS DocumentID,\n'
                   '           CONVERT(nvarchar(100),d.IG) AS DocumentLineID,d.Sequence,\n'
                   '           d.GoodID,d.Qty,\n'
                   '           CONVERT(nvarchar(max),o.RegistrationNumber) AS '
                   'OrderRegistrationNumber,\n'
                   '           CAST(NULL AS nvarchar(max)) AS CustomsDeclarationNumber\n'
                   '    FROM [gnd_scimp].[tblProformaInvoice] AS p\n'
                   '    INNER JOIN [gnd_scimp].[tblProformaInvoiceDetail] AS d ON '
                   'd.ProformaInvoiceID=p.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n'
                   '    UNION ALL\n'
                   "    SELECT N'Commercial invoice',p.ID,c.ID,NULL,NULL,c.ID,\n"
                   '           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n'
                   '           CONVERT(nvarchar(max),o.RegistrationNumber),\n'
                   '           CONVERT(nvarchar(max),k.CottageNumber)\n'
                   '    FROM [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c\n'
                   '    INNER JOIN [gnd_scimp].[tblCurrencyPurchaseInvoiceDetail] AS d ON '
                   'd.CurrencyPurchaseInvoiceID=c.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON '
                   'p.ID=c.ProformaInvoiceID\n'
                   '    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=c.ID\n'
                   '    UNION ALL\n'
                   "    SELECT N'Domestic waybill',p.ID,c.ID,w.ID,NULL,w.ID,\n"
                   '           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n'
                   '           CONVERT(nvarchar(max),o.RegistrationNumber),\n'
                   '           CONVERT(nvarchar(max),k.CottageNumber)\n'
                   '    FROM [gnd_sclog].[tblInternalBillOfLading] AS w\n'
                   '    INNER JOIN [gnd_sclog].[tblInternalBillOfLadingGoodDetail] AS d ON '
                   'd.BillOfLadingID=w.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=w.CottageID\n'
                   '    LEFT JOIN [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c ON c.ID=k.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON '
                   'p.ID=c.ProformaInvoiceID\n'
                   '    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n'
                   '    UNION ALL\n'
                   "    SELECT N'Goods receipt',p.ID,c.ID,w.ID,r.ID,r.ID,\n"
                   '           CONVERT(nvarchar(100),d.IG),d.Sequence,d.GoodID,d.Qty,\n'
                   '           CONVERT(nvarchar(max),o.RegistrationNumber),\n'
                   '           CONVERT(nvarchar(max),k.CottageNumber)\n'
                   '    FROM [gnd_scimp].[tblForeignReceiveGoods] AS r\n'
                   '    INNER JOIN [gnd_scimp].[tblForeignReceiveGoodsDetail] AS d ON '
                   'd.ForeignReceiveGoodsID=r.ID\n'
                   '    LEFT JOIN [gnd_sclog].[tblInternalBillOfLading] AS w ON w.ID=r.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblCottage] AS k ON k.ID=w.CottageID\n'
                   '    LEFT JOIN [gnd_scimp].[tblCurrencyPurchaseInvoice] AS c ON c.ID=k.ID\n'
                   '    LEFT JOIN [gnd_scimp].[tblProformaInvoice] AS p ON '
                   'p.ID=c.ProformaInvoiceID\n'
                   '    LEFT JOIN [gnd_scimp].[tblOrderRegistration] AS o ON o.ID=p.ID\n'
                   ')\n'
                   'SELECT '
                   's.DocumentStage,s.ProformaID,s.CommercialInvoiceID,s.WaybillID,s.ReceiptID,\n'
                   '       s.DocumentID,s.DocumentLineID,s.Sequence,s.GoodID,s.Qty AS '
                   'RecordedQuantity,\n'
                   '       g.UnitTypeID,u.Farsi AS UnitLabel,u.English AS UnitEnglish,\n'
                   '       s.OrderRegistrationNumber,s.CustomsDeclarationNumber\n'
                   'FROM StageLines AS s\n'
                   'LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=s.GoodID\n'
                   'LEFT JOIN [gnd_spgod].[tblGoodUnitTypeL] AS u ON u.ID=g.UnitTypeID;',
  'parameters': {},
  'reference_interpretation_notes': ['UNION ALL preserves one row per recorded stage detail. No '
                                     'sibling detail joins or cross-stage sums. Pro forma rows '
                                     'have no downstream customs number attached: one pro forma '
                                     'can have multiple subsequent invoices. Optional ancestry and '
                                     'lookup joins preserve lines with missing metadata. Units are '
                                     'current item-master units; no conversion or invented '
                                     'historical unit is applied.'],
  'logical_joins': ['tblCottage.ID=tblCurrencyPurchaseInvoice.ID via verified FK inheritance chain '
                    'Cottage -> WareHouseBill -> BillOfLading -> PackingList -> '
                    'CurrencyPurchaseInvoice; intermediate business tables are not queried.'],
  'execution_valid': True,
  'result_columns': ['DocumentStage',
                     'ProformaID',
                     'CommercialInvoiceID',
                     'WaybillID',
                     'ReceiptID',
                     'DocumentID',
                     'DocumentLineID',
                     'Sequence',
                     'GoodID',
                     'RecordedQuantity',
                     'UnitTypeID',
                     'UnitLabel',
                     'UnitEnglish',
                     'OrderRegistrationNumber',
                     'CustomsDeclarationNumber'],
  'validation': {'id': 'REAL-C04',
                 'reference_sql_sha256': 'f7313ba05336f43f442a2d787036681dccf456252adf8a631e3acb5ef9482e57',
                 'expected_tables_actually_referenced': ['gnd_scimp.tblCottage',
                                                         'gnd_scimp.tblCurrencyPurchaseInvoice',
                                                         'gnd_scimp.tblCurrencyPurchaseInvoiceDetail',
                                                         'gnd_scimp.tblForeignReceiveGoods',
                                                         'gnd_scimp.tblForeignReceiveGoodsDetail',
                                                         'gnd_scimp.tblOrderRegistration',
                                                         'gnd_scimp.tblProformaInvoice',
                                                         'gnd_scimp.tblProformaInvoiceDetail',
                                                         'gnd_sclog.tblInternalBillOfLading',
                                                         'gnd_sclog.tblInternalBillOfLadingGoodDetail',
                                                         'gnd_spgod.tblGood',
                                                         'gnd_spgod.tblGoodUnitTypeL'],
                 'logical_joins': ['tblCottage.ID=tblCurrencyPurchaseInvoice.ID via verified FK '
                                   'inheritance chain Cottage -> WareHouseBill -> BillOfLading -> '
                                   'PackingList -> CurrencyPurchaseInvoice; intermediate business '
                                   'tables are not queried.'],
                 'interpretation_notes': ['UNION ALL preserves one row per recorded stage detail. '
                                          'No sibling detail joins or cross-stage sums. Pro forma '
                                          'rows have no downstream customs number attached: one '
                                          'pro forma can have multiple subsequent invoices. '
                                          'Optional ancestry and lookup joins preserve lines with '
                                          'missing metadata. Units are current item-master units; '
                                          'no conversion or invented historical unit is applied.'],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['DocumentStage',
                                    'ProformaID',
                                    'CommercialInvoiceID',
                                    'WaybillID',
                                    'ReceiptID',
                                    'DocumentID',
                                    'DocumentLineID',
                                    'Sequence',
                                    'GoodID',
                                    'RecordedQuantity',
                                    'UnitTypeID',
                                    'UnitLabel',
                                    'UnitEnglish',
                                    'OrderRegistrationNumber',
                                    'CustomsDeclarationNumber'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'DocumentStage': 0,
                                        'ProformaID': 0,
                                        'CommercialInvoiceID': 10,
                                        'WaybillID': 10,
                                        'ReceiptID': 10,
                                        'DocumentID': 0,
                                        'DocumentLineID': 0,
                                        'Sequence': 0,
                                        'GoodID': 0,
                                        'RecordedQuantity': 0,
                                        'UnitTypeID': 0,
                                        'UnitLabel': 0,
                                        'UnitEnglish': 0,
                                        'OrderRegistrationNumber': 2,
                                        'CustomsDeclarationNumber': 10},
                 'sample_blank_string_counts': {'DocumentStage': 0,
                                                'ProformaID': 0,
                                                'CommercialInvoiceID': 0,
                                                'WaybillID': 0,
                                                'ReceiptID': 0,
                                                'DocumentID': 0,
                                                'DocumentLineID': 0,
                                                'Sequence': 0,
                                                'GoodID': 0,
                                                'RecordedQuantity': 0,
                                                'UnitTypeID': 0,
                                                'UnitLabel': 0,
                                                'UnitEnglish': 0,
                                                'OrderRegistrationNumber': 0,
                                                'CustomsDeclarationNumber': 0},
                 'elapsed_seconds': 0.156,
                 'validated_at_utc': '2026-09-19T14:03:53.991401+00:00'}},
 {'id': 'REAL-C05',
  'question': 'List warehouse issue lines and include the item code for each line.',
  'domain': 'inventory',
  'difficulty': 'medium',
  'expected_tables': ['gnd_scinv.tblExitDetail', 'gnd_spgod.tblGood'],
  'expected_table_count': 2,
  'relationship_notes': ['FK: gnd_scinv.tblExitDetail.CredbGoodID -> gnd_spgod.tblGood.ID.'],
  'feasibility_status': 'FEASIBLE',
  'semantic_evaluation_note': 'Use ExitDetail.IG as the reliable line identifier; Sequence may be '
                              'NULL.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT d.ExitID,d.IG AS WarehouseIssueLineID,d.Sequence,d.CredbGoodID AS '
                   'GoodID,\n'
                   '       g.GoodCode,d.Qty\n'
                   'FROM [gnd_scinv].[tblExitDetail] AS d\n'
                   'LEFT JOIN [gnd_spgod].[tblGood] AS g ON g.ID=d.CredbGoodID;',
  'parameters': {},
  'reference_interpretation_notes': [],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['ExitID', 'WarehouseIssueLineID', 'Sequence', 'GoodID', 'GoodCode', 'Qty'],
  'validation': {'id': 'REAL-C05',
                 'reference_sql_sha256': '3e38e6cc84187604dfc74c58cf809c63a758fccf7463e8aa8d824dfa6c172c31',
                 'expected_tables_actually_referenced': ['gnd_scinv.tblExitDetail',
                                                         'gnd_spgod.tblGood'],
                 'logical_joins': [],
                 'interpretation_notes': [],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['ExitID',
                                    'WarehouseIssueLineID',
                                    'Sequence',
                                    'GoodID',
                                    'GoodCode',
                                    'Qty'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'ExitID': 0,
                                        'WarehouseIssueLineID': 0,
                                        'Sequence': 10,
                                        'GoodID': 0,
                                        'GoodCode': 0,
                                        'Qty': 0},
                 'sample_blank_string_counts': {'ExitID': 0,
                                                'WarehouseIssueLineID': 0,
                                                'Sequence': 0,
                                                'GoodID': 0,
                                                'GoodCode': 0,
                                                'Qty': 0},
                 'elapsed_seconds': 0.141,
                 'validated_at_utc': '2026-09-19T14:03:54.130698+00:00'}},
 {'id': 'REAL-C06',
  'question': 'Show the dated shift-assignment history of a selected former employee, including '
              'earlier assignments.',
  'domain': 'hr_attendance',
  'difficulty': 'medium',
  'expected_tables': ['gnd_hrprs.tblEmployee', 'gnd_hrcio.tblEmployeeShift'],
  'expected_table_count': 2,
  'relationship_notes': ['FK: gnd_hrcio.tblEmployeeShift.EmployeeID -> gnd_hrprs.tblEmployee.ID.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'Former-employee status is Employee.IsLeaved. Assignment dates are '
                              'EmployeeShift.FromDate and EndDateStatus. Do not reinterpret the '
                              'question as shift-change requests or approvals.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT s.ID AS AssignmentID,s.ShiftID,s.FromDate,s.EndDateStatus\n'
                   'FROM [gnd_hrcio].[tblEmployeeShift] AS s\n'
                   'INNER JOIN [gnd_hrprs].[tblEmployee] AS e ON e.ID=s.EmployeeID\n'
                   'WHERE e.ID=@EmployeeID AND e.IsLeaved=1\n'
                   'ORDER BY s.FromDate,s.ID;',
  'parameters': {'EmployeeID': 'int'},
  'reference_interpretation_notes': ['Return every dated assignment for the supplied former '
                                     'employee, without filtering to current assignments. IsLeaved '
                                     'defines former status; NULL EndDateStatus remains unknown.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['AssignmentID', 'ShiftID', 'FromDate', 'EndDateStatus'],
  'validation': {'id': 'REAL-C06',
                 'reference_sql_sha256': 'e5df624ae1ed65ed23c382e92e2ac25bebe095d2bb3fa28a05ab93d6b2277bd2',
                 'expected_tables_actually_referenced': ['gnd_hrcio.tblEmployeeShift',
                                                         'gnd_hrprs.tblEmployee'],
                 'logical_joins': [],
                 'interpretation_notes': ['Return every dated assignment for the supplied former '
                                          'employee, without filtering to current assignments. '
                                          'IsLeaved defines former status; NULL EndDateStatus '
                                          'remains unknown.'],
                 'parameter_types': {'EmployeeID': 'int'},
                 'validation_parameter_selection': 'SELECT TOP (1) e.ID AS EmployeeID FROM '
                                                   'gnd_hrprs.tblEmployee e\n'
                                                   'WHERE e.IsLeaved=1 AND EXISTS(SELECT 1 FROM '
                                                   'gnd_hrcio.tblEmployeeShift s WHERE '
                                                   's.EmployeeID=e.ID) ORDER BY e.ID',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['AssignmentID', 'ShiftID', 'FromDate', 'EndDateStatus'],
                 'empty': False,
                 'row_count': 2,
                 'row_count_exact': True,
                 'rows_fetched': 2,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 2,
                 'sample_null_counts': {'AssignmentID': 0,
                                        'ShiftID': 0,
                                        'FromDate': 0,
                                        'EndDateStatus': 1},
                 'sample_blank_string_counts': {'AssignmentID': 0,
                                                'ShiftID': 0,
                                                'FromDate': 0,
                                                'EndDateStatus': 0},
                 'elapsed_seconds': 0.047,
                 'validated_at_utc': '2026-09-19T14:03:54.192997+00:00'}},
 {'id': 'REAL-C07',
  'question': 'Show all recorded monetary components of a selected employee settlement statement, '
              'including components with zero amounts.',
  'domain': 'payroll',
  'difficulty': 'medium',
  'expected_tables': ['gnd_hrpyr.tblBonusBill',
                      'gnd_hrpyr.tblBonusBillParameter',
                      'gnd_hrpyr.tblMonthlyParameterType'],
  'expected_table_count': 3,
  'relationship_notes': ['FK: gnd_hrpyr.tblBonusBillParameter.BonusBillID -> '
                         'gnd_hrpyr.tblBonusBill.ID.',
                         'FK: tblBonusBillParameter.MonthlyParameterTypeID -> '
                         'gnd_hrpyr.tblMonthlyParameterType.ID.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'Fixed components are columns on BonusBill; additional labeled '
                              'components are parameter rows. Preserve the distinction between '
                              'recorded zero and NULL, and do not assume every printed template '
                              'line is physically stored.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': "SELECT b.ID AS SettlementID,N'Stored field' AS ComponentSource,\n"
                   '       v.Component AS ComponentKey,v.Component AS ComponentLabel,\n'
                   '       CAST(NULL AS nvarchar(100)) AS ParameterLineID,\n'
                   '       v.Amount AS RecordedAmount,CAST(NULL AS money) AS DebitAmount,\n'
                   '       CAST(NULL AS money) AS CreditAmount\n'
                   'FROM [gnd_hrpyr].[tblBonusBill] AS b\n'
                   'CROSS APPLY (VALUES\n'
                   "    (N'Eidi',b.[Eidi]),\n"
                   "    (N'Sanavat',b.[Sanavat]),\n"
                   "    (N'CredbBazKharidMorkhasi',b.[CredbBazKharidMorkhasi]),\n"
                   "    (N'CreditBazKharidMorkhasi',b.[CreditBazKharidMorkhasi]),\n"
                   "    (N'RemainedDebit',b.[RemainedDebit]),\n"
                   "    (N'RemainedCredit',b.[RemainedCredit]),\n"
                   "    (N'Maliat',b.[Maliat]),\n"
                   "    (N'MandeGhabelePardakht',b.[MandeGhabelePardakht]),\n"
                   "    (N'JameMashmoulMaliat',b.[JameMashmoulMaliat]),\n"
                   "    (N'JameEzafat',b.[JameEzafat]),\n"
                   "    (N'JameKosourat',b.[JameKosourat]),\n"
                   "    (N'SahmSandogh',b.[SahmSandogh]),\n"
                   "    (N'UniformCost',b.[UniformCost]),\n"
                   "    (N'ComplementallyInsurance',b.[ComplementallyInsurance]),\n"
                   "    (N'JameDaryafti',b.[JameDaryafti]),\n"
                   "    (N'JameKasrshavande',b.[JameKasrshavande]),\n"
                   "    (N'PurchasableService',b.[PurchasableService])\n"
                   ') AS v(Component,Amount)\n'
                   'WHERE b.ID=@SettlementID\n'
                   'UNION ALL\n'
                   "SELECT b.ID,N'Parameter row',CONVERT(nvarchar(100),d.MonthlyParameterTypeID),\n"
                   '       '
                   't.Description,CONVERT(nvarchar(100),d.IG),NULL,d.DebitAccValue,d.CreditAccValue\n'
                   'FROM [gnd_hrpyr].[tblBonusBill] AS b\n'
                   'INNER JOIN [gnd_hrpyr].[tblBonusBillParameter] AS d ON d.BonusBillID=b.ID\n'
                   'LEFT JOIN [gnd_hrpyr].[tblMonthlyParameterType] AS t ON '
                   't.ID=d.MonthlyParameterTypeID\n'
                   'WHERE b.ID=@SettlementID;',
  'parameters': {'SettlementID': 'int'},
  'reference_interpretation_notes': ['Includes all stored monetary fields, including totals as '
                                     'separately labeled stored fields, plus actual parameter '
                                     'rows. Do not add these output amounts together: stored '
                                     'totals can overlap component amounts. NULL and zero remain '
                                     'distinct. RuzeKarkard is a worked-days measure despite its '
                                     'SQL money type and is excluded. Printed application-only '
                                     'lines are not generated.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['SettlementID',
                     'ComponentSource',
                     'ComponentKey',
                     'ComponentLabel',
                     'ParameterLineID',
                     'RecordedAmount',
                     'DebitAmount',
                     'CreditAmount'],
  'validation': {'id': 'REAL-C07',
                 'reference_sql_sha256': '9b8426dedee004c445777a5b2a75fab8fc3442409d5c1bf0290290dfb62d8ab6',
                 'expected_tables_actually_referenced': ['gnd_hrpyr.tblBonusBill',
                                                         'gnd_hrpyr.tblBonusBillParameter',
                                                         'gnd_hrpyr.tblMonthlyParameterType'],
                 'logical_joins': [],
                 'interpretation_notes': ['Includes all stored monetary fields, including totals '
                                          'as separately labeled stored fields, plus actual '
                                          'parameter rows. Do not add these output amounts '
                                          'together: stored totals can overlap component amounts. '
                                          'NULL and zero remain distinct. RuzeKarkard is a '
                                          'worked-days measure despite its SQL money type and is '
                                          'excluded. Printed application-only lines are not '
                                          'generated.'],
                 'parameter_types': {'SettlementID': 'int'},
                 'validation_parameter_selection': 'SELECT TOP (1) b.ID AS SettlementID FROM '
                                                   'gnd_hrpyr.tblBonusBill b\n'
                                                   'WHERE EXISTS(SELECT 1 FROM '
                                                   'gnd_hrpyr.tblBonusBillParameter d WHERE '
                                                   'd.BonusBillID=b.ID) ORDER BY b.ID',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['SettlementID',
                                    'ComponentSource',
                                    'ComponentKey',
                                    'ComponentLabel',
                                    'ParameterLineID',
                                    'RecordedAmount',
                                    'DebitAmount',
                                    'CreditAmount'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'SettlementID': 0,
                                        'ComponentSource': 0,
                                        'ComponentKey': 0,
                                        'ComponentLabel': 0,
                                        'ParameterLineID': 10,
                                        'RecordedAmount': 0,
                                        'DebitAmount': 10,
                                        'CreditAmount': 10},
                 'sample_blank_string_counts': {'SettlementID': 0,
                                                'ComponentSource': 0,
                                                'ComponentKey': 0,
                                                'ComponentLabel': 0,
                                                'ParameterLineID': 0,
                                                'RecordedAmount': 0,
                                                'DebitAmount': 0,
                                                'CreditAmount': 0},
                 'sample_zero_amount_cells': 5,
                 'elapsed_seconds': 0.078,
                 'validated_at_utc': '2026-09-19T14:03:54.279842+00:00'}},
 {'id': 'REAL-C08',
  'question': 'Show total recorded net packaging weight for each yarn group, separately for '
              'cartons, pallets, and bags.',
  'domain': 'production_packaging',
  'difficulty': 'medium',
  'expected_tables': ['gnd_scprd.tblPacking',
                      'gnd_pjprj.tblInterweaving',
                      'gnd_spgod.tblPackagingType'],
  'expected_table_count': 3,
  'relationship_notes': ['FK: gnd_scprd.tblPacking.InterWeavingID -> gnd_pjprj.tblInterweaving.ID.',
                         'FK: tblPacking.PackagingTypeID -> gnd_spgod.tblPackagingType.ID.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'The active ERP entity for همبافت is tblInterweaving; tblHambaft is '
                              'the old entity. Aggregate Packing.NetWeight by interweaving and '
                              'packaging type without inventing package-to-weight conversions.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT i.ID AS InterweavingID,i.InterweavingCode,t.ID AS PackagingTypeID,\n'
                   '       t.Farsi AS PackagingLabel,\n'
                   '       SUM(p.NetWeight) AS TotalRecordedNetWeight\n'
                   'FROM [gnd_scprd].[tblPacking] AS p\n'
                   'INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=p.InterWeavingID\n'
                   'INNER JOIN [gnd_spgod].[tblPackagingType] AS t ON t.ID=p.PackagingTypeID\n'
                   'WHERE t.ID IN (1,2,3)\n'
                   'GROUP BY i.ID,i.InterweavingCode,t.ID,t.Farsi;',
  'parameters': {},
  'reference_interpretation_notes': ['Verified packaging IDs: 1=pallet, 2=carton, 3=bag. Sum '
                                     'recorded NetWeight only. All-NULL groups remain NULL; NULL '
                                     'readings do not become invented zeros.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['InterweavingID',
                     'InterweavingCode',
                     'PackagingTypeID',
                     'PackagingLabel',
                     'TotalRecordedNetWeight'],
  'validation': {'id': 'REAL-C08',
                 'reference_sql_sha256': '58796997f9d80315c0ef510d79445196390cc9d5b91c36d6b1260d3d97f5a2f6',
                 'expected_tables_actually_referenced': ['gnd_pjprj.tblInterweaving',
                                                         'gnd_scprd.tblPacking',
                                                         'gnd_spgod.tblPackagingType'],
                 'logical_joins': [],
                 'interpretation_notes': ['Verified packaging IDs: 1=pallet, 2=carton, 3=bag. Sum '
                                          'recorded NetWeight only. All-NULL groups remain NULL; '
                                          'NULL readings do not become invented zeros.'],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['InterweavingID',
                                    'InterweavingCode',
                                    'PackagingTypeID',
                                    'PackagingLabel',
                                    'TotalRecordedNetWeight'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'InterweavingID': 0,
                                        'InterweavingCode': 0,
                                        'PackagingTypeID': 0,
                                        'PackagingLabel': 0,
                                        'TotalRecordedNetWeight': 0},
                 'sample_blank_string_counts': {'InterweavingID': 0,
                                                'InterweavingCode': 0,
                                                'PackagingTypeID': 0,
                                                'PackagingLabel': 0,
                                                'TotalRecordedNetWeight': 0},
                 'elapsed_seconds': 0.266,
                 'validated_at_utc': '2026-09-19T14:03:54.553341+00:00'}},
 {'id': 'REAL-C09',
  'question': 'Show recorded cot-diameter readings and grinding completion dates for SAURER FLYER '
              'machines, filtered by machine, completion-date range, and diameter range. Include '
              'every recorded reading in the period.',
  'domain': 'maintenance_condition_monitoring',
  'difficulty': 'hard',
  'expected_tables': ['gnd_amspt.tblFeedbackCheckList',
                      'gnd_amspt.tblFeedback',
                      'gnd_amspt.tblRoutine',
                      'gnd_amast.tblSensor',
                      'gnd_amast.tblEquipment',
                      'gnd_amast.tblEquipmentKind'],
  'expected_table_count': 6,
  'relationship_notes': ['FK: tblFeedbackCheckList.FeedbackID -> gnd_amspt.tblFeedback.ID.',
                         'FK: tblFeedbackCheckList.SensorID -> gnd_amast.tblSensor.ID.',
                         'FK: tblFeedback.RoutineID -> gnd_amspt.tblRoutine.ID.',
                         'FK: tblFeedback.EquipmentID -> gnd_amast.tblEquipment.ID.',
                         'FK: tblEquipment.EquipmentKindID -> gnd_amast.tblEquipmentKind.ID.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'Use FeedbackCheckList.SensorValue and Feedback.EndDate. Equipment '
                              'kind 56 is SAURER FLYER, routine 403 is cot grinding, and sensor 30 '
                              'is its cot-diameter sensor. Historical readings exist, but repeated '
                              'non-NULL readings for the same machine were not demonstrated.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT e.ID AS EquipmentID,e.NameInEnglish AS EquipmentName,\n'
                   '       k.English AS EquipmentKind,r.ID AS RoutineID,r.English AS RoutineName,\n'
                   '       s.ID AS SensorID,s.Description AS SensorDescription,\n'
                   '       f.ID AS FeedbackID,c.IG AS ReadingID,f.EndDate AS '
                   'GrindingCompletionDate,\n'
                   '       c.SensorValue AS CotDiameter\n'
                   'FROM [gnd_amspt].[tblFeedbackCheckList] AS c\n'
                   'INNER JOIN [gnd_amspt].[tblFeedback] AS f ON f.ID=c.FeedbackID\n'
                   'INNER JOIN [gnd_amspt].[tblRoutine] AS r ON r.ID=f.RoutineID\n'
                   'INNER JOIN [gnd_amast].[tblSensor] AS s ON s.ID=c.SensorID\n'
                   'INNER JOIN [gnd_amast].[tblEquipment] AS e ON e.ID=f.EquipmentID\n'
                   'INNER JOIN [gnd_amast].[tblEquipmentKind] AS k ON k.ID=e.EquipmentKindID\n'
                   'WHERE e.ID=@EquipmentID AND k.ID=56 AND r.ID=403 AND s.ID=30\n'
                   '  AND f.EndDate>=@FromDate AND f.EndDate<DATEADD(day,1,@ThroughDate)\n'
                   '  AND c.SensorValue BETWEEN @MinimumDiameter AND @MaximumDiameter\n'
                   'ORDER BY f.EndDate,c.IG;',
  'parameters': {'EquipmentID': 'int',
                 'FromDate': 'date',
                 'ThroughDate': 'date',
                 'MinimumDiameter': 'decimal',
                 'MaximumDiameter': 'decimal'},
  'reference_interpretation_notes': ['Equipment kind 56, routine 403 and sensor 30 are verified '
                                     'domain configuration. Date range is inclusive of both '
                                     'calendar dates; diameter endpoints inclusive. Individual '
                                     'readings are retained, without latest-only selection.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['EquipmentID',
                     'EquipmentName',
                     'EquipmentKind',
                     'RoutineID',
                     'RoutineName',
                     'SensorID',
                     'SensorDescription',
                     'FeedbackID',
                     'ReadingID',
                     'GrindingCompletionDate',
                     'CotDiameter'],
  'validation': {'id': 'REAL-C09',
                 'reference_sql_sha256': '02656a980fa55213fa5f93ee9f8ca7aaf595456eb7d18aa7bcde85ae0517b5b9',
                 'expected_tables_actually_referenced': ['gnd_amast.tblEquipment',
                                                         'gnd_amast.tblEquipmentKind',
                                                         'gnd_amast.tblSensor',
                                                         'gnd_amspt.tblFeedback',
                                                         'gnd_amspt.tblFeedbackCheckList',
                                                         'gnd_amspt.tblRoutine'],
                 'logical_joins': [],
                 'interpretation_notes': ['Equipment kind 56, routine 403 and sensor 30 are '
                                          'verified domain configuration. Date range is inclusive '
                                          'of both calendar dates; diameter endpoints inclusive. '
                                          'Individual readings are retained, without latest-only '
                                          'selection.'],
                 'parameter_types': {'EquipmentID': 'int',
                                     'FromDate': 'date',
                                     'ThroughDate': 'date',
                                     'MinimumDiameter': 'decimal',
                                     'MaximumDiameter': 'decimal'},
                 'validation_parameter_selection': 'SELECT TOP (1) '
                                                   'f.EquipmentID,CONVERT(date,f.EndDate) AS '
                                                   'FromDate,CONVERT(date,f.EndDate) AS '
                                                   'ThroughDate,c.SensorValue AS '
                                                   'MinimumDiameter,c.SensorValue AS '
                                                   'MaximumDiameter\n'
                                                   'FROM gnd_amspt.tblFeedbackCheckList c JOIN '
                                                   'gnd_amspt.tblFeedback f ON f.ID=c.FeedbackID '
                                                   'JOIN gnd_amast.tblEquipment e ON '
                                                   'e.ID=f.EquipmentID\n'
                                                   'WHERE f.RoutineID=403 AND c.SensorID=30 AND '
                                                   'e.EquipmentKindID=56 AND c.SensorValue IS NOT '
                                                   'NULL AND f.EndDate IS NOT NULL ORDER BY c.IG',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['EquipmentID',
                                    'EquipmentName',
                                    'EquipmentKind',
                                    'RoutineID',
                                    'RoutineName',
                                    'SensorID',
                                    'SensorDescription',
                                    'FeedbackID',
                                    'ReadingID',
                                    'GrindingCompletionDate',
                                    'CotDiameter'],
                 'empty': False,
                 'row_count': 1,
                 'row_count_exact': True,
                 'rows_fetched': 1,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 1,
                 'sample_null_counts': {'EquipmentID': 0,
                                        'EquipmentName': 0,
                                        'EquipmentKind': 0,
                                        'RoutineID': 0,
                                        'RoutineName': 0,
                                        'SensorID': 0,
                                        'SensorDescription': 0,
                                        'FeedbackID': 0,
                                        'ReadingID': 0,
                                        'GrindingCompletionDate': 0,
                                        'CotDiameter': 0},
                 'sample_blank_string_counts': {'EquipmentID': 0,
                                                'EquipmentName': 0,
                                                'EquipmentKind': 0,
                                                'RoutineID': 0,
                                                'RoutineName': 0,
                                                'SensorID': 0,
                                                'SensorDescription': 0,
                                                'FeedbackID': 0,
                                                'ReadingID': 0,
                                                'GrindingCompletionDate': 0,
                                                'CotDiameter': 0},
                 'elapsed_seconds': 0.171,
                 'validated_at_utc': '2026-09-19T14:03:54.737964+00:00'}},
 {'id': 'REAL-C10',
  'question': 'List maintenance work orders whose proposed dates fall within a specified date '
              'range.',
  'domain': 'maintenance_condition_monitoring',
  'difficulty': 'easy',
  'expected_tables': ['gnd_amspt.tblWorkOrder'],
  'expected_table_count': 1,
  'relationship_notes': [],
  'feasibility_status': 'FEASIBLE',
  'semantic_evaluation_note': 'Filter on SuggestedExecutionDate; TargetDate is a different field.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT w.ID AS WorkOrderID,w.Code,w.WorkOrderTitle,w.SuggestedExecutionDate\n'
                   'FROM [gnd_amspt].[tblWorkOrder] AS w\n'
                   'WHERE w.SuggestedExecutionDate>=@FromDate\n'
                   '  AND w.SuggestedExecutionDate<DATEADD(day,1,@ThroughDate);',
  'parameters': {'FromDate': 'date', 'ThroughDate': 'date'},
  'reference_interpretation_notes': ['Inclusive calendar-date range; use SuggestedExecutionDate, '
                                     'not TargetDate.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['WorkOrderID', 'Code', 'WorkOrderTitle', 'SuggestedExecutionDate'],
  'validation': {'id': 'REAL-C10',
                 'reference_sql_sha256': '92f4e55b63e1e550f4378f612b0b05e44bb2a665495b395161154295ce129867',
                 'expected_tables_actually_referenced': ['gnd_amspt.tblWorkOrder'],
                 'logical_joins': [],
                 'interpretation_notes': ['Inclusive calendar-date range; use '
                                          'SuggestedExecutionDate, not TargetDate.'],
                 'parameter_types': {'FromDate': 'date', 'ThroughDate': 'date'},
                 'validation_parameter_selection': 'SELECT TOP (1) '
                                                   'CONVERT(date,SuggestedExecutionDate) AS '
                                                   'FromDate,CONVERT(date,SuggestedExecutionDate) '
                                                   'AS ThroughDate FROM gnd_amspt.tblWorkOrder '
                                                   'WHERE SuggestedExecutionDate IS NOT NULL ORDER '
                                                   'BY ID',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['WorkOrderID',
                                    'Code',
                                    'WorkOrderTitle',
                                    'SuggestedExecutionDate'],
                 'empty': False,
                 'row_count': 2,
                 'row_count_exact': True,
                 'rows_fetched': 2,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 2,
                 'sample_null_counts': {'WorkOrderID': 0,
                                        'Code': 1,
                                        'WorkOrderTitle': 0,
                                        'SuggestedExecutionDate': 0},
                 'sample_blank_string_counts': {'WorkOrderID': 0,
                                                'Code': 0,
                                                'WorkOrderTitle': 0,
                                                'SuggestedExecutionDate': 0},
                 'elapsed_seconds': 0.109,
                 'validated_at_utc': '2026-09-19T14:03:54.851408+00:00'}},
 {'id': 'REAL-C11',
  'question': "Show each bank guarantee's amount, its deposit amount, and the net amount after "
              'deducting the deposit.',
  'domain': 'treasury',
  'difficulty': 'easy',
  'expected_tables': ['gnd_firpd.tblBankGuaranty'],
  'expected_table_count': 1,
  'relationship_notes': [],
  'feasibility_status': 'FEASIBLE',
  'semantic_evaluation_note': 'Amount is AccValue, deposit is computed DepositValue, and requested '
                              'net is AccValue - DepositValue. TotalValue instead means AccValue + '
                              'WageValue and is not the requested net.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT b.ID AS BankGuaranteeID,b.AccValue AS GuaranteeAmount,\n'
                   '       b.DepositValue AS DepositAmount,\n'
                   '       b.AccValue-b.DepositValue AS NetAmount\n'
                   'FROM [gnd_firpd].[tblBankGuaranty] AS b;',
  'parameters': {},
  'reference_interpretation_notes': [],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['BankGuaranteeID', 'GuaranteeAmount', 'DepositAmount', 'NetAmount'],
  'validation': {'id': 'REAL-C11',
                 'reference_sql_sha256': '35e9e2bdd9ba662c25844750291ccce6c7eade034c50fc46e373179ecfed69cb',
                 'expected_tables_actually_referenced': ['gnd_firpd.tblBankGuaranty'],
                 'logical_joins': [],
                 'interpretation_notes': [],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['BankGuaranteeID',
                                    'GuaranteeAmount',
                                    'DepositAmount',
                                    'NetAmount'],
                 'empty': False,
                 'row_count': 'not fully counted',
                 'row_count_exact': False,
                 'rows_fetched': 10,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 10,
                 'sample_null_counts': {'BankGuaranteeID': 0,
                                        'GuaranteeAmount': 0,
                                        'DepositAmount': 0,
                                        'NetAmount': 0},
                 'sample_blank_string_counts': {'BankGuaranteeID': 0,
                                                'GuaranteeAmount': 0,
                                                'DepositAmount': 0,
                                                'NetAmount': 0},
                 'elapsed_seconds': 0.016,
                 'validated_at_utc': '2026-09-19T14:03:54.875289+00:00'}},
 {'id': 'REAL-C14',
  'question': 'Which yarn groups have at least one numbered lot with positive posted warehouse '
              'stock in the current financial period, without deducting reservations or '
              'allocations?',
  'domain': 'sales',
  'difficulty': 'hard',
  'expected_tables': ['gnd_spgod.tblGood',
                      'gnd_pjprj.tblInterweaving',
                      'gnd_scinv.tblEnter',
                      'gnd_scinv.tblEnterDetail',
                      'gnd_scinv.tblExit',
                      'gnd_scinv.tblExitDetail',
                      'gnd_fiaci.tblPeriodSpec'],
  'expected_table_count': 7,
  'relationship_notes': ['FK: gnd_scinv.tblEnterDetail.EnterID -> gnd_scinv.tblEnter.ID.',
                         'FK: gnd_scinv.tblExitDetail.ExitID -> gnd_scinv.tblExit.ID.',
                         'FKs: tblEnterDetail.CredbGoodID and tblExitDetail.CredbGoodID -> '
                         'gnd_spgod.tblGood.ID.',
                         'Logical subtype join: tblGood.InterweavingID = '
                         'gnd_pjprj.tblInterweaving.ID. The declared FK targets the shared '
                         'gnd_pjprj.tblProject.ID key; the ERP good view explicitly uses the '
                         'interweaving subtype relationship.',
                         'Financial-period membership is a date-range join from movement DoneDate '
                         'to tblPeriodSpec.BeginDate/EndDate, as used by the inspected stock views '
                         'and functions.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'Compute posted stock as receipts minus issues by item and '
                              'warehouse; require nonblank Good.LotNumber and positive balance. '
                              'tblInventoryQty is empty in this snapshot. Do not add reservation, '
                              'allocation, saleability, or order-quantity rules.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'WITH CurrentPeriods AS (\n'
                   '    SELECT p.ID,p.BeginDate,p.EndDate\n'
                   '    FROM [gnd_fiaci].[tblPeriodSpec] AS p\n'
                   '    WHERE CONVERT(date,GETDATE()) BETWEEN p.BeginDate AND p.EndDate\n'
                   '), Movements AS (\n'
                   '    SELECT p.ID AS PeriodID,e.CredbInventoryID AS InventoryID,\n'
                   '           d.CredbGoodID AS GoodID,COALESCE(d.Qty,0) AS SignedQuantity\n'
                   '    FROM [gnd_scinv].[tblEnter] AS e\n'
                   '    INNER JOIN [gnd_scinv].[tblEnterDetail] AS d ON d.EnterID=e.ID\n'
                   '    INNER JOIN CurrentPeriods AS p ON e.DoneDate BETWEEN p.BeginDate AND '
                   'p.EndDate\n'
                   '    WHERE e.Code IS NOT NULL\n'
                   '    UNION ALL\n'
                   '    SELECT p.ID,e.CredbInventoryID,d.CredbGoodID,-COALESCE(d.Qty,0)\n'
                   '    FROM [gnd_scinv].[tblExit] AS e\n'
                   '    INNER JOIN [gnd_scinv].[tblExitDetail] AS d ON d.ExitID=e.ID\n'
                   '    INNER JOIN CurrentPeriods AS p ON e.DoneDate BETWEEN p.BeginDate AND '
                   'p.EndDate\n'
                   '    WHERE e.Code IS NOT NULL\n'
                   '), Balances AS (\n'
                   '    SELECT PeriodID,InventoryID,GoodID,SUM(SignedQuantity) AS PostedStock\n'
                   '    FROM Movements\n'
                   '    GROUP BY PeriodID,InventoryID,GoodID\n'
                   ')\n'
                   'SELECT DISTINCT i.ID AS InterweavingID,i.InterweavingCode\n'
                   'FROM Balances AS b\n'
                   'INNER JOIN [gnd_spgod].[tblGood] AS g ON g.ID=b.GoodID\n'
                   'INNER JOIN [gnd_pjprj].[tblInterweaving] AS i ON i.ID=g.InterweavingID\n'
                   "WHERE b.PostedStock>0 AND NULLIF(LTRIM(RTRIM(g.LotNumber)),N'') IS NOT NULL;",
  'parameters': {},
  'reference_interpretation_notes': ['Current period is evaluated using SQL Server GETDATE(). '
                                     'Posted means non-NULL movement Code; quantity NULL handling '
                                     'follows the inspected stock logic. Balance is per item, '
                                     'warehouse and current period. Do not subtract demand, '
                                     'reservations or allocations, or add undocumented warehouse '
                                     'restrictions. Results are date-dependent.'],
  'logical_joins': ['Movement DoneDate lies within PeriodSpec.BeginDate/EndDate (date-range '
                    'relationship).',
                    'Good.InterweavingID=Interweaving.ID uses their common Project key and '
                    'verified subtype semantics; no direct FK between these two tables.'],
  'execution_valid': True,
  'result_columns': ['InterweavingID', 'InterweavingCode'],
  'validation': {'id': 'REAL-C14',
                 'reference_sql_sha256': 'e2a5fa804b9dfd5513b5c5ff123b7287720222194fdbf49ab74dfe96252316a5',
                 'expected_tables_actually_referenced': ['gnd_fiaci.tblPeriodSpec',
                                                         'gnd_pjprj.tblInterweaving',
                                                         'gnd_scinv.tblEnter',
                                                         'gnd_scinv.tblEnterDetail',
                                                         'gnd_scinv.tblExit',
                                                         'gnd_scinv.tblExitDetail',
                                                         'gnd_spgod.tblGood'],
                 'logical_joins': ['Movement DoneDate lies within PeriodSpec.BeginDate/EndDate '
                                   '(date-range relationship).',
                                   'Good.InterweavingID=Interweaving.ID uses their common Project '
                                   'key and verified subtype semantics; no direct FK between these '
                                   'two tables.'],
                 'interpretation_notes': ['Current period is evaluated using SQL Server GETDATE(). '
                                          'Posted means non-NULL movement Code; quantity NULL '
                                          'handling follows the inspected stock logic. Balance is '
                                          'per item, warehouse and current period. Do not subtract '
                                          'demand, reservations or allocations, or add '
                                          'undocumented warehouse restrictions. Results are '
                                          'date-dependent.'],
                 'parameter_types': {},
                 'validation_parameter_selection': None,
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['InterweavingID', 'InterweavingCode'],
                 'empty': False,
                 'row_count': 1,
                 'row_count_exact': True,
                 'rows_fetched': 1,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 1,
                 'sample_null_counts': {'InterweavingID': 0, 'InterweavingCode': 0},
                 'sample_blank_string_counts': {'InterweavingID': 0, 'InterweavingCode': 0},
                 'elapsed_seconds': 0.218,
                 'validated_at_utc': '2026-09-19T14:03:55.107463+00:00'}},
 {'id': 'REAL-C15',
  'question': 'For a selected employee and payroll month, show the leave balance in days recorded '
              "in that month's payroll work record.",
  'domain': 'hr_attendance',
  'difficulty': 'easy',
  'expected_tables': ['gnd_hrpyr.tblWorkTime', 'gnd_egbse.tblYearMonth'],
  'expected_table_count': 2,
  'relationship_notes': ['FK: gnd_hrpyr.tblWorkTime.YearMonthID -> gnd_egbse.tblYearMonth.ID.'],
  'feasibility_status': 'FEASIBLE WITH WORDING CLARIFICATION',
  'semantic_evaluation_note': 'RemainedLeave is a physically stored monthly value, uniquely keyed '
                              'by employee and year-month. Preserve NULL as not recorded; do not '
                              'claim that the value independently proves correct month-end accrual '
                              'or carry-forward logic.',
  'top10_full_coverage_possible': True,
  'top10_recall_ceiling': 1.0,
  'reference_sql': 'SELECT w.YearMonthID,y.FromDate AS PayrollMonthStart,y.ToDate AS '
                   'PayrollMonthEnd,\n'
                   '       w.RemainedLeave AS RecordedLeaveBalanceDays\n'
                   'FROM [gnd_hrpyr].[tblWorkTime] AS w\n'
                   'INNER JOIN [gnd_egbse].[tblYearMonth] AS y ON y.ID=w.YearMonthID\n'
                   'WHERE w.EmployeeID=@EmployeeID AND w.YearMonthID=@PayrollMonthID;',
  'parameters': {'EmployeeID': 'int', 'PayrollMonthID': 'int'},
  'reference_interpretation_notes': ['Return physically stored days for the selected '
                                     'employee/month. NULL is not recorded and remains NULL. Do '
                                     'not recalculate leave or claim correctness of the original '
                                     'accrual calculation.'],
  'logical_joins': [],
  'execution_valid': True,
  'result_columns': ['YearMonthID',
                     'PayrollMonthStart',
                     'PayrollMonthEnd',
                     'RecordedLeaveBalanceDays'],
  'validation': {'id': 'REAL-C15',
                 'reference_sql_sha256': '39d8ca5f1ede3944f97f0d2371f4a84a4817c59e3c65c045265645d8f96b574a',
                 'expected_tables_actually_referenced': ['gnd_egbse.tblYearMonth',
                                                         'gnd_hrpyr.tblWorkTime'],
                 'logical_joins': [],
                 'interpretation_notes': ['Return physically stored days for the selected '
                                          'employee/month. NULL is not recorded and remains NULL. '
                                          'Do not recalculate leave or claim correctness of the '
                                          'original accrual calculation.'],
                 'parameter_types': {'EmployeeID': 'int', 'PayrollMonthID': 'int'},
                 'validation_parameter_selection': 'SELECT TOP (1) w.EmployeeID,w.YearMonthID AS '
                                                   'PayrollMonthID FROM gnd_hrpyr.tblWorkTime w '
                                                   'ORDER BY w.ID DESC',
                 'parameter_selection_scope': 'Deterministic bounded existing-row example for '
                                              'validation only; not part of reference SQL.',
                 'bound_parameter_values_persisted': False,
                 'execution_valid': True,
                 'result_columns': ['YearMonthID',
                                    'PayrollMonthStart',
                                    'PayrollMonthEnd',
                                    'RecordedLeaveBalanceDays'],
                 'empty': False,
                 'row_count': 1,
                 'row_count_exact': True,
                 'rows_fetched': 1,
                 'fetch_limit': 10,
                 'validation_scope': 'Execution and at most the first 10 returned rows; no '
                                     'full-result semantic certification.',
                 'result_columns_match': True,
                 'row_count_lower_bound': 1,
                 'sample_null_counts': {'YearMonthID': 0,
                                        'PayrollMonthStart': 0,
                                        'PayrollMonthEnd': 0,
                                        'RecordedLeaveBalanceDays': 1},
                 'sample_blank_string_counts': {'YearMonthID': 0,
                                                'PayrollMonthStart': 0,
                                                'PayrollMonthEnd': 0,
                                                'RecordedLeaveBalanceDays': 0},
                 'elapsed_seconds': 0.031,
                 'validated_at_utc': '2026-09-19T14:03:55.157767+00:00'}}]
