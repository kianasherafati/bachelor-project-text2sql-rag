# Current Gold physical dependency audit

**Metadata dependency closure for current SQL. Execution status is recorded separately; formal freeze identity is recorded separately.**

Scoped SQL ASTs identify direct relations. Inspected SQL Server metadata supplies computed-column/helper dependencies. Every record matches its successful or failed bounded-attempt SQL hash. No unrelated FK neighbors are added.

Nine required physical tables are outside the unchanged indexed corpus: initial-registration metadata for U08; stock company metadata for U31; employee-shift metadata for U37; contact/person/prefix, pro forma and supplier metadata used by the U49 entity views. They are included explicitly. U37 uses an inline SELECT-only calculation instead of privileged ERP function calls. U08/U09 match their closed authoritative decisions and passed bounded validation. All 50 dependency sets are human-approved and finalized. The separate freeze manifest determines immutable artifact identity.

| Case | Current physical tables | Hidden dependencies beyond direct SQL | Current-time helpers |
|---|---|---|---|
| FINAL-U01 | gnd_crsls.tblSalesAndServicesInvoice | None | None |
| FINAL-U02 | gnd_scpch.tblPurchaseOrder, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail, gnd_spgod.tblGood | None | None |
| FINAL-U03 | gnd_hrprs.tblEmployee, gnd_scpch.tblGoodServiceRequest, gnd_scpch.tblGoodServiceRequestDetail, gnd_spgod.tblGood | None | None |
| FINAL-U04 | gnd_crsls.tblLoading, gnd_crsls.tblLoadingDetail, gnd_crsls.tblLoadingSerialDetail, gnd_scinv.tblSerial, gnd_scinv.tblTransportationCompanyDriverDetail, gnd_scprd.tblPacking, gnd_scprd.tblRawMaterialPacking, gnd_scprd.tblWastePacking | gnd_crsls.tblLoadingDetail, gnd_crsls.tblLoadingSerialDetail, gnd_scinv.tblSerial, gnd_scprd.tblPacking, gnd_scprd.tblRawMaterialPacking, gnd_scprd.tblWastePacking | None |
| FINAL-U05 | gnd_crsls.tblSalesOrder, gnd_crsls.tblSalesOrderDetail, gnd_crsls.tblSalesOrderWasteDetail | None | None |
| FINAL-U06 | gnd_scinv.tblEnter, gnd_scinv.tblInventory, gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblPurchaseInvoiceGoodDetailEnter, gnd_scpch.tblPurchaseInvoiceSeparatedEnter, gnd_spgod.tblGood | None | None |
| FINAL-U07 | gnd_egbse.tblYearMonth, gnd_hrcio.tblEmployeeShiftAdditionalOffDates, gnd_hrprs.tblEmployee | None | None |
| FINAL-U08 | gnd_egbpm.tblProcessStep, gnd_egbse.tblDepartment, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork, gnd_egwfm.tblWorkRoute, gnd_hrcio.tblEmployeeExitPermission, gnu_hrcio.xblEmployeeExitPermission | None | None |
| FINAL-U09 | gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShiftTemplate, gnd_hrprs.tblEmployee | None | None |
| FINAL-U10 | gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime | None | None |
| FINAL-U11 | gnd_egbse.tblYearMonth, gnd_hrfod.tblEmployeeFood, gnd_hrfod.tblEmployeeFoodDelivery, gnd_hrfod.tblEmployeeFoodRequest, gnd_hrfod.tblEmployeeFoodRequestDetail, gnd_hrprs.tblEmployee | None | None |
| FINAL-U12 | gnd_hrprs.tblEmployee, gnd_hrpyr.tblCofferMembership, gnd_hrpyr.tblEmployeeLoanRequest | None | None |
| FINAL-U13 | gnd_pjprj.tblInterweaving, gnd_scprd.tblPacking, gnd_spgod.tblQualityType, gnd_spgod.tblSpinningCountType, gnd_spgod.tblSpinningSystemType, gnd_spgod.tblYarnType | None | None |
| FINAL-U14 | gnd_pjprj.tblInterweaving, gnd_scprd.tblSpindleLable, gnd_spgod.tblSpinningSystemType | None | None |
| FINAL-U15 | gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblQualityControl, gnd_scpch.tblQualityControlDetail, gnd_spgod.tblGood | None | None |
| FINAL-U16 | gnd_amast.tblEquipment, gnd_amspt.tblRoutine, gnd_amspt.tblWorkOrder | None | None |
| FINAL-U17 | gnd_amspt.tblRoutine, gnd_amspt.tblRoutineCovered | None | None |
| FINAL-U18 | gnd_firpd.tblPayRequest, gnd_firpd.tblPayRequestDetail | None | None |
| FINAL-U19 | gnd_fiaci.tblAccount, gnd_firpd.tblBankInput, gnd_firpd.tblBankInputDetail | None | None |
| FINAL-U20 | gnd_fiaci.tblAccount, gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail, gnd_fiaci.tblTransDetailDetail | None | None |
| FINAL-U21 | gnd_pjprj.tblProject, gnd_scpch.tblPurchaseInvoiceGoodAndService | None | None |
| FINAL-U22 | gnd_egbse.tblChatLastSeen | None | None |
| FINAL-U23 | gnd_egbse.tblRole, gnd_egbse.tblRoleDomain, gnd_egbse.tblRoleSystem, gnd_egbse.tblRoleSystemForm, gnd_egbse.tblRoleSystemReport, gnd_egfrm.tblFormType, gnd_egrpt.tblReport, gnd_egsys.tblCaption, gnd_egsys.tblSystem | None | None |
| FINAL-U24 | gnd_egbpm.tblProcessStep, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork, gnd_ofsct.tblInternalLetter | None | None |
| FINAL-U25 | gnd_scinv.tblGoodConsume, gnd_scinv.tblGoodConsumeDetail, gnd_spgod.tblGood | None | None |
| FINAL-U26 | gnd_amast.tblEquipment, gnd_amspt.tblFeedback, gnd_amspt.tblWorkOrder, gnd_egwfm.tblWorkRoute | None | None |
| FINAL-U27 | gnd_egfrm.tblFormEquivalency, gnd_fiaci.tblAccountDetail, gnd_fiaci.tblTrans, gnd_fiaci.tblTransDetail, gnd_fiaci.tblTransDetailDetail, gnd_firpd.tblInputChequeBankReceive | None | None |
| FINAL-U28 | gnd_egbse.tblContact, gnd_firpd.tblPayRequest, gnd_firpd.tblPayRequestDetail | None | None |
| FINAL-U29 | gnd_firpd.tblInputCheque | None | None |
| FINAL-U30 | gnd_crsls.tblLoading, gnd_crsls.tblLoadingScannedBarcode, gnd_pjprj.tblInterweaving | None | None |
| FINAL-U31 | gnd_fiaci.tblPeriodSpec, gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblExit, gnd_scinv.tblExitDetail, gnd_scinv.tblInventory, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail, gnd_spgod.tblGood, gnu_scinv.xblEnter, gnu_scinv.xblExit | gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblExit, gnd_scinv.tblExitDetail, gnu_scinv.xblEnter, gnu_scinv.xblExit | None |
| FINAL-U32 | gnd_egbse.tblContact, gnd_scinv.tblEnter, gnd_scinv.tblEnterDetail, gnd_scinv.tblInventory, gnd_spgod.tblGood | None | None |
| FINAL-U33 | gnd_egwfm.tblWorkEnd | None | None |
| FINAL-U34 | gnd_egbpm.tblProcessStep, gnd_egbse.tblContact, gnd_egwfm.tblRunStatusTypeL, gnd_egwfm.tblWork | None | None |
| FINAL-U35 | gnd_egbse.tblContact, gnd_ofsct.tblInternalLetter, gnd_ofsct.tblRecEmpInternalLetter | None | None |
| FINAL-U36 | gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime | None | None |
| FINAL-U37 | gnd_egbse.tblConvertDateTypeL, gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblSecurityConfig, gnd_egbse.tblUnit, gnd_egbse.tblUser, gnd_egbse.tblYearMonth, gnd_egsys.tblSystemConfig, gnd_egsys.tblSystemConfigDetail, gnd_hrcio.tblAttendenceRules, gnd_hrcio.tblCalendarHolidays, gnd_hrcio.tblCardLog, gnd_hrcio.tblEmployeeLeave, gnd_hrcio.tblEmployeeSavedLeave, gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShift, gnd_hrcio.tblShiftDetail, gnd_hrcio.tblShiftTemplate, gnd_hrcio.tblShiftTemplateDetail, gnd_hrcio.tblWorkShiftType, gnd_hrprs.tblContract, gnd_hrprs.tblEmployee, gnd_hrprs.tblEmployeeEmploymentStatus, gnd_hrprs.tblEmployeeIncentive, gnu_hrcio.xblEmployeeShift | gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblSecurityConfig, gnd_egbse.tblUnit, gnd_egbse.tblUser, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblWorkShiftType, gnu_hrcio.xblEmployeeShift | None |
| FINAL-U38 | gnd_egbse.tblYearMonth, gnd_hrapr.tblManagerHRFeedback, gnd_hrapr.tblManagerHRFeedbackLeavedEmployeeDetail | None | None |
| FINAL-U39 | gnd_egbse.tblYearMonth, gnd_hrprs.tblContract, gnd_hrprs.tblLegalPosition, gnd_hrpyr.tblWorkTime | None | None |
| FINAL-U40 | gnd_egbse.tblYearMonth, gnd_hrprs.tblContract, gnd_hrprs.tblJobGroup, gnd_hrpyr.tblWorkTime | None | None |
| FINAL-U41 | gnd_egbse.tblYearMonth, gnd_hrcio.tblCardLog, gnd_hrcio.tblWorkTimeAllDays, gnd_hrprs.tblEmployee | None | None |
| FINAL-U42 | gnd_egwfm.tblWork, gnd_hrcio.tblCardLog, gnd_hrcio.tblForgottenEnterExit, gnd_hrprs.tblEmployee | None | None |
| FINAL-U43 | gnd_egbse.tblYearMonth, gnd_hrcio.tblCardLog, gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShift, gnd_hrcio.tblShiftDetail, gnd_hrcio.tblShiftTemplate, gnd_hrcio.tblWorkShiftType, gnd_hrprs.tblEmployee | gnd_hrcio.tblEmployeeShift, gnd_hrcio.tblEmployeeShiftModifications, gnd_hrcio.tblShift, gnd_hrcio.tblShiftDetail, gnd_hrcio.tblShiftTemplate, gnd_hrcio.tblWorkShiftType | None |
| FINAL-U44 | gnd_egbse.tblYearMonth, gnd_hrprs.tblEmployee, gnd_hrpyr.tblWorkTime | None | None |
| FINAL-U45 | gnd_ficac.tblProjectStandardProduction, gnd_ficac.tblProjectStandardProductionScannedBarcode, gnd_scprd.tblPacking | None | None |
| FINAL-U46 | gnd_scpch.tblPurchaseInvoiceGoodAndService, gnd_scpch.tblPurchaseInvoiceGoodDetailEnter, gnd_spgod.tblGood | None | None |
| FINAL-U47 | gnd_hrprs.tblEmployee, gnd_scpch.tblPurchaseInquiry, gnd_scpch.tblPurchaseOrder, gnd_scpch.tblPurchaseOrderDetail, gnd_scpch.tblPurchaseRequest, gnd_scpch.tblPurchaseRequestDetail | None | None |
| FINAL-U48 | gnd_egbpm.tblProcessStep, gnd_egbse.tblContact, gnd_egwfm.tblWork, gnd_scpch.tblPurchaseInquiry | None | None |
| FINAL-U49 | gnd_egbse.tblContact, gnd_egbse.tblConvertDateTypeL, gnd_egbse.tblPerson, gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblPrefix, gnd_egbse.tblUser, gnd_scpch.tblNotifyEnter, gnd_scpch.tblPrePurchaseInvoice, gnd_scpch.tblPrePurchaseInvoiceDetail, gnd_scpch.tblQualityControl, gnd_scpch.tblQualityControlDetail, gnd_scpch.tblSupplier, gnd_spgod.tblGood, gnu_egbse.xblContact, gnu_egbse.xblPerson, gnu_egbse.xblPrefix, gnu_scpch.xblPrePurchaseInvoice, gnu_scpch.xblSupplier | gnd_egbse.tblContact, gnd_egbse.tblConvertDateTypeL, gnd_egbse.tblPerson, gnd_egbse.tblPersonStatus, gnd_egbse.tblPosition, gnd_egbse.tblPrefix, gnd_egbse.tblUser, gnd_scpch.tblSupplier, gnu_egbse.xblContact, gnu_egbse.xblPerson, gnu_egbse.xblPrefix, gnu_scpch.xblPrePurchaseInvoice, gnu_scpch.xblSupplier | None |
| FINAL-U50 | gnd_crsls.tblCustomer, gnd_crsls.tblSalesAndServicesInvoice, gnd_crsls.tblSalesAndServicesInvoiceSalesDetail, gnd_crsls.tblSalesAndServicesInvoiceServDetail, gnd_crsls.tblSellableService, gnd_egbse.tblContact, gnd_fiaci.tblVatPercentage, gnd_spgod.tblGood | gnd_fiaci.tblVatPercentage | None |
