# ESAC-Bench build log

This log records decisions that affect benchmark interpretation. It is
deliberately separate from the implementation so a reviewer can audit the
research choices without reading source code.

## Phase 1 — offline contract and calibration boundary

### Decided

Create a new public repository with a provider-neutral offline v0. Use public
Harbor and Agent Assurance Harness results as labeled calibration and diagnostic
evidence, not as native ESAC-Bench scores.

### Instead of

Extending an existing repository with a mixed-purpose benchmark, importing
earlier provider runs into the ESAC denominator, or starting with live-provider
execution.

### Why

The benchmark needs one source of truth for its task contracts and metrics.
Earlier runs used a different protocol, and the existing synthetic harness
provides reusable evidence-contract patterns. An offline first milestone tests
the scoring logic without provider spend, credentials, model drift, or
environment instability.

### Costs if wrong

A separate repository adds maintenance work. Calibration records could confuse
readers if their protocol boundary is missed, and the offline controls do not
yet demonstrate live-agent behavior. The repository labels those limitations
explicitly.

### Decided by

Julie, following the recommended scope on 2026-11-16.

### Verification

- Six synthetic task contracts are present.
- Guarded and naive reference controls run without provider calls.
- Native reports contain metadata only.
- Calibration records state `native_esac_score: false`.
- Four unit tests pass.
- The CLI reports all four dimensions separately.

## Phase 2 — evaluator mutation controls

### Decided

Add four deterministic mutations to the offline runner before any live adapter:
missing evidence, duplicate effects, stale state, and unsupported success.

### Instead of

Treating the guarded reference profile as proof that the evaluator works, or
testing only positive examples.

### Why

An evaluator can report a clean result while missing the failure it was meant
to catch. Controlled mutations make the expected negative direction explicit
and keep this validation independent of provider behavior.

### Costs if wrong

The mutation suite adds a small maintenance burden and does not prove live-agent
quality. It does establish that the current evaluator catches the declared
failure classes.

### Decided by

Julie and Codex, following the approved ESAC-Bench scope on 2026-11-16.

## Phase 3 — native schema and cross-repository adapters

### Decided

Add a versioned metadata-only native report schema and separate adapters for
public Harbor calibration records and diagnostic case studies.

### Instead of

Parsing arbitrary external reports into native ESAC results, accepting raw
trajectories as an interchange format, or comparing reports without binding
them to the task-contract digest.

### Why

A schema version and task-contract digest make the benchmark result
interpretable later. Separate adapters preserve provenance and prevent earlier
protocols from entering native ESAC denominators.

### Costs if wrong

The schema will need a compatibility policy when the benchmark evolves, and
external reports require explicit adapter maintenance. Those costs are smaller
than silently comparing incompatible measurements.

### Decided by

Julie and Codex on 2026-11-16.

## Phase 4 — CI contract gate and integration smoke

### Decided

Add a no-provider CI gate that runs the unit suite, validates the native report,
checks the mutation suite, and imports the committed Harbor and assurance-lab
metadata through an offline integration smoke.

### Instead of

Cloning external repositories during CI, calling provider APIs, or making a
network-dependent benchmark result part of pull-request validation.

### Why

The gate must be deterministic and safe to run on every change. The smoke still
tests the cross-repository boundary by exercising the same adapters and
committed public metadata that future external checkouts will produce.

### Costs if wrong

The smoke cannot detect a changed upstream repository until its metadata export
is refreshed. A later live adapter will require a separate, explicitly bounded
workflow.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- The native report gate passes with schema version `esac-report-v0`.
- The mutation suite passes with four detected controls.
- The cross-repository smoke imports two calibration sources and two diagnostic
  cases.
- The smoke confirms `native_esac_score: false`.
- The workflow uses a pinned official checkout action and read-only contents
  permissions.

## Phase 5 — live-agent adapter contract

### Decided

Define a provider-neutral, dry-run-capable adapter contract before adding a
provider SDK or live execution. Require bounded runtime, attempts, output,
preflight spend, tool scope, contract digests, and human approval.

### Instead of

Adding a live provider command first, allowing automatic retries, or exposing
raw trajectories through the public benchmark report.

### Why

The adapter is the boundary where credentials, provider cost, timeouts, and
side effects become possible. A typed request and result make those controls
testable before a paid run.

### Costs if wrong

The first live adapter will require explicit provider-specific implementation
work, and no live benchmark score is produced by this phase. That delay is
intentional because a missing stop condition can spend money without producing
interpretable evidence.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- Fourteen unit tests pass.
- Live requests require explicit human approval and bounded runtime, attempts,
  output, spend, tools, and contract digests.
