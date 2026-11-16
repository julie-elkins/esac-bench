# ESAC-Bench

**Evidence-Supported Agent Claims Under Interruption, Recovery, and Handoff**

ESAC-Bench asks a narrower question than a normal task benchmark:

> After an agent completes, fails, resumes, or hands off a task, can its final
> claim be supported by the observed outcome, actions, and evidence records?

An **evidence-supported claim** is a completion statement that is backed by the
records required by the task contract. A task can be correct but not
evidence-supported, or well documented but incorrect. ESAC-Bench reports those
dimensions separately.

## First milestone

This repository currently contains an offline, deterministic reference
benchmark. It is intentionally provider-neutral and does not call model APIs.
The first milestone is designed to validate the scoring contract before adding
live-agent adapters or provider cost.

The native suite includes six synthetic task contracts covering:

- coding verification after an interruption;
- tool acknowledgement loss and duplicate-effect prevention;
- state handoff between agents;
- stale or conflicting evidence;
- a scientific unit contract;
- budget-aware safe stopping.

Each task has a clean reference path and a controlled failure path. The
reference profiles are not model scores: they are evaluator controls that prove
the benchmark catches planted failures.

## Run it

From the repository root:

```bash
PYTHONPATH=src python -m esac_bench
PYTHONPATH=src python -m esac_bench --json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The output is metadata-only. It includes task identifiers, profile names,
dimension statuses, counts, and report digests. It does not include prompts,
tool payloads, provider output, credentials, or raw trajectories.

## Metrics

- **Outcome** — whether the task verifier accepted the result.
- **Recovery safety** — whether the agent avoided duplicate or missing effects
  after interruption or handoff.
- **Evidence completeness** — whether every required evidence identifier was
  observed.
- **Claim support** — whether the reported completion claim is justified by
  the other dimensions.

The benchmark does not collapse those into one score in the first milestone.
That preserves the failure mode the benchmark is intended to reveal: a correct
answer is not automatically a supportable claim.

## Mutation controls

The offline runner inserts four deliberate defects into guarded results:
missing evidence, duplicate effects, stale state, and unsupported success.
The mutation suite must detect each defect in the intended dimension. This is
evaluator validation, not an agent leaderboard.

## Report contract

Native reports carry a schema version and a digest of the task contracts used
to produce them. The validator refuses raw prompts, tool arguments, provider
responses, trajectories, and credentials. Public results from related
repositories are loaded through a separate calibration adapter and remain
explicitly outside native ESAC denominators.

## CI gate

The pull-request workflow runs without provider credentials or network calls. It
checks the unit suite, native schema, mutation controls, metadata boundaries,
and the cross-repository integration smoke. The smoke imports the committed
Harbor and assurance-lab records and verifies that they remain calibration
data—not native ESAC scores.

The first provider-specific integration is a safe Harbor/mini-swe-agent
dry-run adapter. It validates command shape and evidence boundaries without
reading credentials, starting Finch or Docker, contacting a provider, or
claiming a benchmark observation. See
[`docs/harbor-dry-run-adapter.md`](docs/harbor-dry-run-adapter.md) and the
provider-neutral [`docs/live-adapter-contract.md`](docs/live-adapter-contract.md).

The repository also contains a bounded live worker for one explicitly approved
Harbor smoke. It is not a leaderboard adapter: it reports execution and
evidence metadata, while native task correctness remains unknown until the
receipt is evaluated. See
[`docs/harbor-live-adapter.md`](docs/harbor-live-adapter.md).

## Existing research used as calibration

The public Harbor study and Agent Assurance Harness are connected as
calibration sources, not silently merged into native ESAC results. See
[`docs/calibration-policy.md`](docs/calibration-policy.md) and
[`data/legacy-calibration.json`](data/legacy-calibration.json).

The earlier matched Harbor comparison reported Codex at 10/10 clean executions
and 7/10 benchmark passes, and mini-swe-agent at 9/10 clean executions and
6/10 benchmark passes. Those values remain labeled as results from the earlier
Harbor protocol. They are not an ESAC-Bench score.

## What this is not

ESAC-Bench is not a replacement for Recovery-Bench, ContinuityBench,
UndoBench, HSC-Bench, or evidence-grounded action benchmarks. Its proposed
contribution is a portable assurance layer that asks whether the final claim
remains supportable across outcome, recovery, and evidence dimensions.

## Status

The repository is an early public research prototype. The native offline
contract is the source of truth for ESAC-Bench results. A single bounded live
smoke is now supported for execution-plumbing validation. The selected
`regex-log` success-path diagnostic completed with a benchmark pass, but it
remains calibration evidence outside native ESAC denominators. A leaderboard
and composite score remain out of scope until live evidence and task
evaluation have been independently reviewed.

