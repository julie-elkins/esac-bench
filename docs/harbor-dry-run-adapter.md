# Harbor mini-swe-agent dry-run adapter

This adapter is the first provider-specific integration for ESAC-Bench. It
constructs the Harbor command for a mini-swe-agent task but does not execute it.

## Run

```bash
PYTHONPATH=src python3 tools/harbor_dry_run.py
```

The result must show:

- an argument vector beginning with `harbor run`;
- `shell: false`;
- `credential_access: false`;
- an `unknown` execution status;
- `not_observed` benchmark outcome;
- no receipt digest or trajectory claim.

## Why this boundary exists

The command shape is real enough to test path handling and receipt naming, but
the adapter does not yet read `ANTHROPIC_API_KEY`, start Finch or Docker, call
Harbor, or contact Anthropic. A dry run is not evidence that the agent works;
it is evidence that the adapter has constructed a bounded plan.

## Live worker boundary

The bounded live worker is now implemented separately from this dry-run
planner. It must:

1. call `validate_request` before reading a credential;
2. use the validated argument vector with `shell=False`;
3. enforce the declared timeout, output cap, attempt limit, and stop condition;
4. write a metadata-only receipt;
5. pass the receipt through the ESAC evaluator;
6. report refusal, timeout, missing evidence, and provider failure separately.

See [`docs/harbor-live-adapter.md`](harbor-live-adapter.md) for the supervised
one-task smoke procedure. The dry-run remains the required preflight check.
