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

