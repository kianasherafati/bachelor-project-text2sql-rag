# Final evaluation orchestration

Infrastructure status: **COMPLETE for offline engineering and integration contracts**.
Final exposure status: **BLOCKED**. Qwen inference is not yet frozen. There is no
approved final release/bootstrap or verified live platform proof in this task.
Nothing here claims readiness for final evaluation.

## Commands

Run from `C:\Users\Pc\Desktop\Bachelor_Project`:

```powershell
.venv/Scripts/python.exe -B -m evaluation.final_evaluation_runner --dry-run --run-id dev-runner-20260929
.venv/Scripts/python.exe -B -m evaluation.final_evaluation_runner --dry-run --run-id dev-runner-20260929 --resume
```

Omitting a mode selects `DEV_DRY_RUN`. It uses **only** the pinned old
`qwen_preflight_input.jsonl` bundle, checks its hash before reading it, and requires
exactly DEV-01, DEV-02, DEV-03 in that order. No Qwen runtime is imported. Retrieval
and reranking replay previously saved old development Top10 context; their timings
are replay timings, not model performance measurements. Synthetic Gold SQL,
predictions and DB-API rows exercise the real frozen policy code. They do not
answer the ERP questions and are **not an accuracy evaluation**.

Every result and summary is labeled:
**DEVELOPMENT DRY RUN — NOT FINAL EVALUATION**.

The future final invocation, **not executed**, is:

```powershell
.venv/Scripts/python.exe -B -m evaluation.final_evaluation_runner --final-frozen-run --run-id final-v1-run-001 --release evaluation/final_runner_release.json --release-sha256 (Get-Content -LiteralPath evaluation/final_runner_release.sha256 -Raw).Trim()
```

The release and its one-digest SHA sidecar deliberately do not exist yet. This
command can execute only after the prerequisites below are independently verified
and frozen. Adding `--resume` cannot bypass identity checks. A rerun needs a new
run ID; there is no overwrite/force/retry flag.

## Architecture and contracts

`EvaluationCase` carries case ID, exact question, private typed parameters, Gold
SQL, evaluation-only expected physical tables, benchmark version and optional
source case hash. The run manifest binds every case's full input hash and order.
Domain, difficulty and private provenance are absent from this contract.

The runner calls these boundaries:

1. `provider.retrieve(question)` and `provider.rerank(question, candidates)`.
   `FrozenSchemaProvider` delegates to the existing application frozen retrieval
   adapter. It attaches full frozen schema documents rather than UI excerpts.
2. `generator.generate(question, tuple[SchemaContext, ...]) -> Generation`.
   Only the exact question and ten independently retrieved schema contexts cross
   this boundary. The trusted frozen generator adapter must return the exact final
   rendered prompt actually used, including chat formatting/truncation, and raw
   output. The runner hashes that text. It does not invent Qwen prompt/decoding
   settings or call the prospective Qwen runtime.
3. Frozen `policy_sql_contract.extract_output` and `validate_query`. Prediction
   scope is exclusively the retrieved Top10. Rejection skips both SQL reads.
4. `PolicyPairExecutor` delegates the entire pair to frozen
   `policy_query_executor.compare_pair`, including `read_result`, parameter
   binding, full-result collection, ordering, comparison, and empty-AST safeguard.
   An observing DB-API wrapper records Gold and prediction separately. It never
   changes queries, limits, values, transaction settings or comparison semantics.
5. Immutable per-case journal, deterministic aggregates and final export.

Gold and expected tables never enter provider/generator calls. Recall@10 and full
schema coverage are calculated only after context is selected. Gold is used only
by the executor/comparator. Private parameter values are bound identically to both
sides and are never placed in prompts or output artifacts. Case hashes preserve
binding types as well as values, so changing `int` to `Decimal` rejects resume.

## Stage and result schema

Every case has `RETRIEVAL`, `RERANKING`, `GENERATION`, `OUTPUT_PARSING`,
`VALIDATION`, `GOLD_EXECUTION`, `PREDICTION_EXECUTION`, `RESULT_COMPARISON` entries,
each with status, elapsed milliseconds and optional structured sanitized error.
Downstream stages are explicitly skipped after a failure. Comparison time is
frozen pair wall time minus observed reads; it also includes the frozen pair's
validation/isolation overhead. This limitation is recorded in the manifest.

The JSON result includes case/input/question hashes; benchmark, evaluation,
retrieval and generator identities; ranked Top10 names and logits; retrieval
metrics; exact prompt hash; raw generated output plus its original hash; parsed
SQL; stage statuses/timings; validation reason; Gold/prediction column/count/
completeness metadata; comparison reason; frozen execution outcome; total timing;
model/revision/Qwen policy identifiers; sanitized error stage/type/message.
Database rows and connection details are not persisted. Recognizable credential
or connection text suppresses the entire affected output field; its original
output hash remains available. Arbitrary exception text is never serialized.

The outcome taxonomy is imported conceptually from the unchanged frozen policy:
`GENERATION_ERROR`, `VALIDATION_REJECTED`, `EXECUTION_ERROR`, `RESULT_MISMATCH`,
`EXECUTION_CORRECT`, `EVALUATION_BLOCKED`, `EVALUATION_LIMIT`.
`INSUFFICIENT_SCHEMA` remains an explicit pipeline/generation status, mapped to
`GENERATION_ERROR` under the frozen abstention rule. Gold/control failures block
accuracy publication. Resource censoring is separate and retains the fixed case
denominator. Empty results delegate to the frozen structural safeguard.

## Manifest and artifacts

`run_manifest.json` binds UTC creation time, run ID/mode/label, benchmark and policy
hashes, case order/count/input hashes, retrieval identity, generator identity and
policy hash, runtime-lock hash, non-sensitive hashed DB and transaction identities,
execution preflight proof, validation-schema hash, and hashes of runner/contracts/
I/O/fixtures/comparator/validator/executor/retrieval-adapter source files.

