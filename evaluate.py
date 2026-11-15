"""Reproducible ablations; gold labels are read ONLY by this offline evaluator.

python evaluate.py --offline
python evaluate.py                 # paid calls to the unchanged provided generator
python evaluate.py --variants V6 --offline
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hw4 as hw

VARIANTS = {
    "B0": "Naive text + recursive splitter + whitespace BM25 top-5",
    "V1": "B0 + table_to_text",
    "V2": "V1 + paragraph/table-row chunking",
    "V2H": "V2 + source-derived contextual headers",
    "V3": "V2H + query parsing and company/type/year filtering",
    "V4": "V3 + per-company evidence allocation",
    "V5": "V4 + normalized evidence coverage and row-label ranking",
    "V6": "V5 + lexical abstention",
}


def make_chunks(corpus, variant):
    chunks, by_file = [], {}
    for name, html in corpus.items():
        if variant not in {"B0", "V1"}:
            current = hw.chunk_document(name, html)
            if variant == "V2":
                current = [hw.Document(page_content=c.page_content.split("\n", 1)[1],
                                       metadata=c.metadata.copy()) for c in current]
        else:
            soup = BeautifulSoup(html, "html.parser")
            metadata = hw._metadata(name, soup)
            if variant == "V1":
                for table in soup.find_all("table"):
                    table.replace_with(hw.table_to_text(str(table)))
            # Same splitter and text extraction in B0 and V1: only table conversion changes.
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            current = [hw.Document(page_content=t, metadata=metadata.copy())
                       for t in splitter.split_text(soup.get_text())]
        chunks.extend(current)
        by_file[name] = current
    return chunks, by_file


def get_chunks(index, question, variant):
    if variant in {"B0", "V1", "V2", "V2H"}:
        if not index["chunks"]:
            return []
        scores = index["bm25"].get_scores(question.lower().split())
        ids = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:5]
        return [index["chunks"][i] for i in ids]
    return hw._retrieve(index, question, filtering=True, balanced=variant in {"V4", "V5", "V6"},
                        evidence_rank=variant in {"V5", "V6"}, abstention=variant == "V6")


def evaluate(folder, variant, offline, output):
    started = time.perf_counter()
    corpus = hw.load_corpus(folder / "corpus")
    questions = hw.load_json(folder / "questions.json")
    gold = hw.load_json(folder / "ground_truth.json")
    docs = hw.load_json(folder / "docs.json")
    tables = hw.load_json(folder / "tables.json")
    if not gold:
        raise ValueError("This evaluator needs labelled data; use hw4.py for unlabelled corpora.")
    chunks, by_file = make_chunks(corpus, variant)
    index = hw.build_index(chunks)
    indexing = time.perf_counter() - started
    parsed, retrieved, errors = {}, {}, {}
    for qid, question in questions.items():
        parsed[qid] = hw.parse_query(question) if variant in {"V3", "V4", "V5", "V6"} else {}
        try:
            retrieved[qid] = get_chunks(index, question, variant)
        except Exception as exc:
            errors[qid] = repr(exc)
            retrieved[qid] = []
    retrieval_time = time.perf_counter() - started - indexing
    usage_before = hw.GENERATOR_USAGE.summary()
    answers, generator_errors = {}, {}
    if not offline:
        def answer(qid):
            try:
                return qid, hw.generate(questions[qid], retrieved[qid]), None
            except Exception as exc:
                return qid, "", repr(exc)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for qid, value, error in pool.map(answer, questions):
                answers[qid] = value
                if error:
                    generator_errors[qid] = error
    allowed = {(c.metadata["source"], c.page_content) for c in chunks}
    rows, details = [], {}
    for qid, question in questions.items():
        cs, g = retrieved[qid], gold[qid]
        valid = qid not in errors and len(cs) <= 5 and all((c.metadata["source"], c.page_content) in allowed for c in cs)
        row = {"id": qid, "category": g["category"], "question": question,
               "parsed": json.dumps(parsed[qid]), "parse_score": hw.parse_score(parsed[qid], g),
               "retrieved": ";".join(sorted({c.metadata["source"] for c in cs})), "valid": valid,
               "retrieval_hit": hw.retrieval_hit(cs, g) if g["evidence"] else "",
               "answer": answers.get(qid, ""),
               "correct": hw.answer_correct(answers[qid], g) if not offline else "",
               "expected": g["answer"]}
        rows.append(row)
        details[qid] = {"question": question, "parsed": parsed[qid], "expected_query": g["query"],
                        "evidence": g["evidence"], "retrieval_error": errors.get(qid),
                        "generator_error": generator_errors.get(qid),
                        "chunks": [{"metadata": c.metadata, "text": c.page_content} for c in cs]}
    answerable = [r for r in rows if gold[r["id"]]["evidence"]]
    unanswerable = [r for r in rows if not gold[r["id"]]["evidence"]]
    mean = lambda values: sum(values) / max(len(values), 1)
    kept = mean([bool(r["retrieved"]) for r in answerable])
    rejected = mean([not r["retrieved"] for r in unanswerable])
    recall = mean([r["retrieval_hit"] for r in answerable])
    problems = {f: hw.document_problems(by_file[f], None, m, f) for f, m in docs.items()}
    usage_after = hw.GENERATOR_USAGE.summary()
    summary = {"variant": variant, "description": VARIANTS[variant], "mode": "offline" if offline else "full",
               "table_score": mean([hw.table_score(hw.table_to_text(t["html"]), t) for t in tables]),
               "document_pass": mean([not p for p in problems.values()]), "chunks": len(chunks),
               "valid_nonempty": mean([r["valid"] and bool(r["retrieved"]) for r in answerable]),
               "parse_score": mean([r["parse_score"] for r in rows]), "recall": recall,
               "kept": kept, "rejected": rejected,
               "accuracy": None if offline else mean([r["correct"] for r in rows]),
               "retrieval_errors": len(errors), "generator_errors": len(generator_errors),
               "seconds": time.perf_counter() - started, "index_seconds": indexing,
               "retrieval_seconds": retrieval_time,
               "generator_tokens_in": usage_after["llm_input_tokens"] - usage_before["llm_input_tokens"],
               "generator_tokens_out": usage_after["llm_output_tokens"] - usage_before["llm_output_tokens"],
               "hw4_sha256": hashlib.sha256(Path(hw.__file__).read_bytes()).hexdigest(),
               "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.mkdir(parents=True, exist_ok=True)
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for name, data in [("summary", summary), ("details", details), ("document_problems", problems)]:
        (output / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-folder", type=Path, default=Path("public_test"))
    parser.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("experiments"))
    args = parser.parse_args()
    if not args.offline and not hw.os.environ.get("DEEPSEEK_API_KEY"):
        parser.error("No DEEPSEEK_API_KEY; configure .env or use --offline. No results were fabricated.")
    mode = "offline" if args.offline else "full"
    summaries = [evaluate(args.data_folder, v, args.offline, args.output / mode / v) for v in args.variants]
    with (args.output / mode / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)


if __name__ == "__main__":
    main()
