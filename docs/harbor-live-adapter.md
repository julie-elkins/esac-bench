# Bounded Harbor live adapter

The live adapter runs one approved `mini-swe-agent` task through Harbor. It is
an execution-plumbing smoke, not a leaderboard run: `native_outcome` remains
`unknown` until the local receipt is evaluated by the ESAC evaluator.

## Safety gates

The adapter refuses before credential access when:

- the request lacks explicit approval;
- the attempt limit is not exactly one;
- a config, receipt, or output path escapes the workspace;
- any evidence path is outside ignored `runs/` or `jobs/`;
- the credential variable is absent;
- the Harbor configuration is missing;
- an output path already exists.

The worker uses `shell=False`, forwards only runtime essentials plus the
allow-listed credential, kills the process group on timeout, and writes the
metadata-only ESAC receipt separately from Harbor's raw local receipt.

The spend ceiling is a local preflight bound, not a provider billing guarantee.
The first smoke must remain supervised.

## Preflight

Run the dry-run adapter first:

```bash
PYTHONPATH=src python3 tools/harbor_dry_run.py
```

Then verify the selected Harbor config is one public task, Finch or Docker is
running, the credential is present, and the receipt paths are new. Do not place
raw receipts or process output anywhere except `runs/` or `jobs/`.

## Supervised smoke command

The command below is a template. Replace the task, model, digests, and config
with the reviewed values for the one-task smoke. The approval flag is the
human gate immediately before the provider call.

```bash
PYTHONPATH=src python3 tools/harbor_live_smoke.py \
  --run-id esac-harbor-live-smoke-v1 \
  --task-id coding-interruption \
  --model claude-opus-4-6 \
  --config config/mini-swe-agent-live-2.0.toml \
  --receipt runs/esac-harbor-live-smoke-v1.provider.json \
  --metadata-receipt runs/esac-harbor-live-smoke-v1.esac.json \
  --raw-output runs/esac-harbor-live-smoke-v1.output.log \
  --task-contract-digest REPLACE_WITH_REVIEWED_SHA256 \
  --evidence-contract-digest REPLACE_WITH_REVIEWED_SHA256 \
  --stop-condition "stop after one task, one attempt, or any refusal" \
  --max-runtime-seconds 900 \
  --output-cap-bytes 1000000 \
  --spend-ceiling-usd 5 \
  --runner-prefix uv run harbor-assurance run \
  --approve-live-run
```

The command prints only the metadata result. Inspect the local raw receipt and
output separately; never copy them into this public repository.

## Result interpretation

- `completed` means Harbor exited successfully, not that the task passed.
- `failed` means Harbor returned a non-zero exit or exceeded the output cap.
- `timed_out` means the declared runtime bound stopped the process group.
- `refused` means the adapter did not start a provider call.
- `evidence_status: incomplete` means the expected Harbor receipt was absent
  or empty.

## Recorded success-path diagnostic

The supervised `esac-harbor-live-regex-log-v1` and `v2` diagnostics each
completed the same explicitly selected public task. Both metadata-only
provider receipts record one successful execution,
`benchmark_status: passed`, `benchmark_score: 1.0`, complete ATIF v1.2
metadata, and a present trajectory. The observed provider costs were
`$0.40285075` and `$0.45102025`; the combined result is 2/2 passes on one
task.

This is a replicated calibration diagnostic, not a native ESAC score or
leaderboard observation. The outer ESAC metadata receipts remain
`native_outcome: unknown` by design until a separate receipt evaluator
interprets native task correctness. The replication does not establish
general reliability or model improvement. Raw receipts and trajectories remain
local and are not part of this repository.

The offline evaluator is available for that second step:

```bash
PYTHONPATH=src python3 tools/evaluate_harbor_receipt.py \
  --receipt /path/to/local/provider-receipt.json
```

It returns `pass` only when the receipt shows clean execution, a passed
benchmark status, and complete validated evidence. A clean benchmark failure
returns `fail`; timeouts, refusals, missing outcomes, and incomplete evidence
remain `not_observed` or `unknown`. Unsupported fields and raw content are
refused.
