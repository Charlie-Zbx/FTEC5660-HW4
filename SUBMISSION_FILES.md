# Repository contents

This document lists the implementation, report and supporting experiment records. Indexes are built from the supplied corpus at runtime.

## Implementation and report

- `hw4.py`: the five student functions and their helpers; the provided section remains logically unchanged.
- `requirements.txt`: installation dependencies; `requirements-lock.txt` records the tested versions.
- `evaluate.py` and `update_report.py`: reproducible ablations and report refresh.
- `README.md`: Homework 4 solution, pipeline, measured ablations and error analysis.
- `REFLECTION.md`: Task 6, personal reflection.
- `public_test/`: the original public data supplied with the starter repository.

## Results and verification evidence

- `results.csv`: the final official public-set run.
- `experiments/full/`, `experiments/offline/`, `experiments/official/`: per-question answers, evidence, summaries and official logs.
- `experiments/reuse-validation.json`: exact-input proof for unchanged historical ablation rows; their original hashes and times are preserved.
- `test_hw4.py`, `test_robustness.py`: 19 focused regression and robustness tests.
- `AUDIT_REPORT.md` and `audit/`: technical verification, clean-install results and the earlier implementation baseline. Raw logs and JSON records preserve the environment and repository state at the time of each check; fields about staging or reflection hashes are historical metadata, not the current submission status.

## Configuration

- `.env.example`: placeholder only, never a real credential.
- `.gitignore`: excludes credentials, virtual environments, caches, serialized indexes and local-only duplicate review artifacts.
- `.gitattributes`: preserves exact bytes for hash-checked implementation and evidence files. This prevents Git's automatic newline conversion from invalidating reproducibility hashes.

Excluded from version control: `.env`, API keys, `.venv/`, `__pycache__/`, Python bytecode, cache directories, `*.pkl`, `*.pickle`, `*.faiss`, `*.index`, duplicate local experiment backups and the assignment PDF.

Installation and execution commands are documented in [README.md](README.md#setup-and-execution).