- Dry-run requests reject credential-variable names.
- Metadata-only adapter results validate successfully.
- No provider SDK, credential read, network call, or paid run was added.

## Phase 6 — Harbor mini-swe-agent dry-run adapter

### Decided

Add a provider-specific Harbor/mini-swe-agent adapter that constructs a
shell-free command plan and returns an explicitly not-executed result.

### Instead of

Starting Finch, reading an Anthropic credential, invoking Harbor, or treating a
constructed command as a benchmark observation.

### Why

The dry-run adapter exercises the real path and receipt naming while keeping
provider cost, credentials, and environment failures outside the contract
test. It also proves that a result can say `unknown` and `not_observed`
instead of implying success.

### Costs if wrong

The adapter does not yet prove live-provider behavior and adds one
provider-specific contract to maintain. That is preferable to spending credits
before the command, path, and evidence boundaries are tested.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- The dry-run tool emits a shell-free `harbor run` argument vector.
- Credential access is false and no provider or container runtime is called.
- The result reports `status: unknown`, `native_outcome: not_observed`, and no
  receipt digest.
- Traversal paths are refused.
- The CI workflow runs the dry-run adapter.

## Phase 7 — bounded Harbor live worker

### Decided

Implement one supervised `mini-swe-agent` Harbor worker behind the approved
adapter contract. Keep the provider receipt, ESAC metadata receipt, and raw
process output in separate ignored local paths.

### Instead of

Overwriting Harbor's receipt with benchmark metadata, forwarding the entire
shell environment, allowing automatic retries, or exposing a live command in
CI.

### Why

The provider receipt is the raw evidence artifact, while the ESAC receipt is a
metadata-only interpretation. Separating them preserves the evidence needed
for audit without making raw provider material part of the public benchmark.
The explicit approval flag and one-attempt limit keep a first smoke from
becoming an unattended spend loop.

### Costs if wrong

The first worker supports only one bounded smoke and reports native task
correctness as unknown until a separate evaluator consumes the local receipt.
It also requires a supervised operator and does not provide a leaderboard
score.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- Nineteen unit tests pass.
- Missing credentials, unsafe output paths, timeouts, output caps, and provider
  receipt preservation are covered by synthetic tests.
- The worker uses `shell=False`, a minimal child environment, one attempt, and
  process-group termination on timeout.
- The dry-run, native contract gate, and cross-repository smoke still pass.
- No provider call or paid run was made.

## Phase 8 — Harbor wrapper command alignment

### Decided

Allow the live worker to receive an explicit shell-free runner prefix so the
Harbor repository can invoke its validated `uv run harbor-assurance run`
wrapper instead of treating the wrapper TOML as raw Harbor job configuration.

### Instead of

Calling raw `harbor run --config` with the adapter repository's TOML, or
silently translating the configuration into a second command format.

### Why

Raw Harbor accepts its own YAML/JSON job schema, while this project’s TOML is
owned by the Harbor Assurance Adapter wrapper. Using the wrapper preserves the
existing credential transport, Docker shim, bounded process capture, and
metadata receipt behavior.

### Costs if wrong

The live worker now has one additional command-prefix parameter to validate.
The first smoke remains specific to this Harbor wrapper and is not yet a
portable raw-Harbor adapter.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- Harbor help confirms raw `harbor run --config` expects Harbor YAML/JSON.
- The wrapper help confirms `uv run harbor-assurance run --config ... --receipt ...`.
- Nineteen ESAC unit tests pass after the change.
- No provider call or paid run was made.

## Phase 9 — selected regex-log clean-completion diagnostic

### Decided

Record `esac-harbor-live-regex-log-v1` as a clean success-path diagnostic:
one completed execution, one successful trial, one benchmark pass, and a
present validated trajectory. Keep it outside the native ESAC denominator and
any leaderboard-style comparison.

### Instead of

Treating the adapter metadata result's `native_outcome: unknown` as a task
failure, adding this one-task result to native ESAC metrics, or spending more
credits on another live smoke immediately.

### Why

The provider receipt records `benchmark_status: passed`,
`benchmark_score: 1.0`, `runner_successful_trials: 1`, and no errored trials.
ATIF v1.2 metadata validation passed with 18 steps and 16 tool calls. The
observed provider cost was `$0.40285075`, and the run completed in about 288
seconds. The outer adapter intentionally records execution and evidence
plumbing; receipt evaluation records native task correctness.

### Costs if wrong

Calling this a general reliability result would overstate evidence from one
selected task. Calling it a native ESAC score would mix protocols and make the
denominator misleading. The bounded diagnostic therefore supports only the
claim that this selected success path completed with complete metadata
evidence.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- Outer metadata: `status: completed`, `evidence_status: complete`, and
  `trajectory_status: present`.
