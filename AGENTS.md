# ESAC-Bench repository instructions

## Purpose

ESAC-Bench is a public, provider-neutral benchmark for testing whether an
agent's reported result is supported by its outcome, recovery behavior, and
metadata-only evidence.

## Public data boundary

- Keep fixtures synthetic or already public.
- Never add credentials, raw provider responses, prompts, tool arguments, raw
  trajectories, private logs, or unpublished assessment content.
- Calibration records may cite public repositories and published study results,
  but they are not ESAC-Bench scores unless produced under the ESAC protocol.
- Native reports contain identifiers, statuses, counts, digests, and bounded
  limitations only.

## Reliability contract

The benchmark keeps these dimensions separate:

- `outcome`: whether the deterministic task verifier accepted the result;
- `recovery_safety`: whether interruption or handoff caused duplicate or
  missing side effects;
- `evidence_completeness`: whether required metadata evidence was present;
- `claim_support`: whether the final claim is supported by the other three
  dimensions.

An absent event is not evidence that a check passed. Unknown and refused are
not passing results.

## Development

Use the standard-library runner and tests before committing:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python -m esac_bench --json
```

Run commands from the repository root with `PYTHONPATH=src` when the package is
not installed.

Stage one path per `git add` command. Never use blanket staging.

