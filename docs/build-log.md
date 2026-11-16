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

