#!/usr/bin/env python3
"""Run ELS searches and statistical controls on a user-provided corpus."""

from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import json
import os
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from queue import Empty
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.corpus import load_corpus, load_targets
from src.els import find_els
from src.statistics import bh_adjust, corrected_p, entropy_metrics, expected_hits_iid, poisson_at_least_one, resample


_WORKER_PROGRESS_QUEUE = None


def initialize_worker(progress_queue) -> None:
    global _WORKER_PROGRESS_QUEUE
    _WORKER_PROGRESS_QUEUE = progress_queue


def worker_progress(label: str):
    """Envia progresso do processo para o terminal principal em etapas de 10%."""
    last_shown = 0

    def update(done: int, total: int, step: int) -> None:
        nonlocal last_shown
        interval = max(1, total // 10)
        if done == total or done - last_shown >= interval:
            if _WORKER_PROGRESS_QUEUE is not None:
                _WORKER_PROGRESS_QUEUE.put((label, done, total, step))
            last_shown = done

    return update


def make_scan_tasks(text, targets, max_skip, direction, max_locations, workers, chunks_per_term=None):
    """Split each target's skip range into chunks for distribution across processes."""
    tasks = []
    adaptive_chunks = chunks_per_term if chunks_per_term is not None else (1 if workers <= 1 else max(1, math.ceil(workers / max(1, len(targets))) * 2))
    for target_index, target in enumerate(targets):
        word = target["word"]
        if len(word) == 1:
            limit = 1
        else:
            limit = min(max_skip, max(0, (len(text) - 1) // (len(word) - 1)))
        if limit == 0:
            tasks.append({
                "target_index": target_index, "target": target, "text": text,
                "min_skip": 1, "max_skip": 1, "direction": direction,
                "max_locations": max_locations,
                "progress_label": f"{target['label']} | no valid skip range",
            })
            continue
        chunk_count = min(adaptive_chunks, limit)
        chunk_size = math.ceil(limit / chunk_count)
        for chunk_index, start in enumerate(range(1, limit + 1, chunk_size), 1):
            end = min(limit, start + chunk_size - 1)
            tasks.append({
                "target_index": target_index, "target": target, "text": text,
                "min_skip": start, "max_skip": end, "direction": direction,
                "max_locations": max_locations,
                "progress_label": f"{target['label']} | faixa {chunk_index}/{chunk_count}, saltos {start}-{end}",
            })
    return tasks


def search_worker(task):
    callback = worker_progress(task["progress_label"])
    found = find_els(
        task["text"], task["target"]["word"], task["max_skip"], task["direction"],
        task["max_locations"], callback, min_skip=task["min_skip"],
    )
    return {"target_index": task["target_index"], "hits": found.count, "locations": found.locations}


def null_replica_worker(task):
    if _WORKER_PROGRESS_QUEUE is not None:
        label = f"{task['model']} replica {task['replicate']}/{task['replicates']} | generating control corpus"
        _WORKER_PROGRESS_QUEUE.put((label, 0, 1, None))
    control = resample(task["text"], task["model"], random.Random(task["seed"]), task["block_size"])
    counts = []
    for index, target in enumerate(task["targets"], 1):
        label = f"{task['model']} replica {task['replicate']}/{task['replicates']} | target {index}/{len(task['targets'])}: {target['label']}"
        found = find_els(control, target["word"], task["max_skip"], task["direction"], 0, worker_progress(label))
        counts.append(found.count)
    return {
        "model": task["model"],
        "replicate": task["replicate"],
        "seed": task["seed"],
        "counts": counts,
    }


class ParallelRunner:
    """Persistent process pool; return all results and progress to the main process."""

    def __init__(self, workers: int, show_progress: bool):
        self.workers = workers
        self.show_progress = show_progress
        context = mp.get_context("spawn")
        self.progress_queue = context.Queue() if show_progress else None
        self.executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=initialize_worker,
            initargs=(self.progress_queue,),
        )

    def run(self, worker, tasks, label: str):
        if not tasks:
            return []
        active_workers = min(self.workers, len(tasks))
        print(f"{label}: {len(tasks)} tasks, up to {active_workers} parallel processes")
        futures = {self.executor.submit(worker, task) for task in tasks}
        pending = set(futures)
        results = []
        completed = 0
        last_progress = ""
        last_render = time.monotonic()
        render_interval = 15.0
        while pending:
            if self.progress_queue is not None:
                try:
                    progress_label, done, total, step = self.progress_queue.get(timeout=0.1)
                    percent = 100 * done / total if total else 100
                    suffix = " | preparando" if step is None else f" (salto {'+' if step > 0 else '-'}{abs(step):,})"
                    last_progress = f"{progress_label}: {percent:4.0f}%{suffix}"
                except Empty:
                    pass
                finished, pending = wait(pending, timeout=0, return_when=FIRST_COMPLETED)
            else:
                finished, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in finished:
                results.append(future.result())
                completed += 1
            if self.progress_queue is not None and (time.monotonic() - last_render >= render_interval or completed == len(tasks)):
                print(f"\r{label}: {completed}/{len(tasks)} tasks completed | {last_progress}", end="", flush=True)
                last_render = time.monotonic()
        if self.progress_queue is not None:
            while True:
                try:
                    progress_label, done, total, step = self.progress_queue.get_nowait()
                    percent = 100 * done / total if total else 100
                    suffix = " | preparando" if step is None else f" (salto {'+' if step > 0 else '-'}{abs(step):,})"
                    last_progress = f"{progress_label}: {percent:4.0f}%{suffix}"
                except Empty:
                    break
            print(f"\r{label}: {completed}/{len(tasks)} tasks completed | {last_progress}")
        results.sort(key=lambda result: (result.get("target_index", -1), result.get("replicate", -1)))
        return results

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=True)
        if self.progress_queue is not None:
            self.progress_queue.close()


def main() -> int:
    # Windows PowerShell consoles may default to a code page without Hebrew glyphs.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True, help="UTF-8 text file (the corpus is not downloaded or replaced automatically)")
    parser.add_argument("--targets", type=Path, default=Path("targets.json"), help="JSON file of targets fixed before the search")
    parser.add_argument("--alphabet", choices=("hebrew", "latin"), default="hebrew")
    parser.add_argument("--raw-json", action="store_true", help="Corpus is a Sefaria v1/v3 JSON response")
    parser.add_argument("--version-title", help="Exact version title in a Sefaria v3 JSON response")
    parser.add_argument("--merge-final-forms", action="store_true", help="Map ךםןףץ to common forms כמנפצ; default preserves written forms")
    parser.add_argument("--max-skip", type=int, default=1000)
    parser.add_argument("--direction", choices=("both", "forward", "backward"), default="both")
    parser.add_argument("--permutations", type=int, default=0, help="Replicas per null model; 0 disables controls")
    parser.add_argument("--null-models", default="iid_perm,block_perm,markov", help="Comma-separated model list")
    parser.add_argument("--block-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--max-locations", type=int, default=100, help="Maximum coordinates saved per target; counts remain complete")
    parser.add_argument("--out", type=Path, default=Path("results/analysis.json"))
    parser.add_argument("--multiple-tests", type=int, default=0, help="Declared Bonferroni family size; 0 omits")
    parser.add_argument("--workers", type=int, default=0, help="Parallel processes; 0 uses all available logical processors")
    parser.add_argument("--progress", action="store_true", help="Show stages, targets, skips, and replicas while running")
    args = parser.parse_args()
    if args.max_skip < 1 or args.permutations < 0 or args.max_locations < 0 or args.multiple_tests < 0 or args.block_size < 1 or args.workers < 0:
        parser.error("max-skip/block-size must be >=1; workers=0 uses all processors; other numeric parameters cannot be negative")

    runner = None
    try:
        started = time.perf_counter()
        if args.progress:
            print(f"[1/4] Reading local corpus: {args.corpus}")
        text, manifest = load_corpus(args.corpus, args.alphabet, args.raw_json, args.version_title, args.merge_final_forms)
        if not text:
            raise ValueError("The corpus is empty after normalization")
        targets = load_targets(args.targets, args.alphabet, args.merge_final_forms)
        if not targets:
            raise ValueError("No targets were loaded")
        available_workers = os.cpu_count() or 1
        worker_count = min(args.workers or available_workers, available_workers)
        runner = ParallelRunner(worker_count, args.progress)
        if args.progress:
            print(f"Corpus ready: {len(text):,} symbols; {len(targets)} targets; direction={args.direction}; max_skip={args.max_skip:,}")
            print(f"Available logical processors: {available_workers}; configured workers: {worker_count}")
            print("[2/4] Splitting skip ranges and distributing the search")
        scan_tasks = make_scan_tasks(text, targets, args.max_skip, args.direction, args.max_locations, worker_count)
        partial_scans = runner.run(search_worker, scan_tasks, "Busca observada")
        totals = [{"hits": 0, "locations": []} for _ in targets]
        for partial in partial_scans:
            result = totals[partial["target_index"]]
            result["hits"] += partial["hits"]
            result["locations"].extend(partial["locations"])

        results = []
        for index, target in enumerate(targets):
            found = totals[index]
            found["locations"].sort(key=lambda item: (abs(item[1]), 0 if item[1] > 0 else 1, item[0]))
            lam = expected_hits_iid(text, target["word"], args.max_skip, args.direction)
            row = {
                **target,
                "hits": found["hits"],
                "locations_sample": [{"start_zero_based": p, "step": step} for p, step in found["locations"][:args.max_locations]],
                "iid_expected_hits": lam,
                "iid_poisson_approx_p_at_least_one": poisson_at_least_one(lam),
            }
            if args.multiple_tests:
                row["bonferroni_family_size"] = args.multiple_tests
            results.append(row)

        null_results = []
        test_family_size = args.multiple_tests or len(targets)
        if args.permutations:
            models = [m.strip() for m in args.null_models.split(",") if m.strip()]
            if not models:
                parser.error("provide at least one --null-models value")
            if args.progress:
                print(f"[3/4] Controls: {len(models)} models x {args.permutations} replicas")
            for model_index, model in enumerate(models, 1):
                if args.progress:
                    print(f"  Model {model_index}/{len(models)}: {model}")
                replica_tasks = []
                for replicate in range(1, args.permutations + 1):
                    seed = args.seed + (model_index - 1) * args.permutations + replicate - 1
                    replica_tasks.append({
                        "text": text, "targets": targets, "model": model,
                        "block_size": args.block_size, "max_skip": args.max_skip,
                        "direction": args.direction, "replicate": replicate,
                        "replicates": args.permutations, "seed": seed,
                    })
                replica_results = runner.run(null_replica_worker, replica_tasks, f"Controle {model}")
                counts = [[] for _ in targets]
                for replica_result in replica_results:
                    for target_index, count in enumerate(replica_result["counts"]):
                        counts[target_index].append(count)
                model_rows = []
                for target_index, (target, observed) in enumerate(zip(targets, results)):
                    samples = counts[target_index]
                    exceed = sum(value >= observed["hits"] for value in samples)
                    raw_p = (exceed + 1) / (args.permutations + 1)
                    model_rows.append({
                        "model": model,
                        "group": target["group"],
                        "label": target["label"],
                        "permutations": args.permutations,
                        "seed_base": args.seed,
                        "replicate_seeds": [args.seed + (model_index - 1) * args.permutations + r - 1 for r in range(1, args.permutations + 1)],
                        "empirical_p_plus_one": raw_p,
                        "exceedances": exceed,
                        "null_mean_hits": sum(samples) / len(samples),
                        "null_min_hits": min(samples),
                        "null_max_hits": max(samples),
                    })
                adjusted_bh = bh_adjust([row["empirical_p_plus_one"] for row in model_rows])
                for row, q_value in zip(model_rows, adjusted_bh):
                    row["bonferroni_p_within_model"] = corrected_p(row["empirical_p_plus_one"], test_family_size)
                    row["bh_q_within_model"] = q_value
                    row["test_family_size"] = test_family_size
                null_results.extend(model_rows)

        if args.progress:
            print("[4/4] Calculating entropy and writing JSON report")
        output = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_parameters": {
                "max_skip": args.max_skip,
                "direction": args.direction,
                "alphabet": args.alphabet,
                "merge_final_forms": args.merge_final_forms,
                "permutations": args.permutations,
                "null_models": args.null_models if args.permutations else [],
                "block_size": args.block_size,
                "seed": args.seed,
                "workers": worker_count,
                "available_logical_processors": available_workers,
                "target_file": str(args.targets),
                "multiple_tests_family_size": test_family_size if args.permutations else (args.multiple_tests or None),
            },
            "corpus": manifest,
            "entropy_bits_per_symbol": entropy_metrics(text),
            "terms": results,
            "null_model_results": null_results,
            "notes": [
                "Terms in targets.json are exploratory examples, not preregistered predictions.",
                "The IID/Poisson approximation is a reference, not an empirically calibrated p-value.",
                "Choose null permutations according to the hypothesis; each model preserves different properties.",
                "Positions are zero-based in normalized text; audit the corpus edition and normalization.",
                "Bonferroni and Benjamini-Hochberg adjust empirical p-values across targets within each model; prior exploratory choices are not automatically included.",
            ],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"JSON report: {args.out}")
        print(f"Normalized corpus: {manifest['normalized_length']:,} symbols; raw SHA-256 {manifest['source_sha256']}")
        for row in results:
            print(f"{row['label']}: {row['hits']:,} hits; E[Iid]={row['iid_expected_hits']:.4g}; P≈{row['iid_poisson_approx_p_at_least_one']:.4g}")
        if null_results:
            print(f"Control results: {len(null_results)} target/model combinations")
        if args.progress:
            print(f"Run completed in {time.perf_counter() - started:.1f} s")
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if runner is not None:
            runner.close()


if __name__ == "__main__":
    raise SystemExit(main())
