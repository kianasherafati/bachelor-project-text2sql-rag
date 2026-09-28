# Final unseen benchmark — immutable freeze

**SUCCESS: ERP-FINAL-UNSEEN-v1.0**

Manifest SHA-256: `8e812121d26259ff7c100a83dce0e07f2f2bc4caf8e68c85614c227672e54fc8`

50 approved/executable cases; 42 nonempty, 8 empty, 0 failed. All 50 dependency sets finalized; 139 unique physical tables. No pending reviews or semantic blockers.

[Canonical manifest](final_unseen_freeze_manifest.json) contains exact repository-relative public/private/implementation/schema/index file hashes. Its adjacent `.sha256` is the digest of the exact deterministic manifest bytes. This explanatory file is outside the hash payload to avoid a self-referential digest.

## Frozen retrieval identity

Exact English question -> original BGE-M3 Dense Top50 UNION original MiniLM Graph Top50 -> deduplicate by fully qualified table -> BGE-reranker-v2-m3 -> Top10. No rejected business-dense or reverse-graph candidate sources. Existing metadata labels belong only to the frozen reranker representation. Models, revisions, source hashes and schema/index hashes are in the manifest. No model was loaded or run.

## Validation and integrity

Only U04/U32/U42 were revalidated in this completion; all returned ten bounded rows. Other 47 execution records were reused. U04 helper closure adds six physical dependencies to that case, giving eight tables; the corpus-wide dependency union is 139. Domain allocation unchanged. Public privacy checks passed; private files are Git-ignored and represented only by hashes.

## Immutability

Do not edit questions, Gold or expected tables based on model outcomes. Do not replace difficult/failed cases or alter ground truth using retrieval results. For a genuine annotation defect, retain the frozen result and publish an erratum rather than silently modifying and rerunning as unchanged.

Final retrieval, reranking, Qwen generation and final Execution Accuracy have NOT run. Database permissions were not changed. No commit or push.

Next step only: freeze Qwen inference/prompt/decoding and Execution Accuracy comparison policies using old development/observed material. This step has not been performed.
