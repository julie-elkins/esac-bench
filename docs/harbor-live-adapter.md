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
