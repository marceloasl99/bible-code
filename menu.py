#!/usr/bin/env python3
"""Interactive menu for downloading the corpus and running ELS analyses."""

from __future__ import annotations

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ANALYSIS_SCRIPT = ROOT / "run_analysis.py"
DOWNLOAD_SCRIPT = ROOT / "scripts" / "download_torah.py"


def ask_choice(prompt: str, choices: dict[str, str], default: str) -> str:
    while True:
        print(prompt)
        for key, label in choices.items():
            marker = " (default)" if key == default else ""
            print(f"  {key}) {label}{marker}")
        value = input("> ").strip() or default
        if value in choices:
            return value
        print("Invalid choice. Enter one of the listed options.\n")


def ask_number(prompt: str, default: int, minimum: int = 0) -> int:
    while True:
        value = input(f"{prompt} [{default}]: ").strip()
        if not value:
            return default
        try:
            number = int(value)
            if number >= minimum:
                return number
        except ValueError:
            pass
        print(f"Enter an integer greater than or equal to {minimum}.")


def project_path(value: str) -> Path:
    path = Path(value.strip().strip('"'))
    return path if path.is_absolute() else ROOT / path


def run_script(script: Path, arguments: list[str] | None = None) -> int:
    command = [sys.executable, str(script), *(arguments or [])]
    print(f"\nRunning: {Path(sys.executable).name} {script.relative_to(ROOT)} {' '.join(arguments or [])}")
    print("Follow the steps below. Press Ctrl+C to interrupt.\n")
    try:
        return subprocess.run(command, cwd=ROOT, check=False).returncode
    except KeyboardInterrupt:
        print("\nOperation interrupted by the user.")
        return 130


def download_corpus() -> bool:
    print("This step downloads five static JSON files and rebuilds the local corpus files.")
    print("Afterward, analyses use only local files.")
    status = run_script(DOWNLOAD_SCRIPT)
    if status:
        print(f"Download exited with code {status}. Check your connection and try again.")
        return False
    print("Download and corpus assembly completed.\n")
    return True


def configure_and_analyze() -> None:
    standard_corpus = ROOT / "data" / "torah_els.txt"
    merged_corpus = ROOT / "data" / "torah_els_merged_finals.txt"
    if not standard_corpus.exists():
        print("Local corpus not found. First choose 'Download and build the Torah corpus'.\n")
        return

    form_choice = ask_choice(
        "How should Hebrew final forms be handled?",
        {"1": "Preserve ךםןףץ (recommended to match the text spelling)", "2": "Merge final forms with their common forms"},
        "1",
    )
    corpus = standard_corpus if form_choice == "1" else merged_corpus
    if not corpus.exists():
        print(f"Local file not found: {corpus}\n")
        return

    targets_default = ROOT / "targets.json"
    target_input = input(f"Target JSON file [{targets_default.relative_to(ROOT)}]: ").strip()
    targets = project_path(target_input) if target_input else targets_default
    if not targets.exists():
        print(f"Target file not found: {targets}\n")
        return

    skip_choice = ask_choice(
        "Maximum skip for each occurrence? A higher limit takes longer.",
        {"1": "Fast: 20", "2": "Medium: 100", "3": "Broad: 1000", "4": "Enter a value"},
        "2",
    )
    max_skip = {"1": 20, "2": 100, "3": 1000}.get(skip_choice)
    if max_skip is None:
        max_skip = ask_number("max_skip", 100, minimum=1)

    direction_choice = ask_choice(
        "ELS search direction:",
        {"1": "Both (+ and -)", "2": "Forward only (+)", "3": "Backward only (-)"},
        "1",
    )
    direction = {"1": "both", "2": "forward", "3": "backward"}[direction_choice]

    available_cores = os.cpu_count() or 1
    worker_choice = ask_choice(
        f"How many logical processors should be used? The computer reports {available_cores}.",
        {"1": f"All available ({available_cores})", "2": "Enter a number"},
        "1",
    )
    workers = 0 if worker_choice == "1" else ask_number("Number of workers", available_cores, minimum=1)
    effective_workers = available_cores if workers == 0 else min(workers, available_cores)

    control_choice = ask_choice(
        "Run permutation controls? Each replica repeats the complete search.",
        {"0": "No, observed search only", "1": "Yes: 10 replicas for each of 3 models", "2": "Yes: choose replica count and models"},
        "0",
    )
    permutations = 0
    models = "iid_perm,block_perm,markov"
    if control_choice == "1":
        permutations = 10
    elif control_choice == "2":
        permutations = ask_number("Replicas per model", 10, minimum=1)
        model_choice = ask_choice(
            "Null models:",
            {"1": "All: letters, blocks, and Markov", "2": "Letter permutation only", "3": "Block permutation only", "4": "Markov only"},
            "1",
        )
        models = {
            "1": "iid_perm,block_perm,markov",
            "2": "iid_perm",
            "3": "block_perm",
            "4": "markov",
        }[model_choice]

    block_size = 8
    if "block_perm" in models:
        block_size = ask_number("Block size for block_perm", 8, minimum=1)

    default_out = ROOT / "results" / f"analysis_{datetime.now():%Y%m%d_%H%M%S}.json"
    out_input = input(f"Report file [{default_out.relative_to(ROOT)}]: ").strip()
    output = project_path(out_input) if out_input else default_out

    arguments = [
        "--corpus", str(corpus),
        "--targets", str(targets),
        "--alphabet", "hebrew",
        "--max-skip", str(max_skip),
        "--direction", direction,
        "--workers", str(workers),
        "--max-locations", "100",
        "--out", str(output),
        "--progress",
    ]
    if form_choice == "2":
        arguments.append("--merge-final-forms")
    if permutations:
        arguments.extend(["--permutations", str(permutations), "--null-models", models, "--block-size", str(block_size)])

    print("\nRun summary:")
    print(f"  Corpus: {corpus.relative_to(ROOT) if corpus.is_relative_to(ROOT) else corpus}")
    print(f"  Targets: {targets.relative_to(ROOT) if targets.is_relative_to(ROOT) else targets}")
    print(f"  Direction: {direction}; max_skip: {max_skip}")
    print(f"  Worker processes: {effective_workers} (maximum available: {available_cores})")
    print(f"  Controls: {permutations} replica(s) per model" if permutations else "  Controls: disabled")
    print(f"  Report: {output.relative_to(ROOT) if output.is_relative_to(ROOT) else output}")
    if input("Press Enter to start or type C to cancel: ").strip().lower() == "c":
        print("Analysis cancelled.\n")
        return
    run_script(ANALYSIS_SCRIPT, arguments)
    print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    while True:
        print("=" * 64)
        print("BIBLE CODE (ELS) — LOCAL MENU")
        print("=" * 64)
        choice = ask_choice(
            "What would you like to do?",
            {
                "1": "Analyze the Torah already stored locally",
                "2": "Download/update the local Torah corpus, then analyze",
                "3": "Download/update the local Torah corpus only",
                "0": "Exit",
            },
            "1",
        )
        try:
            if choice == "0":
                print("Goodbye.")
                return 0
            if choice == "1":
                configure_and_analyze()
            elif choice == "2":
                if download_corpus():
                    configure_and_analyze()
            elif choice == "3":
                download_corpus()
        except (EOFError, KeyboardInterrupt):
            print("\nReturning to the main menu.\n")


if __name__ == "__main__":
    raise SystemExit(main())
