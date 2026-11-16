# Calibration and provenance policy

**Provenance** means the record of where a result came from and which protocol
produced it. ESAC-Bench keeps provenance explicit because earlier results are
useful evidence without being interchangeable scores.

## Native ESAC results

Only runs produced with the `esac-offline-v0` or a later declared ESAC protocol
belong in native ESAC denominators. They must use the task contract, dimension
definitions, evidence rules, and report schema in this repository.

## Legacy calibration

Public results from the Harbor adapter and the Agent Assurance Harness may be
summarized as calibration evidence. Calibration means an external result used
to motivate or check a benchmark design; it is not a result from this
benchmark.

The calibration record must include:

- source repository;
- source report or study identifier;
- source protocol;
- bounded public metrics;
- what the result supports;
- what it does not support.

## Diagnostic case studies

Raman unit-contract and QEMU compatibility findings belong in a separate
diagnostic lane. They explain why task contracts and environment controls are
needed, but they are not additional native tasks or causal proof.

## Public boundary

Keep raw trajectories, prompts, provider responses, credentials, private logs,
and local paths outside this repository. A public calibration record may retain
only identifiers, counts, statuses, dates, digests, and limitations.

