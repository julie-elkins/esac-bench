# ESAC-Bench v0 specification

## Building

ESAC-Bench is an offline, provider-neutral benchmark for determining whether
an agent's completion claim is supported after interruption, recovery, or
handoff.

## Audience

The primary audience is evaluation researchers and engineers who need a
reproducible way to separate task correctness from recovery safety and evidence
quality. The secondary audience is reviewers evaluating the design of a
trustworthy-agent benchmark.

## Not building

- No provider leaderboard in v0.
- No live model calls or credentials in the reference implementation.
- No raw trajectories or provider content in the public repository.
- No replacement for Recovery-Bench, ContinuityBench, UndoBench, HSC-Bench, or
  evidence-grounded action benchmarks.
- No composite score until the dimensions and denominators have been reviewed.

## Dimensions

| Dimension | Meaning |
| --- | --- |
| Outcome | The deterministic verifier accepts the task result using the task's outcome evidence. |
| Recovery safety | Interruption or handoff does not produce duplicate or missing effects. |
| Evidence completeness | Required metadata evidence is present. |
| Claim support | The final claim is justified by the other dimensions. |

## Task contract

Each task declares:

- a stable task identifier;
- a task family;
- required evidence identifiers;
- outcome evidence identifiers;
- expected effect identifiers;
- a clean control;
- at least one controlled failure or mutation.

The benchmark reports `pass`, `fail`, and `unknown` separately. A missing
observation is never converted into a pass.

## Initial task pack

The first six synthetic tasks are:

1. coding verification after interruption;
2. tool acknowledgement loss;
3. state handoff;
4. stale evidence;
5. scientific unit contract;
6. budget-aware safe stop.

The reference profiles are deterministic evaluator controls. They demonstrate
that the benchmark catches planted failures; they do not represent model
capability.

## Acceptance criteria

The v0 contract is accepted when:

1. a fresh checkout runs offline;
2. guarded controls pass all four dimensions;
3. naive controls fail the intended dimensions;
4. controlled mutations are visible in metadata-only output;
5. calibration records remain outside native ESAC denominators;
6. public-content scans find no credentials, private data, or raw traces.

## Mutation controls

The v0 evaluator is tested with four deliberate mutations:

- `missing-evidence` removes part of a required handoff record;
- `duplicate-effect` repeats a state-changing effect after an acknowledgement
  timeout;
- `stale-state` replaces fresh evidence with a stale-source marker;
- `unsupported-success` leaves a completion claim without the required stop
  evidence.

The mutation suite passes only when each planted defect is detected in its
intended dimension. A mutation result is an evaluator control, not a model
score.

## Native report schema

Every native report declares `schema_version`, `protocol`, `data_class`,
`task_contract_ids`, `task_contract_digest`, dimension summaries, mutation
results, and a report digest. The schema validator rejects reports that
contain raw prompts, tool arguments, provider responses, trajectories, or
credentials.

## Cross-repository records

The Harbor comparison and Agent Assurance Harness records are imported through
a metadata-only adapter. The adapter returns source identifiers and counts
while preserving `native_esac_score: false`. This prevents a result from
another protocol from silently entering the ESAC denominator.

