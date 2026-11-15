# Submission contents

The repository is the submission; no local virtual environment or prebuilt index is required.

## Required implementation and report

- `hw4.py`: the five student functions and their helpers; the provided section remains logically unchanged.
- `requirements.txt`: installation dependencies; `requirements-lock.txt` records the tested versions.
- `evaluate.py` and `update_report.py`: reproducible ablations and report refresh.
- `README.md`: Homework 4 solution, pipeline, measured ablations and error analysis.
- `REFLECTION.md`: Task 6, preserved in the student's currently selected AI-assisted draft form.
- `public_test/`: the original public data supplied with the starter repository.

## Results and verification evidence

- `results.csv`: the final official public-set run.
- `experiments/full/`, `experiments/offline/`, `experiments/official/`: per-question answers, evidence, summaries and official logs.
- `experiments/reuse-validation.json`: exact-input proof for unchanged historical ablation rows; their original hashes and times are preserved.
- `test_hw4.py`, `test_robustness.py`: 19 focused regression and robustness tests.
- `AUDIT_REPORT.md` and selected `audit/` records: audit findings, clean-install verification and pre-audit baseline evidence. Historical audit statements describe the state before staging and submission.

## Configuration

- `.env.example`: placeholder only, never a real credential.
- `.gitignore`: excludes credentials, virtual environments, caches, serialized indexes and local-only duplicate review artifacts.
- `.gitattributes`: preserves exact bytes for hash-checked implementation and evidence files. This prevents Git's automatic newline conversion from invalidating reproducibility hashes.

Excluded from submission: `.env`, API keys, `.venv/`, `__pycache__/`, Python bytecode, cache directories, `*.pkl`, `*.pickle`, `*.faiss`, `*.index`, local duplicate experiment backups and the assignment PDF. They are not deleted from the local working directory.

Run `python -m unittest -v test_hw4 test_robustness` and `python hw4.py --data-folder public_test --output results.csv` in an environment installed from `requirements.txt`; the official run needs a locally configured DeepSeek API key.
