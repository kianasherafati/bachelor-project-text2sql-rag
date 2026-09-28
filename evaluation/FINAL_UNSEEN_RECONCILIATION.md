# Final Unseen Reconciliation

50 final-approved cases; 0 pending human decisions; 0 conflicting decisions; 0 replacement reviews pending. All 50 dependency sets finalized; overall_expected_table_count_finalized=True. 139 unique physical dependencies.

50 executable, 42 nonempty, 8 empty, 0 failed. U04/U32/U42 alone were revalidated with at most 10 fetched rows each; all three were nonempty. The other 47 execution results were preserved.

U04 uses the approved COALESCE fallback and includes its six additional helper-derived physical dependencies. U32 uses warehouse receipt lines. U42 uses the latest completed workflow row and absence of sourced CardLog. These authoritative corrections supersede earlier interpretations. Domain allocation is unchanged.

No final retrieval, reranking, Qwen or final Execution Accuracy has run. No case was selected or changed using final model outcomes. No permission changes, commit or push. Formal immutable identity is specified in FINAL_UNSEEN_FREEZE.md and final_unseen_freeze_manifest.json.
