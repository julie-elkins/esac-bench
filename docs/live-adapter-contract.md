# Live-agent adapter contract

This document defines the boundary for a future live-agent adapter. It does
not enable a provider or authorize a paid run.

## Dependency graph

```text
human approval
      |
      v
request validator -> bounded provider worker -> metadata receipt
      |                    |                    |
      +--------------------+--------------------+
                           v
                    ESAC evaluator
```

The edges are sequential. The validator must succeed before a provider
credential is read. The provider worker owns one responsibility: execute one
bounded task. The evaluator owns a different responsibility: interpret the
metadata receipt against the ESAC task and evidence contracts.

## Request contract

Each execution declares:

- stable run, adapter, provider, model, and task identifiers;
- `dry_run` or `live` mode;
- the name of an allow-listed credential environment variable, never its value;
- maximum runtime, attempts, output bytes, and a preflight spend ceiling;
- a plain-language stop condition;
- the bounded tool scope;
- task-contract and evidence-contract digests;
- explicit human approval.

The spend ceiling is a local preflight stop condition, not a provider billing
guarantee. The adapter must refuse before credential access when the request is
missing a bound or human approval.

## Result contract

The adapter returns only:

- terminal status;
- claim state;
- native task outcome;
- evidence and trajectory status;
- return code and elapsed time;
- observed cost when available;
- receipt digest and limitation.

Raw prompts, tool arguments, provider responses, and trajectories remain in a
local ignored run workspace. They never enter the public result.

## Failure rules

- A refusal is a structured result with `error`, `message`, and `guidance`.
- A timeout is not a benchmark failure; it is an execution result that remains
  outside the clean-observation denominator.
- Missing evidence is not evidence of success.
- A provider result cannot override a failed schema or evidence check.
- The first live implementation must make no automatic retries. Retry policy
  is a later experiment because retries can duplicate side effects.

## Human gate

The first live adapter requires human approval immediately before a paid run.
The approval must name the provider, model, task count, attempt limit, runtime
bound, output cap, spend ceiling, and stop condition.

## Not established yet

- provider-specific command lines;
- model-quality results;
- a billing guarantee;
- safe automatic retries;
- a live leaderboard score.
