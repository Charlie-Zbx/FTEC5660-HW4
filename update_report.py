"""Refresh the measured section of README from saved, reproducible experiment results."""
import csv
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
code_hash = hashlib.sha256((root / "hw4.py").read_bytes()).hexdigest()


def verified_reuse(mode, name, summary):
    """Accept historical answers only with an exact, source-bound context comparison."""
    path = root / 'experiments' / 'reuse-validation.json'
    if mode != 'full' or not path.exists():
        return False
    item = json.loads(path.read_text(encoding='utf-8')).get(name, {})
    if item.get('validated_for_hw4_sha256') != code_hash or item.get('original_hw4_sha256') != summary['hw4_sha256']:
        return False
    for relative, expected in item.get('artifact_hashes', {}).items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            return False
    if len(item.get('artifact_hashes', {})) != 4:
        return False
    old = json.loads((root / 'experiments/full' / name / 'details.json').read_text(encoding='utf-8'))
    new = json.loads((root / 'experiments/offline' / name / 'details.json').read_text(encoding='utf-8'))
    return old.keys() == new.keys() and all(
        all(old[q][field] == new[q][field] for field in ('question', 'parsed', 'chunks')) for q in old)


lines = []
for mode in ("offline", "full"):
    summaries = []
    for name in ("B0", "V1", "V2", "V2H", "V3", "V4", "V5", "V6"):
        path = root / "experiments" / mode / name / "summary.json"
        if path.exists():
            summary = json.loads(path.read_text(encoding="utf-8"))
            if summary["hw4_sha256"] != code_hash and not verified_reuse(mode, name, summary):
                raise SystemExit(f"Stale {mode}/{name} results: rerun affected experiments first.")
            if summary["evaluator_sha256"] != hashlib.sha256((root / "evaluate.py").read_bytes()).hexdigest():
                raise SystemExit(f"Stale {mode}/{name} evaluation configuration: rerun experiments first.")
            summaries.append(summary)
    if not summaries:
        continue
    lines += [f"#### Measured {mode} results", "",
              "| Variant | Recall@5 | Kept | Rejected | Answer accuracy | Seconds |",
              "|---|---:|---:|---:|---:|---:|"]
    for s in summaries:
        accuracy = "Not run" if s["accuracy"] is None else f"{s['accuracy']:.1%}"
        lines.append(f"| {s['variant']} | {s['recall']:.1%} | {s['kept']:.1%} | {s['rejected']:.1%} | {accuracy} | {s['seconds']:.2f} |")
    lines += ["", f"Source: `experiments/{mode}/<variant>/results.csv` and `summary.json`. "
              "Times include loading, indexing and retrieval; full-mode times also include generation. "
              "Offline times exclude generation and do not verify the official end-to-end time limit.", ""]
    if mode == 'full' and any(s['hw4_sha256'] != code_hash for s in summaries):
        lines += ['B0, V1, V2, V2H and V3 retain their actual pre-audit answers and measured times: the evaluator is unchanged, and all 60 questions, parses and ordered source chunks match the current offline run exactly. Original source hashes are preserved. `experiments/reuse-validation.json` records the checked artifacts. V4--V6 were rerun after the audit; historical measurements are not relabelled as new runs.', '']
    if mode == "offline":
        for previous, current in zip(summaries, summaries[1:]):
            delta = 100 * (current["recall"] - previous["recall"])
            lines.append(f"- {current['variant']} relative to {previous['variant']}: recall changes by {delta:+.1f} percentage points; "
                         f"kept changes from {previous['kept']:.1%} to {current['kept']:.1%}, "
                         f"and rejected from {previous['rejected']:.1%} to {current['rejected']:.1%}.")
        lines.append("")
    final = next((s for s in summaries if s["variant"] == "V6"), None)
    if final:
        lines += [f"Final helper checks: table score {final['table_score']:.1%}; document pass rate "
                  f"{final['document_pass']:.1%}; query-field accuracy {final['parse_score']:.1%}; "
                  f"valid nonempty retrieval {final['valid_nonempty']:.1%}; "
                  f"retrieval exceptions {final['retrieval_errors']}; generator exceptions {final['generator_errors']}.", ""]
        with (root / "experiments" / mode / "V6" / "results.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        misses = [r for r in rows if r["retrieval_hit"] == "False"]
        lines += ["Final retrieval misses: " + (", ".join(r["id"] for r in misses) if misses else "none on this public run") + ".", ""]
if not (root / "experiments/full/V6/summary.json").exists():
    lines += ["**Incomplete verification:** the full generator evaluation and full ablation accuracy have not been run. "
              "No final `results.csv` from the official runner or Task 4 score is claimed.", ""]
readme = root / "README.md"
text = readme.read_text(encoding="utf-8")
before, rest = text.split("<!-- MEASURED_RESULTS -->", 1)
_, after = rest.split("<!-- END_MEASURED_RESULTS -->", 1)
readme.write_text(before + "<!-- MEASURED_RESULTS -->\n" + "\n".join(lines) + "\n<!-- END_MEASURED_RESULTS -->" + after, encoding="utf-8")
print("README measurements refreshed from saved results.")