Development output: `evaluation/dev_dry_runs/<run_id>/`.
Future final output: `evaluation/final_runs/<run_id>/` (fixed and not created here).
Both directories are Git-ignored.

- `run_manifest.json`, `run_manifest.sha256`
- `cases/00000.json`, etc.: canonical result plus previous-record hash and checksum
- `completion_receipts/00000.sha256`, etc.: independent exact-byte completion receipt
- `per_case_results.jsonl`, `errors.jsonl`
- `summary.json`, `retrieval_metrics.json`, `execution_accuracy_summary.json`
- `.writer.lock`: OS-released-on-process-death exclusive writer lock

## Crash safety and integrity

Files are UTF-8, sorted-key JSON, LF terminated, finite-number-only serialization.
Fully flushed temporary files are published using exclusive atomic hard links;
existing completed files are never replaced. Requires a local filesystem with
working atomic hard links/OS locks (verified here on the current Windows host).
This is process-interruption safety, not a claim of protection against malicious
filesystem administrators or catastrophic storage failure.

Resume validates the complete manifest (creation timestamp retained), its checksum,
case order/input/source/schema/runtime identities, contiguous journal, hash chain,
and every completion receipt before generation. It skips all completed cases,
including failed model cases. Deletion/corruption and changed parameters or inputs
are rejected. Completed aggregate exports are byte-checked, never overwritten.
Missing exports can be reconstructed from a complete intact case journal.

The receipt is written immediately before publishing its completed case. A crash
in that narrow interval, or removal of a completed file, blocks resume rather than
risk regeneration. A crash before any completion receipt permits explicit resume
of that uncompleted case. Unpublished `.pending-*` files are never treated as
completed records. A partially created/corrupt manifest also fails closed.

Final snapshot continuity is stricter than filesystem recovery: the frozen policy
requires **one run-wide SNAPSHOT transaction**. If a process/connection dies and
that transaction cannot be preserved, the old run cannot resume on a new live
snapshot. No silent live-read fallback or permission changes are allowed. A new
run requires independent explicit authorization and a new ID.

## Future final release prerequisites and trusted bootstrap

This is an integration contract for a **trusted, reviewed Python bootstrap**, not
a sandbox for arbitrary code. Supply a new release artifact after Qwen is frozen;
do not edit the existing partial policy manifest or any frozen benchmark file.

The approved `final_runner_release.json` must contain:

```json
{
  "final_use_authorized": true,
  "bootstrap": {"path": "evaluation/<approved-bootstrap>.py", "sha256": "<64 hex>"},
  "runtime_lock": {"path": "evaluation/<frozen-runtime-lock>.json", "sha256": "<64 hex>"},
  "qwen_policy": {"path": "evaluation/<new-frozen-qwen-policy>.json", "sha256": "<64 hex>"},
  "source_hashes": {"<every bootstrap dependency relative path>": "<64 hex>"},
  "runner_sources": {"<every key returned by source_hashes()>": "<64 hex>"},
  "generator_identity": {
    "model_id": "<verified repository>",
    "model_revision": "<verified immutable 40-hex commit>",
    "qwen_policy_version": "<new frozen version>",
    "qwen_policy_sha256": "<same policy hash as above>"
  },
  "ordered_case_input_sha256": "<digest of the approved ordered 50 case input hashes>"
}
```

The gate verifies the approved release hash, all declared dependencies, unchanged
benchmark and execution-policy manifests/artifacts, runner sources, Qwen
`freeze_status == SUCCESS`, runtime `final_use_authorized == true`, and installed
package versions **before importing the bootstrap**. The bootstrap's
`prepare(run_id=..., resume=..., release=...)` must perform model/driver/platform
preflight before exposing any case, then return `(cases, RunConfig, Components)`.
It must supply:

- The independently frozen Qwen adapter/config/tokenizer/model/runtime, truthful
  rendered-prompt reporting, and all dependency hashes. Prospective settings alone
  are insufficient. This adapter/bootstrap must be verified using development
  material before final approval.
- Canonical `FrozenSchemaProvider` with full frozen documents and existing pinned
  retrieval resources. Expected tables must not be consulted during construction.
- `PolicyPairExecutor` with the same live read-only connection for every pair,
  `autocommit=False`, SNAPSHOT isolation, and no transaction resets.
- A release-hashed preflight callable inspecting that connection and the live
  supervisor. It must verify read-only authorization, isolation, lossless driver
  conversion, enforced 4-GiB process memory cap, and DB/transaction identity.
  Merely returning constant booleans is **not a valid live preflight**. The fake
  proof in development applies only to the in-memory fixture executor.
- Original frozen case order, approved private typed parameters and the trusted
  ordered case-input digest. Freeze/review this digest as part of release approval;
  it is not calculated from final material during this engineering task.

The runner pins and checks the preflight identity before cases, immediately before
SQL reads, and after each case. Identity changes or unsafe paths stop the whole
run. Final release integration and live platform verification remain external
prerequisites; they are not represented as completed by the development tests.

## Safe tests

```powershell
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_*.py
.venv/Scripts/python.exe -B evaluation/test_evaluation_policies.py
.venv/Scripts/python.exe -B evaluation/test_qwen_prospective.py
```

The targeted runner suite covers all requested categories, including deterministic
order, stage isolation, leakage, strict validation, continued case failures, frozen
empty comparison, Unicode serialization, no secrets, checksums, interruption,
completed-case immutability, explicit new-run requirements, frozen identities,
snapshot changes, complete-result fetching, resource censoring and summaries.
Legacy DB scripts and real model smoke scripts are excluded from offline discovery.