- Provider receipt: `status: completed`, `benchmark_status: passed`,
  `benchmark_score: 1.0`, and `runner_errored_trials: 0`.
- No raw trajectory, prompt, provider response, credential, or local path was
  added to the public repository.

## Phase 10 — offline Harbor receipt evaluator

### Decided

Add a metadata-only Harbor receipt evaluator that maps one reviewed
`receipt-v1` record to `pass`, `fail`, `unknown`, or `not_observed` without
reading raw provider content.

### Instead of

Treating Harbor process completion as a benchmark pass, manually interpreting
each receipt, or importing raw trajectories into ESAC-Bench.

### Why

The live adapter correctly separates execution evidence from native task
correctness, but its outer result remains `native_outcome: unknown` until a
receipt evaluator performs the second step. The evaluator closes that gap
while preserving the public metadata boundary: `pass` requires clean
execution, a passed benchmark status, and complete validated trajectory
metadata.

### Costs if wrong

A strict allow-list can reject a future Harbor metadata field until the
receipt contract is reviewed. That is safer than silently accepting provider
content or treating an unreviewed field as evidence. The evaluator also
supports one receipt at a time; it does not create a cohort score.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- The synthetic receipt evaluator returns `native_outcome: pass`.
- The actual local `regex-log` receipt returns `native_outcome: pass`,
  `evidence_status: complete`, and `trajectory_status: present`.
- Timeouts return `not_observed`; incomplete evidence returns `unknown`.
- Raw content, unknown fields, and invalid metadata types are refused.
- Twenty-nine unit tests pass, the native CI gate passes, and the evaluator
  runs in the CI workflow without provider access.

## Phase 11 — refreshed-key regex-log replication

### Decided

Record `esac-harbor-live-regex-log-v2` as a second clean replication of the
explicitly selected `regex-log` diagnostic. Keep the two one-task runs outside
native ESAC and leaderboard-style denominators.

### Instead of

Treating the refreshed credential as evidence of model improvement, adding the
two one-task passes to the matched cohort, or running another repeat without a
new research question.

### Why

The v2 provider receipt records one completed trial, one benchmark pass, ATIF
v1.2 validation, complete trajectory metadata, and observed cost
`$0.45102025`. The earlier v1 receipt also passed with observed cost
`$0.40285075`. The two runs confirm that the refreshed credential supports the
bounded success path, while different runtimes and trajectories are expected
run variation rather than a controlled model change.

### Costs if wrong

Calling two passes on one task general reliability evidence would overstate the
sample. Stopping here leaves ten-task performance under the refreshed
credential unmeasured, but avoids spending more without a pre-specified
question and preserves the study's denominator discipline.

### Decided by

Julie and Codex on 2026-11-16.

### Verification

- v2 outer metadata: `status: completed`, `evidence_status: complete`, and
  `trajectory_status: present`.
- v2 evaluated outcome: `pass`; benchmark score `1.0`.
- v1 and v2: two completed executions, two successful trials, two benchmark
  passes.
- No raw receipt, trajectory, prompt, provider response, or credential was
  added to the public repository.

## Phase 20 — add the ESAC-Bench Recovery Track

### Decided

Add a separate native `recovery-v0` track with seven synthetic recovery cases:
before-side-effect, after-side-effect-before-ack, retry-after-timeout,
destructive-action-restore, stale-checkpoint, handoff-during-recovery, and
incomplete-recovery-evidence. Report final-state restoration, side-effect
integrity, recovery-evidence completeness, and bounded recovery separately.

### Instead of

Adding recovery cases to the existing six-task denominator, importing real
Harbor or Agent Assurance Harness recovery records as native scores, or
executing destructive actions to make the benchmark appear more realistic.

### Why

The recovery post's central question—whether a system can return to a safe,
known state after interruption—requires more than a generic recovery-safety
dimension. A named track makes the failure points and acceptance conditions
reviewable while preserving the original core-task comparisons. Synthetic
controls provide repeatable evaluator evidence without provider cost or
operational risk.

### Costs if wrong

The track may not predict production disaster recovery; it is an offline
benchmark control, not a deployment rehearsal. Keeping that limitation visible
is safer than implying that seven synthetic cases prove operational resilience.

### Decided by

Julie and Codex on 2026-11-18.

### Verification

- Guarded recovery controls pass all four recovery metrics across all seven
  cases.
- Naive controls expose distinct state, side-effect, and evidence failures.
- The core task count remains six, and the Recovery Track reports seven cases
  separately.
- No provider API, credential, destructive action, raw trajectory, or raw
  provider content is used.

